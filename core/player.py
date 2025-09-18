# core/player.py
# -*- coding: utf-8 -*-
"""Player dataclass and common hand operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .cards import Card, normalize_token, sort_cards, RANK_VALUE
from .enums import Role


@dataclass
class Player:
    name: str
    cards: List[Card] = field(default_factory=list)
    role: Role = Role.PEASANT  # will be set during bidding

    # ----------------------------- Hand Ops -----------------------------
    def sort(self) -> None:
        self.cards = sort_cards(self.cards)

    def has_cards(self, ranks: List[str]) -> bool:
        """Check multiset containment by rank tokens (not specific suits)."""
        from collections import Counter

        target = Counter([normalize_token(r) for r in ranks])
        own = Counter([c.rank() for c in self.cards])
        return all(own[r] >= n for r, n in target.items())

    def take_cards(self, ranks: List[str]) -> List[Card]:
        """Remove the first matching instances by rank tokens and return them."""
        taken: List[Card] = []
        req = [normalize_token(r) for r in ranks]
        for r in req:
            for i, c in enumerate(self.cards):
                if c.rank() == r:
                    taken.append(c)
                    del self.cards[i]
                    break
        return taken

    def add_cards(self, cards: List[Card]) -> None:
        self.cards.extend(cards)
        self.sort()

    def is_empty(self) -> bool:
        return len(self.cards) == 0

    def display(self) -> str:
        """One-line grouped summary for console."""
        self.sort()
        from collections import Counter

        cnt = Counter([c.rank() for c in self.cards])
        bundle = " ".join(
            [
                f"{r}×{n}"
                for r, n in sorted(
                    cnt.items(), key=lambda kv: (RANK_VALUE[kv[0]], kv[1])
                )
            ]
        )
        return f"[{self.name} | {self.role.value}] {bundle}"
