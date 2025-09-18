# core/enums.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from enum import Enum, IntEnum

class Role(Enum):
    LANDLORD = "Landlord"
    PEASANT = "Peasant"
    PLAYER = "Player"

class RuleKind(Enum):
    STANDARD_DDZ = "standard_ddz"
    GENERIC_BEAT = "generic_beat"

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
    NORMAL = 10
    STRONG = 20
    BOMB = 90
    JOKER_BOMB = 100
