"""
Planning task dataset generator.

Generates multi-step planning tasks for testing long-horizon reasoning.
"""

import random
from typing import List, Dict, Any

from ..framework.dataset_manager import DatasetGenerator, DatasetItem


class PlanningDatasetGenerator(DatasetGenerator):
    """Generate planning tasks for testing multi-step reasoning."""
    
    def get_category(self) -> str:
        return "planning"
    
    def generate(self, num_items: int, seed: int) -> List[DatasetItem]:
        """Generate planning tasks."""
        random.seed(seed)
        
        items = []
        
        # Multi-step planning tasks
        for i in range(num_items // 2):
            item = self._generate_multi_step_task(i, seed)
            items.append(item)
        
        # Goal decomposition tasks
        for i in range(num_items // 2):
            item = self._generate_decomposition_task(i, seed)
            items.append(item)
        
        return items[:num_items]
    
    def _generate_multi_step_task(self, index: int, seed: int) -> DatasetItem:
        """Generate multi-step planning task."""
        plans = [
            {
                "goal": "Deploy a web application to production",
                "steps": [
                    "Write code",
                    "Write tests",
                    "Run tests",
                    "Build application",
                    "Deploy to staging",
                    "Test staging",
                    "Deploy to production",
                    "Monitor production",
                ],
                "question": "What must happen before deploying to production?",
                "answer": "deploy to staging and test staging"
            },
            {
                "goal": "Bake a cake",
                "steps": [
                    "Preheat oven",
                    "Mix ingredients",
                    "Pour into pan",
                    "Put in oven",
                    "Bake for specified time",
                    "Remove from oven",
                    "Let cool",
                    "Frost cake",
                ],
                "question": "What must happen before putting in oven?",
                "answer": "mix ingredients and pour into pan"
            },
            {
                "goal": "Plan a trip",
                "steps": [
                    "Choose destination",
                    "Book flights",
                    "Book accommodation",
                    "Plan activities",
                    "Pack luggage",
                    "Go to airport",
                    "Fly to destination",
                ],
                "question": "What must happen before going to airport?",
                "answer": "book flights, book accommodation, plan activities, and pack luggage"
            },
            {
                "goal": "Debug a software issue",
                "steps": [
                    "Reproduce the issue",
                    "Add logging",
                    "Run with logging",
                    "Analyze logs",
                    "Identify root cause",
                    "Write fix",
                    "Test fix",
                    "Deploy fix",
                ],
                "question": "What must happen before identifying root cause?",
                "answer": "reproduce issue, add logging, and run with logging"
            },
        ]
        
        plan = random.choice(plans)
        
        return DatasetItem(
            item_id=f"planning_multi_step_{index}",
            category="planning",
            difficulty="medium",
            task_data={
                "type": "multi_step_planning",
                "goal": plan["goal"],
                "steps": plan["steps"],
                "question": plan["question"],
            },
            ground_truth=plan["answer"],
            metadata={
                "num_steps": len(plan["steps"]),
                "seed": seed,
            },
        )
    
    def _generate_decomposition_task(self, index: int, seed: int) -> DatasetItem:
        """Generate goal decomposition task."""
        decompositions = [
            {
                "goal": "Build a house",
                "subgoals": [
                    "Design the house",
                    "Get permits",
                    "Prepare foundation",
                    "Frame the structure",
                    "Install utilities",
                    "Finish interior",
                    "Landscaping",
                ],
                "question": "What are the main subgoals for building a house?",
            },
            {
                "goal": "Learn a programming language",
                "subgoals": [
                    "Learn syntax",
                    "Practice basic programs",
                    "Learn data structures",
                    "Practice algorithms",
                    "Build projects",
                    "Read existing code",
                    "Contribute to open source",
                ],
                "question": "What are the main subgoals for learning a programming language?",
            },
            {
                "goal": "Start a business",
                "subgoals": [
                    "Develop business idea",
                    "Create business plan",
                    "Secure funding",
                    "Register business",
                    "Build product/service",
                    "Market to customers",
                    "Scale operations",
                ],
                "question": "What are the main subgoals for starting a business?",
            },
        ]
        
        decomp = random.choice(decompositions)
        
        return DatasetItem(
            item_id=f"planning_decomposition_{index}",
            category="planning",
            difficulty="medium",
            task_data={
                "type": "goal_decomposition",
                "goal": decomp["goal"],
                "question": decomp["question"],
            },
            ground_truth=decomp["subgoals"],
            metadata={
                "num_subgoals": len(decomp["subgoals"]),
                "seed": seed,
            },
        )
