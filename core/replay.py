# core/replay.py
# -*- coding: utf-8 -*-
"""Rebuild in-memory state from a ledger (for crash/exit recovery)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .cards import Card, sort_cards
from .player import Player
from .enums import EventType, Role


def rebuild(players: List[Player], ledger) -> Dict[str, Any]:
    events = ledger.read_all()
    last_play: List[Card] = []
    last_player: Optional[int] = None
    current_index: int = 0
    landlord_idx: Optional[int] = None

    # Reset players
    for p in players:
        p.cards.clear()
        p.role = Role.PEASANT

    for e in events:
        t = e.type
        payload = e.payload
        if t == EventType.DEAL.value:
            # Distribute exactly by card code
            for i_str, codes in payload["players"].items():
                i = int(i_str)
                for code in codes:
                    players[i].cards.append(Card(code))
            for pl in players:
                pl.cards = sort_cards(pl.cards)
        elif t == EventType.SET_LANDLORD.value:
            landlord_idx = payload["landlord_idx"]
            # Give bottom to landlord
            for code in payload.get("bottom", []):
                players[landlord_idx].cards.append(Card(code))
            players[landlord_idx].cards = sort_cards(players[landlord_idx].cards)
            for i, pl in enumerate(players):
                pl.role = Role.LANDLORD if i == landlord_idx else Role.PEASANT
            current_index = landlord_idx
        elif t == EventType.PLAY.value:
            idx = payload["player_index"]
            codes = payload.get("codes") or payload.get("ranks")
            tmp: List[Card] = []
            hand = players[idx].cards
            for code in codes:
                for i, c in enumerate(hand):
                    if c.code == code or c.rank() == code:
                        tmp.append(c)
                        del hand[i]
                        break
            last_play = tmp
            last_player = idx
            current_index = (idx + 1) % len(players)
        elif t == EventType.PASS.value:
            idx = payload["player_index"]
            current_index = (idx + 1) % len(players)
        elif t == EventType.ROUND_RESET.value:
            last_play = []
            last_player = None

    return {
        "last_play": last_play,
        "last_player": last_player,
        "current_index": current_index,
        "landlord_idx": landlord_idx,
    }
