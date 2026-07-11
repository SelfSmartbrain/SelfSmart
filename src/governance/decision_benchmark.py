"""decision_benchmark.py

Phase 16G: Decision Benchmark

Benchmarks decision quality against standards and historical performance.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Result of benchmarking a decision."""
    decision_id: str = ""
    benchmark_type: str = ""
    score: float = 0.0
    percentile: float = 0.0  # Percentile rank against historical decisions
    comparison: str = ""  # above_average, average, below_average
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "benchmark_type": self.benchmark_type,
            "score": self.score,
            "percentile": self.percentile,
            "comparison": self.comparison,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class DecisionBenchmark:
    """Benchmarks decisions against standards and history."""
    
    def __init__(self):
        self.benchmarks: Dict[str, BenchmarkResult] = {}
        self.historical_fitness: List[float] = []
        self.standards: Dict[str, float] = {
            "min_accuracy": 0.6,
            "max_risk": 0.4,
            "min_efficiency": 0.5,
            "min_fitness": 0.6,
        }
        logger.info("DecisionBenchmark initialized")
    
    def add_historical_fitness(self, fitness_score: float) -> None:
        """Add a historical fitness score for comparison."""
        self.historical_fitness.append(fitness_score)
    
    def benchmark_decision(
        self,
        decision_data: Dict[str, Any],
        fitness: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkResult:
        """Benchmark a decision against standards and history."""
        decision_id = decision_data.get("id", "")
        
        if fitness is None:
            # Calculate fitness if not provided
            from src.governance.decision_fitness import DecisionFitnessCalculator
            calculator = DecisionFitnessCalculator()
            fitness_obj = calculator.calculate_fitness(decision_data)
            fitness = fitness_obj.to_dict()
        
        result = BenchmarkResult(decision_id=decision_id)
        
        # Benchmark against standards
        result = self._benchmark_against_standards(result, fitness)
        
        # Benchmark against history
        result = self._benchmark_against_history(result, fitness)
        
        # Generate analysis
        result.strengths = self._identify_strengths(fitness)
        result.weaknesses = self._identify_weaknesses(fitness)
        result.recommendations = self._generate_recommendations(fitness)
        
        # Store result
        self.benchmarks[decision_id] = result
        
        logger.info(f"Benchmarked decision {decision_id}: {result.comparison}")
        
        return result
    
    def _benchmark_against_standards(
        self,
        result: BenchmarkResult,
        fitness: Dict[str, Any],
    ) -> BenchmarkResult:
        """Benchmark decision against defined standards."""
        result.benchmark_type = "standards"
        
        passed_standards = []
        failed_standards = []
        
        # Check accuracy
        accuracy = fitness.get("accuracy", 0)
        if accuracy >= self.standards["min_accuracy"]:
            passed_standards.append("accuracy")
        else:
            failed_standards.append("accuracy")
        
        # Check risk
        risk = fitness.get("risk_score", 0)
        if risk <= self.standards["max_risk"]:
            passed_standards.append("risk")
        else:
            failed_standards.append("risk")
        
        # Check efficiency
        efficiency = fitness.get("efficiency_score", 0)
        if efficiency >= self.standards["min_efficiency"]:
            passed_standards.append("efficiency")
        else:
            failed_standards.append("efficiency")
        
        # Check overall fitness
        overall = fitness.get("overall_fitness", 0)
        if overall >= self.standards["min_fitness"]:
            passed_standards.append("overall_fitness")
        else:
            failed_standards.append("overall_fitness")
        
        # Calculate score
        total_standards = len(self.standards)
        result.score = len(passed_standards) / total_standards if total_standards > 0 else 0
        
        # Determine comparison
        if result.score >= 0.8:
            result.comparison = "exceeds_standards"
        elif result.score >= 0.6:
            result.comparison = "meets_standards"
        else:
            result.comparison = "below_standards"
        
        return result
    
    def _benchmark_against_history(
        self,
        result: BenchmarkResult,
        fitness: Dict[str, Any],
    ) -> BenchmarkResult:
        """Benchmark decision against historical performance."""
        if not self.historical_fitness:
            return result
        
        overall_fitness = fitness.get("overall_fitness", 0)
        
        # Calculate percentile
        sorted_history = sorted(self.historical_fitness)
        rank = sum(1 for f in sorted_history if f < overall_fitness)
        percentile = rank / len(sorted_history) if sorted_history else 0.5
        
        result.percentile = percentile
        
        # Update comparison based on history
        if percentile >= 0.75:
            result.comparison = "above_average"
        elif percentile >= 0.25:
            result.comparison = "average"
        else:
            result.comparison = "below_average"
        
        return result
    
    def _identify_strengths(self, fitness: Dict[str, Any]) -> List[str]:
        """Identify strengths of the decision."""
        strengths = []
        
        if fitness.get("accuracy", 0) > 0.8:
            strengths.append("High accuracy in achieving goals")
        
        if fitness.get("risk_score", 0) < 0.3:
            strengths.append("Low risk profile")
        
        if fitness.get("impact_score", 0) > 0.7:
            strengths.append("High impact potential")
        
        if fitness.get("efficiency_score", 0) > 0.7:
            strengths.append("High resource efficiency")
        
        if fitness.get("regret_score", 0) < 0.2:
            strengths.append("Low opportunity cost")
        
        return strengths
    
    def _identify_weaknesses(self, fitness: Dict[str, Any]) -> List[str]:
        """Identify weaknesses of the decision."""
        weaknesses = []
        
        if fitness.get("accuracy", 0) < 0.5:
            weaknesses.append("Low accuracy in achieving goals")
        
        if fitness.get("risk_score", 0) > 0.6:
            weaknesses.append("High risk profile")
        
        if fitness.get("impact_score", 0) < 0.4:
            weaknesses.append("Low impact potential")
        
        if fitness.get("efficiency_score", 0) < 0.4:
            weaknesses.append("Low resource efficiency")
        
        if fitness.get("regret_score", 0) > 0.4:
            weaknesses.append("High opportunity cost")
        
        return weaknesses
    
    def _generate_recommendations(self, fitness: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on fitness."""
        recommendations = []
        
        if fitness.get("accuracy", 0) < 0.6:
            recommendations.append("Improve goal alignment and outcome prediction")
        
        if fitness.get("risk_score", 0) > 0.5:
            recommendations.append("Consider lower-risk alternatives or add mitigation strategies")
        
        if fitness.get("impact_score", 0) < 0.5:
            recommendations.append("Explore higher-impact options")
        
        if fitness.get("efficiency_score", 0) < 0.5:
            recommendations.append("Optimize resource allocation")
        
        if fitness.get("regret_score", 0) > 0.3:
            recommendations.append("Consider alternative options more carefully")
        
        if not recommendations:
            recommendations.append("Decision performs well across all metrics")
        
        return recommendations
    
    def update_standards(self, new_standards: Dict[str, float]) -> None:
        """Update benchmark standards."""
        self.standards.update(new_standards)
        logger.info("Updated benchmark standards")
    
    def get_benchmark(self, decision_id: str) -> Optional[BenchmarkResult]:
        """Get benchmark result for a decision."""
        return self.benchmarks.get(decision_id)
    
    def get_benchmark_statistics(self) -> Dict[str, Any]:
        """Get statistics about benchmarks."""
        total_benchmarks = len(self.benchmarks)
        
        if total_benchmarks == 0:
            return {"total_benchmarks": 0}
        
        by_comparison = {
            comp: len([b for b in self.benchmarks.values() if b.comparison == comp])
            for comp in ["above_average", "average", "below_average", "exceeds_standards", "meets_standards", "below_standards"]
        }
        
        avg_score = sum(b.score for b in self.benchmarks.values()) / total_benchmarks
        
        return {
            "total_benchmarks": total_benchmarks,
            "by_comparison": by_comparison,
            "average_score": avg_score,
            "historical_decisions": len(self.historical_fitness),
            "current_standards": self.standards,
        }
