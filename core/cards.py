# core/cards.py
# -*- coding: utf-8 -*-
"""Card primitives using a single string code (no suit for jokers)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

RANK_ORDER: List[str] = [
    "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "BJ", "RJ"
]
RANK_VALUE: Dict[str, int] = {r: i for i, r in enumerate(RANK_ORDER)}
SUITS: List[str] = ["♠", "♥", "♣", "♦"]
SUIT_SET = set(SUITS)

TOKEN_NORMALIZATION = {
    "j": "J",
    "q": "Q",
    "k": "K",
    "a": "A",
    "t": "10",
    "1": "A",
    "01": "A",
    "bj": "BJ",
    "rj": "RJ",
}

def normalize_token(tok: str) -> str:
    t = tok.strip().upper()
    return TOKEN_NORMALIZATION.get(t, t)

@dataclass(frozen=True, order=True)
class Card:
    code: str
    def is_joker(self) -> bool:
        return self.code in ("BJ", "RJ")
    def rank(self) -> str:
        if self.is_joker():
            return self.code
        if self.code and self.code[-1] in SUIT_SET:
            return self.code[:-1]
        return self.code
    def suit(self) -> Optional[str]:
        if self.is_joker():
            return None
        return self.code[-1] if self.code and self.code[-1] in SUIT_SET else None
    def value(self) -> int:
        return RANK_VALUE[self.rank()]
    def short(self) -> str:
        return self.rank()

def standard_deck(include_jokers: bool = True) -> list[Card]:
    deck: list[Card] = []
    for r in RANK_ORDER[:-2]:
        for s in SUITS:
            deck.append(Card(f"{r}{s}"))
    if include_jokers:
        deck.append(Card("BJ"))
        deck.append(Card("RJ"))
    return deck

def multi_deck(num_decks: int = 1, include_jokers: bool = True) -> list[Card]:
    out: list[Card] = []
    for _ in range(num_decks):
        out.extend(standard_deck(include_jokers=include_jokers))
    return out

def sort_cards(cards: Sequence[Card]) -> list[Card]:
    return sorted(cards, key=lambda c: (c.value(), c.suit() or ""))
