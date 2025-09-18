# core/ledger.py
# -*- coding: utf-8 -*-
"""Append-only JSONL ledger with hash chaining (for recovery & audit)."""
from __future__ import annotations

import json, os, hashlib, datetime
from dataclasses import dataclass
from typing import Any, Dict, List
from .enums import EventType

def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _hash_record(prev_hash: str, event: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update((prev_hash or "").encode("utf-8"))
    h.update(json.dumps(event, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()

@dataclass
class LedgerEvent:
    seq: int
    type: str
    payload: Dict[str, Any]
    ts: str
    prev_hash: str
    hash: str

class Ledger:
    """Small, dependency-free ledger.
    - append(EventType, payload) -> writes one JSON line with hash.
    - read_all() -> verifies the chain and yields events.
    """
    def __init__(self, path: str):
        self.path = path
        self._seq = 0
        self._last_hash = ""
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        self._seq = obj.get("seq", self._seq)
                        self._last_hash = obj.get("hash", self._last_hash)
                    except Exception:
                        continue

    def append(self, etype: EventType, payload: Dict[str, Any]) -> LedgerEvent:
        self._seq += 1
        core = {"seq": self._seq, "type": etype.value, "payload": payload, "ts": _now_iso()}
        rec_hash = _hash_record(self._last_hash, core)
        full = {**core, "prev_hash": self._last_hash, "hash": rec_hash}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(full, ensure_ascii=False) + "\n")
        self._last_hash = rec_hash
        return LedgerEvent(**full)  # type: ignore

    def read_all(self) -> List[LedgerEvent]:
        out: List[LedgerEvent] = []
        if not os.path.exists(self.path):
            return out
        prev = ""
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                expected = _hash_record(prev, {k: obj[k] for k in ["seq", "type", "payload", "ts"]})
                if expected != obj.get("hash"):
                    raise ValueError(f"Ledger corrupted at seq {obj.get('seq')}")
                prev = obj.get("hash", "")
                out.append(LedgerEvent(**obj))  # type: ignore
        return out
