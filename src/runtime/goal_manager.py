class GoalManager:
    def __init__(self):
        self.active_goals = []
        self.completed_goals = []
        self.blocked_goals = []
        self.failed_goals = []

    def add_goal(self, goal):
        self.active_goals.append(goal)
