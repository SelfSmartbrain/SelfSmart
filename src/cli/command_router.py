import os
import shlex
from src.tools.shell_tool import ShellTool
from src.tools.filesystem_tool import FilesystemTool

class CommandRouter:
    def __init__(self, session, history):
        self.session = session
        self.history = history
        self.shell_tool = ShellTool(cwd=self.session.working_directory)
        self.fs_tool = FilesystemTool(base_dir=self.session.working_directory)

    def route(self, command: str):
        try:
            parts = shlex.split(command)
        except ValueError as e:
            print(f"Error parsing command: {e}")
            return
            
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "ask":
            print("Routing to ask command...")
        elif cmd == "run":
            if not args:
                print("Usage: run <shell_command>")
                return
            shell_cmd = " ".join(args)
            result = self.shell_tool.run_command(shell_cmd)
            if result["stdout"]:
                print(result["stdout"], end="")
            if result["stderr"]:
                print(result["stderr"], end="")
        elif cmd == "read":
            if not args:
                print("Usage: read <filepath>")
                return
            print(self.fs_tool.read_file(args[0]))
        elif cmd == "plan":
            print("Routing to plan command...")
        elif cmd == "explain":
            print("Routing to explain command...")
        elif cmd == "memory":
            print("Routing to memory command...")
        elif cmd == "status":
            print("Routing to status command...")
        elif cmd == "project":
            print("Routing to project command...")
        elif cmd == "learn":
            print("Routing to learn command...")
        elif cmd == "autonomous":
            print("Entering autonomous mode...")
        else:
            print(f"Unknown command: {cmd}")
