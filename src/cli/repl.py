from src.cli.command_router import CommandRouter
from src.cli.session import Session
from src.cli.history import History

class REPL:
    def __init__(self):
        self.session = Session()
        self.history = History()
        self.router = CommandRouter(self.session, self.history)

    def loop(self):
        while True:
            try:
                user_input = input("\n> ")
                if not user_input.strip():
                    continue
                if user_input.strip().lower() in ("exit", "quit"):
                    break
                self.router.route(user_input)
                self.history.add_command(user_input)
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                print(f"System Error: {e}")
