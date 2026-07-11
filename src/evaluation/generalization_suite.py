'''generalization_suite.py

Runs a suite of cross‑domain generalization benchmarks for the cognitive core.
Each test loads a predefined problem set from the ``novel_domain_benchmark`` module
and evaluates the system's ability to transfer learned skills.
''' 

from typing import List, Dict
from .novel_domain_benchmark import load_benchmarks
from .transfer_validation import TransferValidator

class GeneralizationSuite:
    def __init__(self, transfer_validator: TransferValidator):
        self.validator = transfer_validator
        self.benchmarks = load_benchmarks()

    def run(self) -> List[Dict[str, float]]:
        """Execute all benchmarks and return a list of metric dicts.
        
        Example result entry: {"benchmark": "graph_reasoning", "accuracy": 0.78}
        """
        results = []
        for bench in self.benchmarks:
            # Each benchmark provides a ``run`` method returning predictions.
            predictions = bench.run()
            metrics = self.validator.validate(predictions)
            metrics["benchmark"] = bench.name
            results.append(metrics)
        return results

    def __repr__(self):
        return f"GeneralizationSuite(benchmarks={len(self.benchmarks)})"
