# core/rules.py
# -*- coding: utf-8 -*-
"""Standard 3-player Dou Dizhu only (single deck), with ledger logging.

This keeps the code focused and easy to read. To customize, you can still
extend HandPattern (牌型) or tweak bidding here.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from .cards import Card, standard_deck, sort_cards
from .player import Player
from .registry import HandRegistry
from .enums import Role, EventType
from .ledger import Ledger

@dataclass
class GameConfig:
    include_jokers: bool = True  # kept for possible toggles later

class BiddingController:
    """Externalises how bids are collected/announced (CLI, AI, tests, etc.)."""
    def on_bidding_start(self, order: Sequence[int], players: Sequence[Player]) -> None:
        pass

    def choose_bid(self, player: Player, highest_bid: int) -> int:
        raise NotImplementedError

    def on_bid_committed(self, player: Player, bid: int, highest_bid: int) -> None:
        pass

    def on_no_bid(self, players: Sequence[Player]) -> None:
        pass

    def on_landlord_selected(self, player: Player, via_random: bool) -> None:
        pass


class RuleSet:
    """Small interface so the Game class stays clean."""
    def __init__(self, cfg: GameConfig, ledger: Ledger):
        self.cfg = cfg
        self.ledger = ledger

    def setup(self, players: List[Player]) -> None: ...
    def starting_player_index(self, players: List[Player]) -> int: return 0
    def can_play(self, registry: HandRegistry, current: Sequence[Card], last: Sequence[Card]) -> bool:
        if not last: return registry.evaluate(current) is not None
        return registry.can_beat(current, last)
    def passes_to_reset(self) -> int: return 2
    def check_win(self, player: Player) -> bool: return player.is_empty()

class StandardDouDizhuRules(RuleSet):
    """3-player standard DDZ with bidding and 3 bottom cards."""
    def __init__(self, cfg: GameConfig, ledger: Ledger, bidding_controller: Optional[BiddingController] = None):
        super().__init__(cfg, ledger)
        self.bottom: List[Card] = []
        self.landlord_idx: int = 0
        self._bidding_controller = bidding_controller

    def setup(self, players: List[Player]) -> None:
        deck = standard_deck()
        random.shuffle(deck)

        # Deal 17 each; keep 3 as bottom
        deals: Dict[int, List[Card]] = {0: [], 1: [], 2: []}
        for _ in range(17):
            for i, p in enumerate(players):
                c = deck.pop()
                p.cards.append(c)
                deals[i].append(c)
        self.bottom = deck  # 3 cards left

        # Clean roles & sort
        for p in players:
            p.role = Role.PEASANT
            p.cards = sort_cards(p.cards)

        # Log DEAL with exact codes (precise recovery)
        self.ledger.append(EventType.DEAL, {
            "players": {i: [c.code for c in deals[i]] for i in deals},
            "bottom": [c.code for c in self.bottom],
        })

        # Bidding 0-3; random landlord if all 0
        self._bidding(players)

        # Landlord takes the bottom
        players[self.landlord_idx].add_cards(self.bottom)
        self.ledger.append(EventType.SET_LANDLORD, {
            "landlord_idx": self.landlord_idx,
            "bottom": [c.code for c in self.bottom],
        })
        self.bottom = []

    def _bidding(self, players: List[Player]) -> None:
        start = random.randrange(0, 3)
        highest = -1
        winner: Optional[int] = None
        order = [(start + i) % 3 for i in range(3)]
        controller = self._bidding_controller
        if controller is not None:
            controller.on_bidding_start(order, players)
        for idx in order:
            p = players[idx]
            bid = controller.choose_bid(p, highest) if controller else 0
            if bid < 0 or bid > 3:
                raise ValueError("Bidding controller must return 0-3")
            self.ledger.append(EventType.BID, {"player_index": idx, "bid": bid})
            if bid > highest: highest, winner = bid, idx
            if controller is not None:
                controller.on_bid_committed(p, bid, highest)
        if highest <= 0 or winner is None:
            if controller is not None:
                controller.on_no_bid(players)
            winner = random.randrange(0, 3)
        self.landlord_idx = winner
        for i, p in enumerate(players):
            p.role = Role.LANDLORD if i == winner else Role.PEASANT
        if controller is not None:
            controller.on_landlord_selected(players[winner], highest <= 0)

    def starting_player_index(self, players: List[Player]) -> int:
        return self.landlord_idx
