# core/hand_patterns.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from .cards import Card, RANK_VALUE, sort_cards
from .enums import PatternPriority

@dataclass(frozen=True)
class HandMatch:
    name: str
    key: int
    meta: Dict
    priority: int
    size: int

class HandPattern:
    name: str = "abstract"
    priority: int = PatternPriority.NORMAL
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        raise NotImplementedError
    def same_shape(self, a: HandMatch, b: HandMatch) -> bool:
        return a.name == b.name

def counts_by_rank(cards: List[Card]) -> Dict[str, int]:
    from collections import Counter
    return dict(Counter([c.rank() for c in cards]))

def is_consecutive(ranks: List[str]) -> bool:
    vals = [RANK_VALUE[r] for r in ranks]
    if any(r in ("2", "BJ", "RJ") for r in ranks):
        return False
    return all(vals[i + 1] - vals[i] == 1 for i in range(len(vals) - 1))

def split_by_count(cnt: Dict[str, int], target: int) -> List[str]:
    return sorted([r for r, c in cnt.items() if c == target], key=lambda r: RANK_VALUE[r])

class JokerBomb(HandPattern):
    name = "joker_bomb"
    priority = PatternPriority.JOKER_BOMB
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 2:
            ranks = sorted([c.rank() for c in cards])
            if ranks == ["BJ", "RJ"]:
                return HandMatch(self.name, key=RANK_VALUE["RJ"], meta={}, priority=int(self.priority), size=2)
        return None

class Bomb(HandPattern):
    name = "bomb"
    priority = PatternPriority.BOMB
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 4:
            cnt = counts_by_rank(cards)
            if len(cnt) == 1:
                r = next(iter(cnt.keys()))
                return HandMatch(self.name, key=RANK_VALUE[r], meta={}, priority=int(self.priority), size=4)
        return None

class Single(HandPattern):
    name = "single"
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 1:
            r = cards[0].rank()
            return HandMatch(self.name, key=RANK_VALUE[r], meta={}, priority=int(self.priority), size=1)
        return None

class Pair(HandPattern):
    name = "pair"
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 2:
            cnt = counts_by_rank(cards)
            if len(cnt) == 1:
                r = next(iter(cnt.keys()))
                return HandMatch(self.name, key=RANK_VALUE[r], meta={}, priority=int(self.priority), size=2)
        return None

class Triple(HandPattern):
    name = "triple"
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 3:
            cnt = counts_by_rank(cards)
            if len(cnt) == 1:
                r = next(iter(cnt.keys()))
                return HandMatch(self.name, key=RANK_VALUE[r], meta={}, priority=int(self.priority), size=3)
        return None

class TripleWithSingle(HandPattern):
    name = "triple_with_single"
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 4:
            cnt = counts_by_rank(cards)
            if sorted(cnt.values()) == [1, 3]:
                r = [k for k, v in cnt.items() if v == 3][0]
                return HandMatch(self.name, key=RANK_VALUE[r], meta={}, priority=int(self.priority), size=4)
        return None

class TripleWithPair(HandPattern):
    name = "triple_with_pair"
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 5:
            cnt = counts_by_rank(cards)
            if sorted(cnt.values()) == [2, 3]:
                r = [k for k, v in cnt.items() if v == 3][0]
                return HandMatch(self.name, key=RANK_VALUE[r], meta={}, priority=int(self.priority), size=5)
        return None

class Sequence(HandPattern):
    name = "sequence"
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) >= 5:
            ranks = [c.rank() for c in sort_cards(cards)]
            if len(set(ranks)) == len(ranks) and is_consecutive(ranks):
                return HandMatch(self.name, key=RANK_VALUE[ranks[-1]], meta={"length": len(ranks)}, priority=int(self.priority), size=len(ranks))
        return None
    def same_shape(self, a: HandMatch, b: HandMatch) -> bool:
        return a.name == b.name and a.meta.get("length") == b.meta.get("length")

class PairSequence(HandPattern):
    name = "pair_sequence"
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) >= 6 and len(cards) % 2 == 0:
            cnt = counts_by_rank(cards)
            if all(v == 2 for v in cnt.values()):
                seq = sorted(cnt.keys(), key=lambda r: RANK_VALUE[r])
                if is_consecutive(seq):
                    return HandMatch(self.name, key=RANK_VALUE[seq[-1]], meta={"length_pairs": len(cards) // 2}, priority=int(self.priority), size=len(cards))
        return None
    def same_shape(self, a: HandMatch, b: HandMatch) -> bool:
        return a.name == b.name and a.meta.get("length_pairs") == b.meta.get("length_pairs")

class TripleSequence(HandPattern):
    name = "triple_sequence"
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) >= 6 and len(cards) % 3 == 0:
            cnt = counts_by_rank(cards)
            if all(v == 3 for v in cnt.values()):
                seq = sorted(cnt.keys(), key=lambda r: RANK_VALUE[r])
                if is_consecutive(seq):
                    return HandMatch(self.name, key=RANK_VALUE[seq[-1]], meta={"length_triples": len(cards) // 3}, priority=int(self.priority), size=len(cards))
        return None
    def same_shape(self, a: HandMatch, b: HandMatch) -> bool:
        return a.name == b.name and a.meta.get("length_triples") == b.meta.get("length_triples")

class FourWithTwoSingles(HandPattern):
    name = "four_with_two_singles"
    priority = PatternPriority.STRONG
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 6:
            cnt = counts_by_rank(cards)
            if sorted(cnt.values()) == [1, 1, 4]:
                r = [k for k, v in cnt.items() if v == 4][0]
                return HandMatch(self.name, key=RANK_VALUE[r], meta={}, priority=int(self.priority), size=6)
        return None

class FourWithTwoPairs(HandPattern):
    name = "four_with_two_pairs"
    priority = PatternPriority.STRONG
    def match(self, cards: List[Card]) -> Optional[HandMatch]:
        if len(cards) == 8:
            cnt = counts_by_rank(cards)
            if sorted(cnt.values()) == [2, 2, 4]:
                r = [k for k, v in cnt.items() if v == 4][0]
                return HandMatch(self.name, key=RANK_VALUE[r], meta={}, priority=int(self.priority), size=8)
        return None

BUILTIN_PATTERNS = [
    JokerBomb(),
    Bomb(),
    FourWithTwoPairs(),
    FourWithTwoSingles(),
    TripleSequence(),
    PairSequence(),
    Sequence(),
    TripleWithPair(),
    TripleWithSingle(),
    Triple(),
    Pair(),
    Single(),
]
