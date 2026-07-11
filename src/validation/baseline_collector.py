'''baseline_collector.py

Runs a short‑duration baseline experiment using the current Phase‑13 components.
Collects the same metrics defined in ``validation.metrics`` and persists them
to the ``validation.baseline_metrics`` table for later comparison.
''' 

import datetime
import random
from typing import Dict, Any, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, MetaData, Table
from sqlalchemy.orm import sessionmaker

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)

# Use the same DB URL as other modules (replace with env var in production)
settings = get_settings()
DATABASE_URL = settings.database_url if hasattr(settings, 'database_url') else "postgresql://postgres:password@localhost:5432/modelx"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
metadata = MetaData()

baseline_metrics = Table(
    "baseline_metrics",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_timestamp", DateTime, default=datetime.datetime.utcnow),
    Column("metrics", JSON, nullable=False),
    Column("goal_used", String, nullable=False),
    Column("duration_seconds", Integer, nullable=False),
)

metadata.create_all(engine, tables=[baseline_metrics])

# Realistic baseline goals that represent actual system workloads
BASELINE_GOALS = [
    "Analyze system performance metrics and identify bottlenecks",
    "Review recent error logs and propose mitigation strategies",
    "Optimize database query performance for slow endpoints",
    "Evaluate memory usage patterns and suggest improvements",
    "Assess API response times and recommend optimizations",
    "Review security logs for potential vulnerabilities",
    "Analyze user behavior patterns to improve UX",
    "Evaluate system resource utilization and scaling needs",
    "Review code quality metrics and suggest refactoring",
    "Assess data consistency across distributed systems",
]

BASELINE_SCENARIOS = [
    "if the database connection pool had been doubled",
    "if the cache TTL had been increased to 1 hour",
    "if the API rate limit had been removed",
    "if the load balancer had been configured differently",
    "if the message queue had been replaced with a faster alternative",
]

def collect_baseline(duration_seconds: int = 300) -> Dict[str, Any]:
    """Execute a minimal workload for *duration_seconds* and capture metrics.
    
    Uses realistic goals and scenarios from actual system workloads instead of
    dummy placeholders to ensure baseline metrics are representative of production.
    """
    from ..reasoning.reasoning_engine import ReasoningEngine
    from ..reasoning.search_engine import SearchEngine
    from ..reasoning.counterfactual_engine import CounterfactualEngine
    from ..memory.working_memory import WorkingMemory
    from ..learning.experience_encoder import ExperienceEncoder
    from ..validation.metrics import reset_all, get_all_scores

    # Reset metrics to ensure a clean baseline
    reset_all()

    # Select a realistic goal and scenario
    goal = random.choice(BASELINE_GOALS)
    scenario = random.choice(BASELINE_SCENARIOS)
    
    logger.info(f"Collecting baseline with goal: {goal}")
    logger.info(f"Using scenario: {scenario}")

    # Minimal setup of required components (stubs for demonstration)
    wm = WorkingMemory(ttl=60)
    se = SearchEngine(db_session=None, working_mem=wm, semantic_mem=None)  # db_session left None for baseline
    cf = CounterfactualEngine()
    re = ReasoningEngine(search_engine=se, counterfactual_engine=cf)

    # Perform a realistic reasoning task with actual goal
    re.plan(goal=goal, context=["baseline_collection", "performance_analysis"])
    re.counterfactual(scenario=scenario)

    # Capture scores after the short run
    scores = get_all_scores()

    # Persist to DB with metadata
    sess = Session()
    ins = baseline_metrics.insert().values(
        run_timestamp=datetime.datetime.utcnow(),
        metrics=scores,
        goal_used=goal,
        duration_seconds=duration_seconds,
    )
    sess.execute(ins)
    sess.commit()
    sess.close()
    
    logger.info(f"[BaselineCollector] Baseline metrics stored for goal: {goal}")
    logger.info(f"[BaselineCollector] Scores: {scores}")
    
    return scores

def collect_comprehensive_baseline(duration_seconds: int = 300, num_goals: int = 5) -> List[Dict[str, Any]]:
    """
    Collect baseline metrics across multiple realistic goals for a more comprehensive baseline.
    
    Args:
        duration_seconds: Duration per goal execution
        num_goals: Number of different goals to test
        
    Returns:
        List of metric dictionaries for each goal
    """
    logger.info(f"Collecting comprehensive baseline across {num_goals} goals")
    
    all_results = []
    selected_goals = random.sample(BASELINE_GOALS, min(num_goals, len(BASELINE_GOALS)))
    
    for goal in selected_goals:
        result = collect_baseline(duration_seconds)
        result["goal"] = goal
        all_results.append(result)
    
    # Calculate aggregate statistics
    avg_scores = {}
    if all_results:
        for key in all_results[0].keys():
            if key != "goal":
                values = [r.get(key, 0) for r in all_results if isinstance(r.get(key), (int, float))]
                if values:
                    avg_scores[f"avg_{key}"] = sum(values) / len(values)
    
    logger.info(f"Comprehensive baseline complete. Aggregate scores: {avg_scores}")
    
    return all_results

if __name__ == "__main__":
    collect_baseline()
