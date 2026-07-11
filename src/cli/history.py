class History:
    def __init__(self):
        self.command_history = []
        self.agent_history = []
        self.execution_history = []

    def add_command(self, command: str):
        self.command_history.append(command)
