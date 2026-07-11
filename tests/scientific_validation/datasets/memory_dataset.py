"""
Memory-dependent task dataset generator.

Generates tasks that require memory to solve correctly.
"""

import random
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..framework.dataset_manager import DatasetGenerator, DatasetItem


class MemoryDatasetGenerator(DatasetGenerator):
    """Generate memory-dependent tasks for ablation studies."""
    
    def get_category(self) -> str:
        return "memory"
    
    def generate(self, num_items: int, seed: int) -> List[DatasetItem]:
        """Generate memory-dependent tasks."""
        random.seed(seed)
        
        items = []
        
        # Personal information recall tasks
        for i in range(num_items // 4):
            item = self._generate_personal_info_task(i, seed)
            items.append(item)
        
        # Context retention tasks
        for i in range(num_items // 4):
            item = self._generate_context_retention_task(i, seed)
            items.append(item)
        
        # Procedural memory tasks
        for i in range(num_items // 4):
            item = self._generate_procedural_memory_task(i, seed)
            items.append(item)
        
        # Semantic memory tasks
        for i in range(num_items // 4):
            item = self._generate_semantic_memory_task(i, seed)
            items.append(item)
        
        return items[:num_items]
    
    def _generate_personal_info_task(self, index: int, seed: int) -> DatasetItem:
        """Generate personal information recall task."""
        # Generate random personal facts
        names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        cities = ["New York", "London", "Paris", "Tokyo", "Sydney", "Berlin", "Toronto"]
        birthdays = [
            "January 15", "February 28", "March 10", "April 4", "May 22",
            "June 30", "July 7", "August 19", "September 3", "October 31",
            "November 12", "December 25"
        ]
        occupations = ["engineer", "doctor", "teacher", "artist", "scientist", "writer"]
        
        name = random.choice(names)
        city = random.choice(cities)
        birthday = random.choice(birthdays)
        occupation = random.choice(occupations)
        
        # Create conversation context
        conversation = [
            f"User: Hi, I'm {name}.",
            f"Assistant: Nice to meet you, {name}!",
            f"User: I live in {city}.",
            f"Assistant: {city} is a great place!",
            f"User: My birthday is {birthday}.",
            f"Assistant: I'll remember that!",
            f"User: I work as a {occupation}.",
            f"Assistant: That's interesting!",
        ]
        
        # Add distractor interactions
        distractors = [
            "User: What's the weather like?",
            "Assistant: I don't have access to weather data.",
            "User: Can you help me with math?",
            "Assistant: Sure, what do you need help with?",
            "User: Never mind.",
            "Assistant: Okay, let me know if you need anything.",
        ]
        
        num_distractors = random.randint(5, 15)
        for _ in range(num_distractors):
            conversation.extend(random.sample(distractors, 2))
        
        # Generate question
        question_type = random.choice(["birthday", "city", "occupation", "name"])
        
        if question_type == "birthday":
            question = f"When is {name}'s birthday?"
            answer = birthday
        elif question_type == "city":
            question = f"Where does {name} live?"
            answer = city
        elif question_type == "occupation":
            question = f"What does {name} do for work?"
            answer = occupation
        else:
            question = f"What is the user's name?"
            answer = name
        
        return DatasetItem(
            item_id=f"memory_personal_{index}",
            category="memory",
            difficulty="easy",
            task_data={
                "type": "personal_info_recall",
                "conversation": conversation,
                "question": question,
                "distractor_count": num_distractors,
            },
            ground_truth=answer,
            metadata={
                "question_type": question_type,
                "seed": seed,
            },
        )
    
    def _generate_context_retention_task(self, index: int, seed: int) -> DatasetItem:
        """Generate context retention task."""
        # Generate a multi-step task with context
        task_type = random.choice(["recipe", "directions", "story", "instructions"])
        
        if task_type == "recipe":
            ingredients = random.sample(
                ["flour", "sugar", "eggs", "butter", "milk", "vanilla", "chocolate", "salt"],
                k=random.randint(3, 6)
            )
            steps = [
                f"Mix {ingredients[0]} and {ingredients[1]}.",
                f"Add {ingredients[2]} and stir.",
                f"Bake for {random.randint(20, 45)} minutes at {random.randint(350, 400)}°F.",
            ]
            question = f"What ingredient was mentioned first?"
            answer = ingredients[0]
        
        elif task_type == "directions":
            locations = random.sample(
                ["library", "park", "cafe", "museum", "school", "hospital"],
                k=random.randint(3, 5)
            )
            steps = [
                f"Start at the {locations[0]}.",
                f"Walk north to the {locations[1]}.",
                f"Turn left and go to the {locations[2]}.",
            ]
            question = f"What was the second location mentioned?"
            answer = locations[1]
        
        elif task_type == "story":
            characters = random.sample(
                ["John", "Mary", "Tom", "Lisa", "Mike", "Sarah"],
                k=random.randint(2, 4)
            )
            story = [
                f"{characters[0]} went to the store.",
                f"{characters[1]} met {characters[0]} there.",
                f"They bought groceries together.",
            ]
            question = f"Who went to the store first?"
            answer = characters[0]
        
        else:  # instructions
            steps = [
                "First, turn on the device.",
                "Then, press the blue button.",
                "Wait for the light to flash.",
                "Finally, enter your code.",
            ]
            question = "What do you do after turning on the device?"
            answer = "press the blue button"
        
        return DatasetItem(
            item_id=f"memory_context_{index}",
            category="memory",
            difficulty="medium",
            task_data={
                "type": "context_retention",
                "content": steps if task_type != "story" else story,
                "question": question,
            },
            ground_truth=answer,
            metadata={
                "task_type": task_type,
                "seed": seed,
            },
        )
    
    def _generate_procedural_memory_task(self, index: int, seed: int) -> DatasetItem:
        """Generate procedural memory task."""
        procedures = [
            {
                "name": "making coffee",
                "steps": ["grind beans", "heat water", "add grounds", "pour water"],
                "question": "What comes after grinding beans?",
                "answer": "heat water"
            },
            {
                "name": "tying shoes",
                "steps": ["cross laces", "make loop", "wrap around", "pull tight"],
                "question": "What is the first step?",
                "answer": "cross laces"
            },
            {
                "name": "sending email",
                "steps": ["open email app", "compose new", "add recipient", "write message", "send"],
                "question": "What is the last step?",
                "answer": "send"
            },
        ]
        
        procedure = random.choice(procedures)
        
        return DatasetItem(
            item_id=f"memory_procedural_{index}",
            category="memory",
            difficulty="easy",
            task_data={
                "type": "procedural_memory",
                "procedure": procedure["name"],
                "steps": procedure["steps"],
                "question": procedure["question"],
            },
            ground_truth=procedure["answer"],
            metadata={
                "procedure": procedure["name"],
                "seed": seed,
            },
        )
    
    def _generate_semantic_memory_task(self, index: int, seed: int) -> DatasetItem:
        """Generate semantic memory task."""
        facts = [
            {
                "fact": "The capital of France is Paris.",
                "question": "What is the capital of France?",
                "answer": "Paris"
            },
            {
                "fact": "Water boils at 100 degrees Celsius.",
                "question": "At what temperature does water boil (in Celsius)?",
                "answer": "100"
            },
            {
                "fact": "The Earth has one moon.",
                "question": "How many moons does Earth have?",
                "answer": "1"
            },
            {
                "fact": "Photosynthesis converts sunlight into energy.",
                "question": "What does photosynthesis convert sunlight into?",
                "answer": "energy"
            },
        ]
        
        fact = random.choice(facts)
        
        return DatasetItem(
            item_id=f"memory_semantic_{index}",
            category="memory",
            difficulty="easy",
            task_data={
                "type": "semantic_memory",
                "fact": fact["fact"],
                "question": fact["question"],
            },
            ground_truth=fact["answer"],
            metadata={
                "seed": seed,
            },
        )
