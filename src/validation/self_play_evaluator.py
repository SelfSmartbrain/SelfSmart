'''self_play_evaluator.py

Collects statistics from the self‑play manager runs.
Tracks total iterations, success count, new procedural entries, and computes
aggregate scores that feed into ``validation.metrics``.
''' 

import threading
from typing import Dict

# Thread‑safe counters
_counter_lock = threading.Lock()
_stats = {
    "iterations": 0,
    "successes": 0,
    "new_procedural": 0,
}

def record_iteration(success: bool, new_procedural: bool = False) -> None:
    """Call after each self‑play iteration.
    ``success`` indicates whether the synthetic problem was solved.
    ``new_procedural`` indicates whether a new entry was added to ProceduralMemory.
    """
    with _counter_lock:
        _stats["iterations"] += 1
        if success:
            _stats["successes"] += 1
        if new_procedural:
            _stats["new_procedural"] += 1

def compute_metrics() -> Dict[str, float]:
    """Calculate derived metrics for the current run.
    Returns a dict compatible with ``validation.metrics``.
    """
    with _counter_lock:
        it = _stats["iterations"] or 1  # avoid division by zero
        success_rate = _stats["successes"] / it
        skill_growth = _stats["new_procedural"] / it
    # Example: we map success_rate and skill_growth to a single self‑play score
    self_play_score = (success_rate + skill_growth) / 2.0
    return {
        "self_play_success_rate": success_rate,
        "self_play_skill_growth": skill_growth,
        "self_play_score": self_play_score,
    }

def reset() -> None:
    """Reset counters – useful before a new validation run."""
    with _counter_lock:
        for k in _stats:
            _stats[k] = 0
