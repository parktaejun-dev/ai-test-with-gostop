from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass


@dataclass(frozen=True, slots=True)
class Agent:
    name: str

    def select_action(self, state):
        raise NotImplementedError

    def state_hash(self) -> str:
        if is_dataclass(self):
            payload = {
                field.name: getattr(self, field.name)
                for field in fields(self)
                if not field.name.startswith("_")
            }
        else:
            payload = {key: value for key, value in self.__dict__.items() if not key.startswith("_")}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
