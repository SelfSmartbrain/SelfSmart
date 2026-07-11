"""
Concept engine task dataset generator.

Generates tasks for testing transfer learning, concept composition, and hierarchical reasoning.
"""

import random
from typing import List, Dict, Any

from ..framework.dataset_manager import DatasetGenerator, DatasetItem


class ConceptDatasetGenerator(DatasetGenerator):
    """Generate concept-dependent tasks for testing the concept engine."""
    
    def get_category(self) -> str:
        return "concepts"
    
    def generate(self, num_items: int, seed: int) -> List[DatasetItem]:
        """Generate concept-dependent tasks."""
        random.seed(seed)
        
        items = []
        
        # Hierarchical reasoning tasks
        for i in range(num_items // 3):
            item = self._generate_hierarchy_task(i, seed)
            items.append(item)
        
        # Concept composition tasks
        for i in range(num_items // 3):
            item = self._generate_composition_task(i, seed)
            items.append(item)
        
        # Analogy tasks
        for i in range(num_items // 3):
            item = self._generate_analogy_task(i, seed)
            items.append(item)
        
        return items[:num_items]
    
    def _generate_hierarchy_task(self, index: int, seed: int) -> DatasetItem:
        """Generate hierarchical reasoning task."""
        hierarchies = [
            {
                "hierarchy": ["animal", "mammal", "dog", "poodle"],
                "questions": [
                    ("Is a dog an animal?", True),
                    ("Is a poodle a mammal?", True),
                    ("Is a mammal a dog?", False),
                ]
            },
            {
                "hierarchy": ["vehicle", "car", "sedan", "Toyota Camry"],
                "questions": [
                    ("Is a sedan a vehicle?", True),
                    ("Is a car a sedan?", False),
                    ("Is a Toyota Camry a car?", True),
                ]
            },
            {
                "hierarchy": ["food", "fruit", "apple", "Granny Smith"],
                "questions": [
                    ("Is an apple a food?", True),
                    ("Is a fruit an apple?", False),
                    ("Is a Granny Smith a fruit?", True),
                ]
            },
            {
                "hierarchy": ["building", "house", "room", "bedroom"],
                "questions": [
                    ("Is a bedroom a building?", True),
                    ("Is a house a room?", False),
                    ("Is a room a house?", True),
                ]
            },
        ]
        
        hierarchy_data = random.choice(hierarchies)
        question, answer = random.choice(hierarchy_data["questions"])
        
        return DatasetItem(
            item_id=f"concept_hierarchy_{index}",
            category="concepts",
            difficulty="easy",
            task_data={
                "type": "hierarchical_reasoning",
                "hierarchy": hierarchy_data["hierarchy"],
                "question": question,
            },
            ground_truth=answer,
            metadata={
                "hierarchy": hierarchy_data["hierarchy"],
                "seed": seed,
            },
        )
    
    def _generate_composition_task(self, index: int, seed: int) -> DatasetItem:
        """Generate concept composition task."""
        compositions = [
            {
                "concepts": ["red", "fruit"],
                "composed": "apple",
                "question": "What is a red fruit?",
                "answer": "apple"
            },
            {
                "concepts": ["flying", "mammal"],
                "composed": "bat",
                "question": "What is a flying mammal?",
                "answer": "bat"
            },
            {
                "concepts": ["large", "cat"],
                "composed": "lion",
                "question": "What is a large cat?",
                "answer": "lion"
            },
            {
                "concepts": ["water", "vehicle"],
                "composed": "boat",
                "question": "What is a water vehicle?",
                "answer": "boat"
            },
            {
                "concepts": ["cold", "sweet", "food"],
                "composed": "ice cream",
                "question": "What is cold, sweet food?",
                "answer": "ice cream"
            },
        ]
        
        composition = random.choice(compositions)
        
        return DatasetItem(
            item_id=f"concept_composition_{index}",
            category="concepts",
            difficulty="medium",
            task_data={
                "type": "concept_composition",
                "concepts": composition["concepts"],
                "question": composition["question"],
            },
            ground_truth=composition["answer"],
            metadata={
                "concepts": composition["concepts"],
                "seed": seed,
            },
        )
    
    def _generate_analogy_task(self, index: int, seed: int) -> DatasetItem:
        """Generate analogy task."""
        analogies = [
            {
                "premise": ("dog", "puppy"),
                "question": ("cat", "?"),
                "answer": "kitten",
                "relation": "young"
            },
            {
                "premise": ("doctor", "hospital"),
                "question": ("teacher", "?"),
                "answer": "school",
                "relation": "workplace"
            },
            {
                "premise": ("king", "queen"),
                "question": ("man", "?"),
                "answer": "woman",
                "relation": "gender"
            },
            {
                "premise": ("car", "wheel"),
                "question": ("bicycle", "?"),
                "answer": "tire",
                "relation": "part"
            },
            {
                "premise": ("book", "read"),
                "question": ("music", "?"),
                "answer": "listen",
                "relation": "action"
            },
        ]
        
        analogy = random.choice(analogies)
        
        return DatasetItem(
            item_id=f"concept_analogy_{index}",
            category="concepts",
            difficulty="medium",
            task_data={
                "type": "analogy",
                "premise": analogy["premise"],
                "question": analogy["question"],
                "relation": analogy["relation"],
            },
            ground_truth=analogy["answer"],
            metadata={
                "relation": analogy["relation"],
                "seed": seed,
            },
        )
