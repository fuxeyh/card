# core/events.py
# -*- coding: utf-8 -*-
"""Event dispatcher that owns ledger persistence."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

from .enums import EventType
from .ledger import Ledger, LedgerEvent


class EventDispatcher:
    """Central place to persist domain events.

    Game logic emits intents here so that failure handling and ordering are
    controlled in one spot. The dispatcher can later be extended to buffer
    batches or add retry hooks without touching game/rule code.
    """

    def __init__(self, ledger: Ledger):
        self._ledger = ledger

    def bind_ledger(self, ledger: Ledger) -> None:
        """Switch the underlying ledger (e.g., after resume)."""
        self._ledger = ledger

    def emit(self, event_type: EventType, payload: Dict[str, Any]) -> LedgerEvent:
        return self._ledger.append(event_type, payload)

    def emit_many(self, events: Iterable[Tuple[EventType, Dict[str, Any]]]) -> None:
        for event_type, payload in events:
            self.emit(event_type, payload)
