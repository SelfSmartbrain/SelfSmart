"""knowledge_benchmark.py

Provides benchmarking capabilities for knowledge systems.
Tests knowledge structures against standard datasets and scenarios.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import time

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class BenchmarkType(str, Enum):
    """Types of benchmarks."""
    ACCURACY = "accuracy"
    GENERALIZATION = "generalization"
    PREDICTION = "prediction"
    EFFICIENCY = "efficiency"
    ROBUSTNESS = "robustness"


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    benchmark_id: str
    benchmark_type: BenchmarkType
    knowledge_id: str
    score: float
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_type": self.benchmark_type.value,
            "knowledge_id": self.knowledge_id,
            "score": self.score,
            "metrics": self.metrics,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class KnowledgeBenchmark:
    """Benchmarks knowledge structures against standard tests."""
    
    def __init__(self):
        self.benchmarks: Dict[str, Callable] = {}
        self.results: Dict[str, List[BenchmarkResult]] = {}
        self._register_standard_benchmarks()
        logger.info("KnowledgeBenchmark initialized")
    
    def _register_standard_benchmarks(self):
        """Register standard benchmark tests."""
        self.benchmarks["accuracy_test"] = self._accuracy_benchmark
        self.benchmarks["generalization_test"] = self._generalization_benchmark
        self.benchmarks["prediction_test"] = self._prediction_benchmark
        self.benchmarks["efficiency_test"] = self._efficiency_benchmark
        self.benchmarks["robustness_test"] = self._robustness_benchmark
    
    def register_benchmark(
        self,
        name: str,
        benchmark_func: Callable,
    ) -> None:
        """Register a custom benchmark."""
        self.benchmarks[name] = benchmark_func
        logger.info(f"Registered custom benchmark: {name}")
    
    def run_benchmark(
        self,
        benchmark_name: str,
        knowledge_id: str,
        knowledge_data: Dict[str, Any],
        test_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[BenchmarkResult]:
        """Run a specific benchmark on knowledge."""
        if benchmark_name not in self.benchmarks:
            logger.error(f"Benchmark {benchmark_name} not found")
            return None
        
        benchmark_func = self.benchmarks[benchmark_name]
        
        start_time = time.time()
        try:
            result_data = benchmark_func(knowledge_id, knowledge_data, test_data or {})
            duration_ms = (time.time() - start_time) * 1000
            
            result = BenchmarkResult(
                benchmark_id=f"{benchmark_name}_{datetime.now(timezone.utc).timestamp()}",
                benchmark_type=self._infer_type(benchmark_name),
                knowledge_id=knowledge_id,
                score=result_data.get("score", 0.0),
                metrics=result_data.get("metrics", {}),
                duration_ms=duration_ms,
                metadata=result_data.get("metadata", {}),
            )
            
            if knowledge_id not in self.results:
                self.results[knowledge_id] = []
            self.results[knowledge_id].append(result)
            
            logger.info(f"Benchmark {benchmark_name} completed for {knowledge_id}: score={result.score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Benchmark {benchmark_name} failed: {e}")
            return None
    
    def run_all_benchmarks(
        self,
        knowledge_id: str,
        knowledge_data: Dict[str, Any],
        test_data: Optional[Dict[str, Any]] = None,
    ) -> List[BenchmarkResult]:
        """Run all benchmarks on knowledge."""
        results = []
        
        for benchmark_name in self.benchmarks:
            result = self.run_benchmark(
                benchmark_name,
                knowledge_id,
                knowledge_data,
                test_data,
            )
            if result:
                results.append(result)
        
        return results
    
    def _infer_type(self, benchmark_name: str) -> BenchmarkType:
        """Infer benchmark type from name."""
        if "accuracy" in benchmark_name:
            return BenchmarkType.ACCURACY
        elif "generalization" in benchmark_name:
            return BenchmarkType.GENERALIZATION
        elif "prediction" in benchmark_name:
            return BenchmarkType.PREDICTION
        elif "efficiency" in benchmark_name:
            return BenchmarkType.EFFICIENCY
        elif "robustness" in benchmark_name:
            return BenchmarkType.ROBUSTNESS
        else:
            return BenchmarkType.ACCURACY
    
    def _accuracy_benchmark(
        self,
        knowledge_id: str,
        knowledge_data: Dict[str, Any],
        test_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Benchmark knowledge accuracy."""
        # Simulate accuracy test
        correct = 0
        total = 100
        
        # In a real implementation, this would test the knowledge against labeled data
        # For now, use a heuristic based on knowledge confidence
        confidence = knowledge_data.get("confidence", 0.5)
        correct = int(total * confidence)
        
        score = correct / total
        
        return {
            "score": score,
            "metrics": {
                "correct": correct,
                "total": total,
                "error_rate": 1.0 - score,
            },
            "metadata": {
                "test_type": "simulated",
            },
        }
    
    def _generalization_benchmark(
        self,
        knowledge_id: str,
        knowledge_data: Dict[str, Any],
        test_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Benchmark knowledge generalization capability."""
        # Simulate generalization test
        # Test how well knowledge applies to new contexts
        applicable_contexts = knowledge_data.get("applicable_contexts", 5)
        total_contexts = 10
        
        score = applicable_contexts / total_contexts
        
        return {
            "score": score,
            "metrics": {
                "applicable_contexts": applicable_contexts,
                "total_contexts": total_contexts,
                "generalization_ratio": score,
            },
            "metadata": {
                "test_type": "simulated",
            },
        }
    
    def _prediction_benchmark(
        self,
        knowledge_id: str,
        knowledge_data: Dict[str, Any],
        test_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Benchmark knowledge prediction capability."""
        # Simulate prediction test
        predictions = knowledge_data.get("predictions", [])
        correct_predictions = int(len(predictions) * knowledge_data.get("confidence", 0.5))
        
        score = correct_predictions / len(predictions) if predictions else 0.0
        
        return {
            "score": score,
            "metrics": {
                "total_predictions": len(predictions),
                "correct_predictions": correct_predictions,
                "prediction_accuracy": score,
            },
            "metadata": {
                "test_type": "simulated",
            },
        }
    
    def _efficiency_benchmark(
        self,
        knowledge_id: str,
        knowledge_data: Dict[str, Any],
        test_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Benchmark knowledge efficiency (computational)."""
        # Simulate efficiency test
        # Measure time to apply knowledge
        complexity = knowledge_data.get("complexity", 1.0)
        
        # Lower complexity = higher efficiency
        score = max(0.0, 1.0 - complexity / 10.0)
        
        return {
            "score": score,
            "metrics": {
                "complexity": complexity,
                "efficiency_score": score,
            },
            "metadata": {
                "test_type": "simulated",
            },
        }
    
    def _robustness_benchmark(
        self,
        knowledge_id: str,
        knowledge_data: Dict[str, Any],
        test_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Benchmark knowledge robustness to noise/errors."""
        # Simulate robustness test
        # Test how well knowledge handles noisy inputs
        confidence = knowledge_data.get("confidence", 0.5)
        evidence_count = knowledge_data.get("evidence_count", 1)
        
        # More evidence = more robust
        robustness = min(1.0, confidence * (1.0 + evidence_count / 10.0))
        score = robustness / 2.0  # Normalize to 0-1
        
        return {
            "score": score,
            "metrics": {
                "confidence": confidence,
                "evidence_count": evidence_count,
                "robustness_score": robustness,
            },
            "metadata": {
                "test_type": "simulated",
            },
        }
    
    def get_results(
        self,
        knowledge_id: str,
        benchmark_type: Optional[BenchmarkType] = None,
    ) -> List[BenchmarkResult]:
        """Get benchmark results for knowledge."""
        if knowledge_id not in self.results:
            return []
        
        results = self.results[knowledge_id]
        
        if benchmark_type:
            results = [r for r in results if r.benchmark_type == benchmark_type]
        
        return results
    
    def get_average_score(
        self,
        knowledge_id: str,
        benchmark_type: Optional[BenchmarkType] = None,
    ) -> float:
        """Get average benchmark score for knowledge."""
        results = self.get_results(knowledge_id, benchmark_type)
        
        if not results:
            return 0.0
        
        return sum(r.score for r in results) / len(results)
    
    def compare_knowledge(
        self,
        knowledge_id_a: str,
        knowledge_id_b: str,
    ) -> Optional[Dict[str, Any]]:
        """Compare benchmark results between two knowledge items."""
        results_a = self.get_results(knowledge_id_a)
        results_b = self.get_results(knowledge_id_b)
        
        if not results_a or not results_b:
            return None
        
        avg_a = sum(r.score for r in results_a) / len(results_a)
        avg_b = sum(r.score for r in results_b) / len(results_b)
        
        comparison = {
            "knowledge_a": knowledge_id_a,
            "knowledge_b": knowledge_id_b,
            "average_score_a": avg_a,
            "average_score_b": avg_b,
            "winner": knowledge_id_a if avg_a > avg_b else knowledge_id_b,
            "benchmark_count_a": len(results_a),
            "benchmark_count_b": len(results_b),
        }
        
        return comparison
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get benchmark statistics."""
        total_runs = sum(len(results) for results in self.results.values())
        
        type_counts = {}
        for results_list in self.results.values():
            for result in results_list:
                type_counts[result.benchmark_type.value] = type_counts.get(result.benchmark_type.value, 0) + 1
        
        avg_duration = 0.0
        if total_runs > 0:
            total_duration = sum(
                r.duration_ms
                for results_list in self.results.values()
                for r in results_list
            )
            avg_duration = total_duration / total_runs
        
        return {
            "total_benchmarks": len(self.benchmarks),
            "total_runs": total_runs,
            "knowledge_items_tested": len(self.results),
            "by_type": type_counts,
            "average_duration_ms": avg_duration,
        }
