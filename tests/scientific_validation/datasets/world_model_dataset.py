"""
World model task dataset generator.

Generates tasks for testing prediction, causal reasoning, and outcome simulation.
"""

import random
from typing import List, Dict, Any

from ..framework.dataset_manager import DatasetGenerator, DatasetItem


class WorldModelDatasetGenerator(DatasetGenerator):
    """Generate world model tasks for testing prediction capabilities."""
    
    def get_category(self) -> str:
        return "world_model"
    
    def generate(self, num_items: int, seed: int) -> List[DatasetItem]:
        """Generate world model tasks."""
        random.seed(seed)
        
        items = []
        
        # Prediction tasks
        for i in range(num_items // 3):
            item = self._generate_prediction_task(i, seed)
            items.append(item)
        
        # Causal reasoning tasks
        for i in range(num_items // 3):
            item = self._generate_causal_task(i, seed)
            items.append(item)
        
        # Outcome simulation tasks
        for i in range(num_items // 3):
            item = self._generate_outcome_task(i, seed)
            items.append(item)
        
        return items[:num_items]
    
    def _generate_prediction_task(self, index: int, seed: int) -> DatasetItem:
        """Generate prediction task."""
        scenarios = [
            {
                "scenario": "If you drop a glass from a height of 2 meters",
                "outcome": "it will likely break",
                "probability": 0.9,
                "question": "What will happen to the glass?"
            },
            {
                "scenario": "If you water a plant regularly",
                "outcome": "it will grow",
                "probability": 0.8,
                "question": "What will happen to the plant?"
            },
            {
                "scenario": "If you leave ice cream in the sun",
                "outcome": "it will melt",
                "probability": 0.95,
                "question": "What will happen to the ice cream?"
            },
            {
                "scenario": "If you study for a test",
                "outcome": "you will likely perform better",
                "probability": 0.7,
                "question": "What will happen to your test performance?"
            },
            {
                "scenario": "If you don't sleep for 24 hours",
                "outcome": "you will feel tired",
                "probability": 0.95,
                "question": "How will you feel?"
            },
        ]
        
        scenario = random.choice(scenarios)
        
        return DatasetItem(
            item_id=f"world_model_prediction_{index}",
            category="world_model",
            difficulty="easy",
            task_data={
                "type": "prediction",
                "scenario": scenario["scenario"],
                "question": scenario["question"],
            },
            ground_truth={
                "outcome": scenario["outcome"],
                "probability": scenario["probability"],
            },
            metadata={
                "probability": scenario["probability"],
                "seed": seed,
            },
        )
    
    def _generate_causal_task(self, index: int, seed: int) -> DatasetItem:
        """Generate causal reasoning task."""
        causal_chains = [
            {
                "chain": ["rain", "wet ground", "slippery surface", "falling risk"],
                "question": "What causes the ground to be wet?",
                "answer": "rain"
            },
            {
                "chain": ["lack of sleep", "fatigue", "reduced concentration", "errors"],
                "question": "What causes reduced concentration?",
                "answer": "fatigue"
            },
            {
                "chain": ["high temperature", "expansion", "pressure increase", "explosion risk"],
                "question": "What causes pressure to increase?",
                "answer": "expansion"
            },
            {
                "chain": ["exercise", "increased heart rate", "sweating", "cooling"],
                "question": "What causes sweating?",
                "answer": "increased heart rate"
            },
        ]
        
        chain = random.choice(causal_chains)
        
        return DatasetItem(
            item_id=f"world_model_causal_{index}",
            category="world_model",
            difficulty="medium",
            task_data={
                "type": "causal_reasoning",
                "causal_chain": chain["chain"],
                "question": chain["question"],
            },
            ground_truth=chain["answer"],
            metadata={
                "chain_length": len(chain["chain"]),
                "seed": seed,
            },
        )
    
    def _generate_outcome_task(self, index: int, seed: int) -> DatasetItem:
        """Generate outcome simulation task."""
        simulations = [
            {
                "initial_state": "A ball is at the top of a hill",
                "action": "push the ball",
                "expected_outcome": "the ball rolls down",
                "question": "What happens after pushing the ball?"
            },
            {
                "initial_state": "A light switch is off",
                "action": "flip the switch",
                "expected_outcome": "the light turns on",
                "question": "What happens after flipping the switch?"
            },
            {
                "initial_state": "A car is moving at 60 mph",
                "action": "apply brakes",
                "expected_outcome": "the car slows down",
                "question": "What happens after applying brakes?"
            },
            {
                "initial_state": "A plant is in a dark room",
                "action": "move it to sunlight",
                "expected_outcome": "it will grow towards the light",
                "question": "What happens after moving the plant to sunlight?"
            },
        ]
        
        simulation = random.choice(simulations)
        
        return DatasetItem(
            item_id=f"world_model_outcome_{index}",
            category="world_model",
            difficulty="easy",
            task_data={
                "type": "outcome_simulation",
                "initial_state": simulation["initial_state"],
                "action": simulation["action"],
                "question": simulation["question"],
            },
            ground_truth=simulation["expected_outcome"],
            metadata={
                "seed": seed,
            },
        )
