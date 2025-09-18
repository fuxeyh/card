# game.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, uuid
from typing import List
from core.cards import Card, normalize_token
from core.player import Player
from core.registry import HandRegistry
from core.rules import GameConfig, GenericBeatRules, RuleKind, RuleSet, StandardDouDizhuRules
from core.enums import EventType
from core.ledger import Ledger
from core.replay import rebuild

class Game:
    def __init__(self, cfg: GameConfig, names: List[str], ledger_dir: str):
        if cfg.num_players != len(names):
            raise ValueError("玩家数量与配置不一致")
        if cfg.num_players < 3 or cfg.num_players > 6:
            raise ValueError("支持 3–6 名玩家")
        self.cfg = cfg
        self.players = [Player(n) for n in names]
        self.registry = HandRegistry()
        self.game_id = str(uuid.uuid4())
        self.ledger_path = os.path.join(ledger_dir, f"ledger_{self.game_id}.jsonl")
        self.ledger = Ledger(self.ledger_path)
        self.rules: RuleSet = (
            StandardDouDizhuRules(cfg, self.ledger) if cfg.rule_kind == RuleKind.STANDARD_DDZ and cfg.num_players == 3
            else GenericBeatRules(cfg, self.ledger)
        )
        self.last_play: List[Card] = []
        self.last_player: int | None = None
        self.turn_index: int = 0

    def setup(self) -> None:
        self.ledger.append(EventType.GAME_START, {
            "game_id": self.game_id,
            "config": {
                "num_players": self.cfg.num_players,
                "num_decks": self.cfg.num_decks,
                "include_jokers": self.cfg.include_jokers,
                "rule_kind": self.cfg.rule_kind.value,
            },
            "names": [p.name for p in self.players],
        })
        self.rules.setup(self.players)
        self.turn_index = self.rules.starting_player_index(self.players)

    def resume_from_ledger(self, ledger_path: str) -> None:
        self.ledger = Ledger(ledger_path)
        state = rebuild(self.players, self.ledger)
        self.last_play = state["last_play"]
        self.last_player = state["last_player"]
        self.turn_index = state["current_index"]

    def play(self) -> None:
        print("\n--- 对局开始 ---")
        passes_needed = self.rules.passes_to_reset(len(self.players))
        passes_in_row = 0
        while True:
            p = self.players[self.turn_index]
            self._print_status(self.turn_index)
            cmd = input(f"{p.name} 出牌，输入牌面或命令[help/show/last/tips/sort/pass]：").strip()
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
                print("可考虑：" + (" | ".join([" ".join(t) for t in tips[:5]]) if tips else "暂无提示。"))
                continue
            if cmd.lower() == "pass":
                if not self.last_play or self.last_player == self.turn_index:
                    print("你是本轮首家，不能 PASS。"); continue
                passes_in_row += 1
                self.ledger.append(EventType.PASS, {"player_index": self.turn_index})
                if passes_in_row >= passes_needed:
                    self.last_play = []; self.last_player = None; passes_in_row = 0
                    self.ledger.append(EventType.ROUND_RESET, {"reason": "passes_reset"})
                self.turn_index = (self.turn_index + 1) % len(self.players); continue
            ranks = [normalize_token(t) for t in cmd.split() if t.strip()]
            if not ranks: print("输入为空，请重试。"); continue
            if not p.has_cards(ranks): print("你没有这些牌，请检查输入。"); continue
            temp = self._pick_from_hand(p, ranks)
            m = self.registry.evaluate(temp)
            if m is None: print("这不是一个合法的出牌组合。"); continue
            if self.last_play and self.last_player != self.turn_index:
                if not self.rules.can_play(self.registry, temp, self.last_play):
                    print("无法大过上家，请重试或输入 pass。"); continue
            played = p.take_cards(ranks)
            self.last_play = played; self.last_player = self.turn_index; passes_in_row = 0
            print(f"{p.name} 出：", " ".join([c.short() for c in played]), f"[{m.name}]")
            self.ledger.append(EventType.PLAY, {
                "player_index": self.turn_index,
                "codes": [c.code for c in played],
                "tokens": [c.rank() for c in played],
                "match": {"name": m.name, "key": m.key, "meta": m.meta, "priority": m.priority},
            })
            if self.rules.check_win(p):
                print(f"\n🎉 {p.name} 出完了！")
                print("结果：地主胜" if getattr(p.role, "value", str(p.role)) == "Landlord" else "结果：农民/平民方胜")
                self.ledger.append(EventType.GAME_END, {"winner_index": self.turn_index, "role": getattr(p.role, "value", str(p.role))})
                break
            self.turn_index = (self.turn_index + 1) % len(self.players)

    def _pick_from_hand(self, p: Player, ranks: List[str]) -> List[Card]:
        tmp: List[Card] = []
        hand = p.cards.copy()
        for r in ranks:
            for i, c in enumerate(hand):
                if c.rank() == r:
                    tmp.append(c); del hand[i]; break
        return tmp

    def _simple_tips(self, p: Player) -> List[List[str]]:
        from itertools import combinations
        from core.cards import RANK_VALUE
        suggestions: List[List[str]] = []
        if not self.last_play or self.last_player == self.players.index(p):
            low = min(p.cards, key=lambda c: c.value()); suggestions.append([low.rank()])
            from collections import Counter
            cnt = Counter([c.rank() for c in p.cards])
            for r, num in sorted(cnt.items(), key=lambda kv: RANK_VALUE[kv[0]]):
                if num >= 2: suggestions.append([r, r]); break
            return suggestions
        target = self.last_play; t_eval = self.registry.evaluate(target)
        if t_eval is None: return suggestions
        n = len(p.cards); tested = set(); sizes = {len(target)}
        if t_eval.name != "joker_bomb": sizes |= {2, 4}
        for k in sorted(sizes):
            for combo in combinations(range(n), k):
                ranks = tuple(sorted([p.cards[i].rank() for i in combo], key=lambda r: RANK_VALUE[r]))
                if (k, ranks) in tested: continue
                tested.add((k, ranks)); subset = [p.cards[i] for i in combo]
                if self.rules.can_play(self.registry, subset, target):
                    suggestions.append([c.rank() for c in subset])
        return suggestions

    def _print_status(self, idx: int) -> None:
        order_names = " -> ".join([pl.name for pl in self.players[idx:] + self.players[:idx]])
        print("\n当前出牌顺序：", order_names)
        last = "PASS" if not self.last_play else " ".join([c.short() for c in self.last_play])
        src = f"（来自 {self.players[self.last_player].name}）" if self.last_player is not None else ""
        print("桌面上一次出牌：", last, src)

def print_help() -> None:
    print("""命令：help/show/last/tips/sort/pass；出牌示例：BJ RJ、10 10、7 8 9 10 J、Q Q Q 9 等。""")
