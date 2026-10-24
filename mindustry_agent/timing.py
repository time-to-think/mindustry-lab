"""Additive Python-side stage durations measured on one monotonic clock."""
from __future__ import annotations

import time
from typing import Any, Callable


class CycleTimer:
    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.stages: dict[str, float] = {}

    def call(self, stage: str, function: Callable, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            self.stages[stage] = self.stages.get(stage, 0.0) + time.perf_counter() - started

    def snapshot(self) -> dict[str, Any]:
        return {"schema_version": 1, "stages_seconds": dict(self.stages),
                "elapsed_seconds": time.perf_counter() - self.started}
