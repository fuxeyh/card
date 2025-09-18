# core/registry.py
# -*- coding: utf-8 -*-
"""Pattern registry + comparison rules (small and focused)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .cards import Card
from .hand_patterns import HandMatch, HandPattern, BUILTIN_PATTERNS

@dataclass
class HandRegistry:
    patterns: List[HandPattern] = field(default_factory=list)

    def __post_init__(self):
        if not self.patterns:
            self.patterns = list(BUILTIN_PATTERNS)

    def register(self, pattern: HandPattern) -> None:
        self.patterns.append(pattern)

    def evaluate(self, cards: Sequence[Card]) -> Optional[HandMatch]:
        """Return the *best* matching pattern for the given cards."""
        best: Optional[HandMatch] = None
        for p in self.patterns:
            m = p.match(list(cards))
            if not m:
                continue
            if best is None or (m.priority, m.key) > (best.priority, best.key):
                best = m
        return best

    def can_beat(self, current: Sequence[Card], last: Sequence[Card]) -> bool:
        """Whether `current` can beat `last` under pattern rules."""
        ca = self.evaluate(current); cb = self.evaluate(last)
        if ca is None or cb is None:
            return False
        if ca.name != cb.name:
            return ca.priority > cb.priority  # cross-pattern rule
        # same pattern name -> require same shape and bigger key
        ap = self._find(ca.name); bp = self._find(cb.name)
        if ap and bp and ap.same_shape(ca, cb):
            return ca.key > cb.key
        return False

    def _find(self, name: str) -> Optional[HandPattern]:
        for p in self.patterns:
            if p.name == name:
                return p
        return None
