# core/rules.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
from .cards import Card, multi_deck, sort_cards
from .player import Player
from .registry import HandRegistry
from .enums import Role, RuleKind, EventType
from .ledger import Ledger

@dataclass
class GameConfig:
    num_players: int = 3
    num_decks: int = 1
    include_jokers: bool = True
    rule_kind: RuleKind = RuleKind.STANDARD_DDZ

class RuleSet:
    def __init__(self, cfg: GameConfig, ledger: Ledger):
        self.cfg = cfg
        self.ledger = ledger
    def setup(self, players: List[Player]) -> None:
        raise NotImplementedError
    def starting_player_index(self, players: List[Player]) -> int:
        return 0
    def can_play(self, registry: HandRegistry, current: Sequence[Card], last: Sequence[Card]) -> bool:
        if not last:
            return registry.evaluate(current) is not None
        return registry.can_beat(current, last)
    def passes_to_reset(self, num_players: int) -> int:
        return max(2, num_players - 1)
    def check_win(self, player: Player) -> bool:
        return player.is_empty()

class StandardDouDizhuRules(RuleSet):
    def __init__(self, cfg: GameConfig, ledger: Ledger):
        super().__init__(cfg, ledger)
        self.bottom: List[Card] = []
        self.landlord_idx: int = 0
    def setup(self, players: List[Player]) -> None:
        deck = multi_deck(self.cfg.num_decks, include_jokers=self.cfg.include_jokers)
        random.shuffle(deck)
        deals: Dict[int, List[Card]] = {i: [] for i in range(len(players))}
        for _ in range(17):
            for i, p in enumerate(players):
                c = deck.pop()
                p.cards.append(c)
                deals[i].append(c)
        self.bottom = deck
        for p in players:
            p.role = Role.PEASANT
            p.cards = sort_cards(p.cards)
        self.ledger.append(EventType.DEAL, {
            "players": {i: [c.code for c in deals[i]] for i in deals},
            "bottom": [c.code for c in self.bottom]
        })
        self._bidding(players)
        players[self.landlord_idx].add_cards(self.bottom)
        self.ledger.append(EventType.SET_LANDLORD, {
            "landlord_idx": self.landlord_idx,
            "bottom": [c.code for c in self.bottom]
        })
        self.bottom = []
    def _bidding(self, players: List[Player]) -> None:
        print("\n--- 叫分阶段（0/1/2/3）---")
        start = random.randrange(0, 3)
        highest = -1
        winner: Optional[int] = None
        order = [(start + i) % 3 for i in range(3)]
        for idx in order:
            p = players[idx]
            while True:
                try:
                    s = input(f"{p.name} 请叫分 [0-3]：").strip() or "0"
                    bid = int(s)
                    if bid < 0 or bid > 3:
                        raise ValueError
                    break
                except Exception:
                    print("请输入 0 1 2 或 3")
            self.ledger.append(EventType.BID, {"player_index": idx, "bid": bid})
            if bid > highest:
                highest = bid
                winner = idx
        if highest <= 0 or winner is None:
            print("无人叫分，随机指定地主。")
            winner = random.randrange(0, 3)
        self.landlord_idx = winner
        for i, p in enumerate(players):
            p.role = Role.LANDLORD if i == winner else Role.PEASANT
        print(f"地主：{players[winner].name} 获得底牌。")
    def starting_player_index(self, players: List[Player]) -> int:
        return self.landlord_idx

class GenericBeatRules(RuleSet):
    def setup(self, players: List[Player]) -> None:
        deck = multi_deck(self.cfg.num_decks, include_jokers=self.cfg.include_jokers)
        random.shuffle(deck)
        deals: Dict[int, List[Card]] = {i: [] for i in range(len(players))}
        i = 0
        while deck:
            c = deck.pop()
            players[i % len(players)].cards.append(c)
            deals[i % len(players)].append(c)
            i += 1
        for p in players:
            p.cards = sort_cards(p.cards)
            p.role = Role.PLAYER
        self._starter = random.randrange(0, len(players))
        self.ledger.append(EventType.DEAL, {"players": {i: [c.code for c in deals[i]] for i in deals}})
    def starting_player_index(self, players: List[Player]) -> int:
        return getattr(self, "_starter", 0)
