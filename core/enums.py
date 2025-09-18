# core/enums.py
# -*- coding: utf-8 -*-
"""Enums used across the project.
- Role: player identity in standard Dou Dizhu.
- EventType: all actions that go into the append-only ledger.
- PatternPriority: cross-pattern strength ordering (bigger wins across types).
"""
from __future__ import annotations
from enum import Enum, IntEnum

class Role(Enum):
    LANDLORD = "Landlord"
    PEASANT = "Peasant"

class EventType(Enum):
    GAME_START = "GAME_START"
    DEAL = "DEAL"
    BID = "BID"
    SET_LANDLORD = "SET_LANDLORD"
    PLAY = "PLAY"
    PASS = "PASS"
    ROUND_RESET = "ROUND_RESET"
    GAME_END = "GAME_END"

class PatternPriority(IntEnum):
    NORMAL = 10        # singles/pairs/triples etc.
    STRONG = 20        # four-with-two etc.
    BOMB = 90          # bomb
    JOKER_BOMB = 100   # BJ+RJ
