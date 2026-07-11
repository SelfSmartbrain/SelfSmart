import os
import uuid

class Session:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.working_directory = os.getcwd()
        self.active_project = None
        self.current_goal = None
        self.context = {}
