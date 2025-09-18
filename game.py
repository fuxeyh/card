# game.py
# -*- coding: utf-8 -*-
"""Terminal game loop: simple, commented, and recoverable via ledger."""
from __future__ import annotations

import os, uuid
from typing import List

from core.cards import Card, normalize_token
from core.player import Player
from core.registry import HandRegistry
from core.rules import GameConfig, RuleSet, StandardDouDizhuRules
from core.enums import EventType, Role
from core.ledger import Ledger
from core.replay import rebuild

LEDGER_DIR = "./ledger"
LATEST_PTR = os.path.join(LEDGER_DIR, "_latest.txt")

class Game:
    def __init__(self, names: List[str]):
        if len(names) != 3:
            raise ValueError("本版本仅支持 3 名玩家")
        self.players = [Player(n) for n in names]
        self.registry = HandRegistry()

        # Prepare a new ledger for this session
        os.makedirs(LEDGER_DIR, exist_ok=True)
        self.game_id = str(uuid.uuid4())
        self.ledger_path = os.path.join(LEDGER_DIR, f"ledger_{self.game_id}.jsonl")
        self.ledger = Ledger(self.ledger_path)

        # Single ruleset: standard 3-player Dou Dizhu
        self.rules: RuleSet = StandardDouDizhuRules(GameConfig(), self.ledger)

        # Round state
        self.last_play: List[Card] = []
        self.last_player: int | None = None
        self.turn_index: int = 0

    # ------------------------------- Lifecycle -------------------------------
    def setup(self) -> None:
        # Announce the game in ledger
        self.ledger.append(EventType.GAME_START, {
            "game_id": self.game_id,
            "names": [p.name for p in self.players],
        })
        # Deal + bidding done in rules
        self.rules.setup(self.players)
        self.turn_index = self.rules.starting_player_index(self.players)

        # Remember latest ledger path for convenient resume
        with open(LATEST_PTR, "w", encoding="utf-8") as f:
            f.write(self.ledger_path)

    def resume_from_ledger(self, ledger_path: str) -> None:
        """Rebuild full state from a previous ledger (crash-safe)."""
        self.ledger = Ledger(ledger_path)
        state = rebuild(self.players, self.ledger)
        self.last_play = state["last_play"]
        self.last_player = state["last_player"]
        self.turn_index = state["current_index"]

    # --------------------------------- Loop ----------------------------------
    def play(self) -> None:
        print("\n--- 对局开始 ---")
        passes_needed = self.rules.passes_to_reset()
        passes_in_row = 0

        while True:
            p = self.players[self.turn_index]
            self._print_status(self.turn_index)

            cmd = input(f"{p.name} 出牌，输入牌面或命令[help/show/last/tips/sort/pass]：").strip()

            # ----- Utility commands -----
            if cmd.lower() in ("help", "?"):
                print_help(); continue
            if cmd.lower() == "show":
                for pl in self.players: print(pl.display())
                continue
            if cmd.lower() == "last":
                if self.last_play: print("上家出牌：", " ".join([c.short() for c in self.last_play]))
                else: print("当前为新一轮，无需跟牌。")
                continue
            if cmd.lower() == "sort":
                p.sort(); print("已整理手牌。"); continue
            if cmd.lower() == "tips":
                tips = self._simple_tips(p)
                if tips: print("可考虑：", " | ".join([" ".join(t) for t in tips[:5]]))
                else: print("暂无提示。")
                continue
            if cmd.lower() == "pass":
                # Can't pass if you start the trick
                if not self.last_play or self.last_player == self.turn_index:
                    print("你是本轮首家，不能 PASS。"); continue
                passes_in_row += 1
                self.ledger.append(EventType.PASS, {"player_index": self.turn_index})
                if passes_in_row >= passes_needed:
                    # New trick
                    self.last_play = []
                    self.last_player = None
                    passes_in_row = 0
                    self.ledger.append(EventType.ROUND_RESET, {"reason": "passes_reset"})
                self.turn_index = (self.turn_index + 1) % 3
                continue

            # ----- Parse ranks from user input -----
            ranks = [normalize_token(t) for t in cmd.split() if t.strip()]
            if not ranks: print("输入为空，请重试。"); continue
            if not p.has_cards(ranks): print("你没有这些牌，请检查输入。"); continue

            # Assemble temporary cards for validation
            temp = self._pick_from_hand(p, ranks)
            m = self.registry.evaluate(temp)
            if m is None: print("这不是一个合法的出牌组合。"); continue

            # Need to beat the last play when not starting
            if self.last_play and self.last_player != self.turn_index:
                if not self.rules.can_play(self.registry, temp, self.last_play):
                    print("无法大过上家，请重试或输入 pass。"); continue

            # Commit
            played = p.take_cards(ranks)
            self.last_play = played
            self.last_player = self.turn_index
            passes_in_row = 0
            print(f"{p.name} 出：", " ".join([c.short() for c in played]), f"[{m.name}]")

            # Log onto ledger (precise codes + human tokens)
            self.ledger.append(EventType.PLAY, {
                "player_index": self.turn_index,
                "codes": [c.code for c in played],
                "tokens": [c.rank() for c in played],
                "match": {"name": m.name, "key": m.key, "meta": m.meta, "priority": m.priority},
            })

            # Win?
            if self.rules.check_win(p):
                print(f"\n🎉 {p.name} 出完了！")
                print("结果：地主胜" if p.role == Role.LANDLORD else "结果：农民胜")
                self.ledger.append(EventType.GAME_END, {"winner_index": self.turn_index, "role": p.role.value})
                break

            # Next player
            self.turn_index = (self.turn_index + 1) % 3

    # -------------------------------- Helpers --------------------------------
    def _pick_from_hand(self, p: Player, ranks: List[str]) -> List[Card]:
        """Pick cards by rank tokens without mutating the hand (preview)."""
        tmp: List[Card] = []
        hand = p.cards.copy()
        for r in ranks:
            for i, c in enumerate(hand):
                if c.rank() == r:
                    tmp.append(c); del hand[i]; break
        return tmp

    def _simple_tips(self, p: Player) -> List[List[str]]:
        """Very naive hints: lowest single/pair, or some beating combos."""
        from itertools import combinations
        from core.cards import RANK_VALUE
        from collections import Counter

        suggestions: List[List[str]] = []
        # Free to start: lowest single + maybe one small pair
        if not self.last_play or self.last_player == self.players.index(p):
            low = min(p.cards, key=lambda c: c.value())
            suggestions.append([low.rank()])
            cnt = Counter([c.rank() for c in p.cards])
            for r, num in sorted(cnt.items(), key=lambda kv: RANK_VALUE[kv[0]]):
                if num >= 2: suggestions.append([r, r]); break
            return suggestions

        # Must beat
        target = self.last_play
        t_eval = self.registry.evaluate(target)
        if t_eval is None:
            return suggestions
        n = len(p.cards)
        tested = set()
        sizes = {len(target)}
        if t_eval.name != "joker_bomb": sizes |= {2, 4}
        for k in sorted(sizes):
            for combo in combinations(range(n), k):
                ranks = tuple(sorted([p.cards[i].rank() for i in combo], key=lambda r: RANK_VALUE[r]))
                if (k, ranks) in tested: continue
                tested.add((k, ranks))
                subset = [p.cards[i] for i in combo]
                if self.rules.can_play(self.registry, subset, target):
                    suggestions.append([c.rank() for c in subset])
        return suggestions

    def _print_status(self, idx: int) -> None:
        order_names = " -> ".join([pl.name for pl in self.players[idx:] + self.players[:idx]])
        print("\n当前出牌顺序：", order_names)
        last = "PASS" if not self.last_play else " ".join([c.short() for c in self.last_play])
        src = f"（来自 {self.players[self.last_player].name}）" if self.last_player is not None else ""
        print("桌面上一次出牌：", last, src)

def print_help() -> None:  # pragma: no cover
    print(
        """
命令与输入示例：
  3 3              对子
  7 8 9 10 J       顺子（至少5张，不能含2和王）
  Q Q Q 9          三带一
  5 5 5 6 6        三带一对
  10 10 J J Q Q    连对（至少3对）
  4 4 4 5 5 5      飞机（纯三顺）
  2 2 2 2          炸弹
  BJ RJ            王炸

特殊命令：
  help  显示本帮助
  show  显示所有玩家手牌摘要
  last  查看上家出牌
  tips  简单提示
  sort  整理当前手牌
  pass  过（在需要跟牌时可用）
"""
    )
