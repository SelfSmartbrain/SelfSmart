"""metrics.py

Defines and updates the validation metrics used in Phase 13.5.
All metric updates are stored in a simple in‑memory dict and can be persisted
via the ``validation.report_generator`` when a report is generated.
"""

from typing import Dict, Any
import threading

# Global thread‑safe store for metric values
_metrics_lock = threading.Lock()
_metrics_store: Dict[str, Any] = {
    "cognitive_score": 0.0,
    "reasoning_score": 0.0,
    "memory_utilization_score": 0.0,
    "abstraction_score": 0.0,
    "transfer_score": 0.0,
    "prediction_score": 0.0,
    "generalization_score": 0.0,
}

# ---- Helper update functions ------------------------------------------------


def _set_metric(name: str, value: float) -> None:
    with _metrics_lock:
        _metrics_store[name] = value


def _add_to_metric(name: str, delta: float) -> None:
    with _metrics_lock:
        _metrics_store[name] = _metrics_store.get(name, 0.0) + delta


# ---- Public API -------------------------------------------------------------


def record_reasoning_score(score: float) -> None:
    """Record the latest reasoning accuracy (0‑1)."""
    _set_metric("reasoning_score", score)
    _recompute_cognitive_score()


def record_memory_utilization(hit_ratio: float) -> None:
    """Record how often memory look‑ups succeed (0‑1)."""
    _set_metric("memory_utilization_score", hit_ratio)
    _recompute_cognitive_score()


def record_abstraction_score(score: float) -> None:
    _set_metric("abstraction_score", score)
    _recompute_cognitive_score()


def record_transfer_score(score: float) -> None:
    _set_metric("transfer_score", score)
    _recompute_cognitive_score()


def record_prediction_score(score: float) -> None:
    _set_metric("prediction_score", score)
    _recompute_cognitive_score()


def record_generalization_score(score: float) -> None:
    _set_metric("generalization_score", score)
    _recompute_cognitive_score()


def _recompute_cognitive_score() -> None:
    """Weighted sum of all component scores.
    The weights are simple equal weighting for now – they can be tuned later.
    """
    with _metrics_lock:
        total = (
            _metrics_store["reasoning_score"]
            + _metrics_store["memory_utilization_score"]
            + _metrics_store["abstraction_score"]
            + _metrics_store["transfer_score"]
            + _metrics_store["prediction_score"]
            + _metrics_store["generalization_score"]
        )
        # Normalize to 0‑1 range (max possible sum = 6)
        _metrics_store["cognitive_score"] = total / 6.0


def get_all_scores() -> Dict[str, float]:
    """Return a copy of the current metric values."""
    with _metrics_lock:
        return dict(_metrics_store)


# ---- Convenience wrappers for easy import -----------------------------------


def reset_all() -> None:
    """Reset every metric to zero – useful for baseline collection runs."""
    with _metrics_lock:
        for key in _metrics_store:
            _metrics_store[key] = 0.0
