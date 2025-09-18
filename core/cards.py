# core/cards.py
# -*- coding: utf-8 -*-
"""Card primitives using a single string `code`.
- Normal cards use code like '3♠', '10♥' (rank + suit symbol).
- Jokers are 'BJ' and 'RJ' with **no suit**.
This unifies representation (no separate rank/suit fields) while still allowing
us to parse rank/suit via small helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

# -------- Rank & suit order used for sorting / comparison --------
RANK_ORDER: List[str] = [
    "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "BJ", "RJ"
]
RANK_VALUE: Dict[str, int] = {r: i for i, r in enumerate(RANK_ORDER)}
SUITS: List[str] = ["♠", "♥", "♣", "♦"]
SUIT_SET = set(SUITS)

# -------- Input normalization (terminal tokens) --------
TOKEN_NORMALIZATION = {
    "j": "J",
    "q": "Q",
    "k": "K",
    "a": "A",
    "t": "10",
    "1": "A",   # common habit: 1 => A
    "01": "A",
    "bj": "BJ",
    "rj": "RJ",
}

def normalize_token(tok: str) -> str:
    """Normalize one user-typed token into a canonical rank string."""
    t = tok.strip().upper()
    return TOKEN_NORMALIZATION.get(t, t)

@dataclass(frozen=True, order=True)
class Card:
    """Single-field card representation.
    code: e.g. '3♠', '10♦', 'BJ', 'RJ'.
    """
    code: str

    # ---------- Derived helpers (do not store rank/suit separately) ----------
    def is_joker(self) -> bool:
        return self.code in ("BJ", "RJ")

    def rank(self) -> str:
        if self.is_joker():
            return self.code
        if self.code and self.code[-1] in SUIT_SET:
            return self.code[:-1]
        return self.code  # fallback

    def suit(self) -> Optional[str]:
        if self.is_joker():
            return None
        return self.code[-1] if self.code and self.code[-1] in SUIT_SET else None

    def value(self) -> int:
        return RANK_VALUE[self.rank()]

    def short(self) -> str:
        """Short text for console output (rank only)."""
        return self.rank()

# ------------------------------ Deck helpers ------------------------------
def standard_deck() -> list[Card]:
    """Build one 54-card Dou Dizhu deck (52 + 2 jokers)."""
    deck: list[Card] = []
    for r in RANK_ORDER[:-2]:
        for s in SUITS:
            deck.append(Card(f"{r}{s}"))
    deck.append(Card("BJ"))
    deck.append(Card("RJ"))
    return deck

def sort_cards(cards: Sequence[Card]) -> list[Card]:
    """Sort by rank value first, then suit for stable display."""
    return sorted(cards, key=lambda c: (c.value(), c.suit() or ""))
