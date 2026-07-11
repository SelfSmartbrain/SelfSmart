'''curriculum_engine.py

Orders synthetic problems by difficulty using a simple curriculum schedule.
Keeps track of the learner's performance and gradually increases problem complexity.
''' 

from typing import List, Dict
import random

class CurriculumEngine:
    def __init__(self):
        # Define difficulty levels (1=easiest, 5=hardest)
        self.difficulty_levels = {1: [], 2: [], 3: [], 4: [], 5: []}
        # Populate with placeholder problem identifiers (in real system these would be problem configs)
        for lvl in self.difficulty_levels:
            self.difficulty_levels[lvl] = [f"problem_{lvl}_{i}" for i in range(10)]
        self.current_level = 1
        self.success_streak = 0
        self.required_streak = 3  # advance after 3 consecutive successes

    def record_outcome(self, problem_id: str, success: bool):
        """Update curriculum based on outcome of a problem.
        
        If the learner succeeds, increase streak; otherwise reset.
        When streak reaches required threshold, move to next difficulty.
        """
        if success:
            self.success_streak += 1
            if self.success_streak >= self.required_streak and self.current_level < max(self.difficulty_levels):
                self.current_level += 1
                self.success_streak = 0
        else:
            self.success_streak = 0
            # Optionally step back a level on repeated failures
            if self.current_level > 1:
                self.current_level -= 1

    def get_next_problem(self) -> str:
        """Return a randomly selected problem ID from the current difficulty level."""
        pool = self.difficulty_levels.get(self.current_level, [])
        if not pool:
            raise ValueError("No problems available for current difficulty level")
        return random.choice(pool)

    def __repr__(self):
        return f"CurriculumEngine(level={self.current_level}, streak={self.success_streak})"
