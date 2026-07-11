"""TUI screens for ModelX."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Static,
    Input,
    Label,
    TextArea,
    Select,
    LoadingIndicator,
)

from src.cli.api_client import ModelXClient

# Command categories and their commands
COMMAND_CATEGORIES = {
    "autonomous": {
        "description": "Autonomous execution operations",
        "commands": ["run", "status"],
    },
    "cognitive": {
        "description": "Cognitive OS operations",
        "commands": ["status", "reason", "attend"],
    },
    "concepts": {
        "description": "Concept graph operations",
        "commands": ["create", "search", "relate", "list", "lineage"],
    },
    "config": {
        "description": "Manage ModelX CLI configuration",
        "commands": ["add_provider", "remove_provider", "list_providers", "set", "get"],
    },
    "develop": {
        "description": "Autonomous development operations",
        "commands": ["analyze", "optimize", "improve"],
    },
    "discover": {
        "description": "Scientific discovery loop operations",
        "commands": ["run"],
    },
    "goal": {
        "description": "Manage goals",
        "commands": ["create", "list", "get", "delete"],
    },
    "identity": {
        "description": "Identity and mission operations",
        "commands": ["status", "create_mission", "missions"],
    },
    "knowledge": {
        "description": "Knowledge compression and distillation operations",
        "commands": ["compress", "abstract", "distill"],
    },
    "lineage": {
        "description": "Knowledge lineage tracking operations",
        "commands": [],
    },
    "memory": {
        "description": "Manage memory operations",
        "commands": ["add", "search", "list"],
    },
    "meta": {
        "description": "Meta-learning operations",
        "commands": ["analyze", "strategies"],
    },
    "reflect": {
        "description": "Reflection operations",
        "commands": ["create", "list"],
    },
    "research": {
        "description": "Research program operations",
        "commands": ["create_program", "schedule", "list"],
    },
    "society": {
        "description": "Agent society operations",
        "commands": ["create", "list", "add_agent"],
    },
    "swarm": {
        "description": "Swarm orchestration operations",
        "commands": ["submit", "status", "metrics", "scale", "initialize", "shutdown"],
    },
    "task": {
        "description": "Manage tasks",
        "commands": ["create", "list", "get", "execute"],
    },
    "theories": {
        "description": "Theory formation operations",
        "commands": ["create", "strengthen", "weaken", "list", "validate"],
    },
    "vision": {
        "description": "Vision processing operations",
        "commands": ["analyze", "capture", "detect"],
    },
}


class MainScreen(Screen):
    """Main TUI screen with category sidebar and command grid."""

    CSS = """
    MainScreen {
        layout: horizontal;
    }
    
    #sidebar {
        width: 30;
        background: $surface;
        dock: left;
    }
    
    #main-content {
        width: 1fr;
    }
    
    .category-button {
        width: 100%;
        margin: 1;
    }
    
    .command-button {
        width: 20;
        height: 3;
        margin: 1;
    }
    
    #command-grid {
        height: 1fr;
    }
    
    #description {
        height: 3;
        background: $surface;
        padding: 1;
        content-align: center middle;
    }
    """

    def __init__(self, client: ModelXClient) -> None:
        super().__init__()
        self.client = client
        self.selected_category = "autonomous"

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        with Horizontal():
            # Sidebar with categories
            with Vertical(id="sidebar"):
                yield Static("Categories", classes="header")
                for category in COMMAND_CATEGORIES.keys():
                    yield Button(
                        category,
                        id=f"cat-{category}",
                        classes="category-button",
                        variant="primary" if category == self.selected_category else "default",
                    )
                yield Static()  # Spacer
                yield Button("Exit", id="exit-button", variant="error")
            
            # Main content area
            with Vertical(id="main-content"):
                yield Header()
                yield Static(
                    COMMAND_CATEGORIES[self.selected_category]["description"],
                    id="description",
                )
                yield Vertical(id="command-grid")
                yield Footer()

    def on_mount(self) -> None:
        """Initialize commands after mount."""
        self._render_commands(self.selected_category)

    def _render_commands(self, category: str) -> None:
        """Render command buttons for a category."""
        # Clear existing buttons
        command_grid = self.query_one("#command-grid", Vertical)
        command_grid.remove_children()
        
        commands = COMMAND_CATEGORIES[category]["commands"]
        if commands:
            for cmd in commands:
                command_grid.mount(
                    Button(
                        cmd,
                        id=f"cmd-{category}-{cmd}",
                        classes="command-button",
                    )
                )
        else:
            command_grid.mount(Static("No commands available"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id and button_id.startswith("cat-"):
            # Category selected
            category = button_id.replace("cat-", "")
            self.selected_category = category
            
            # Update description
            self.query_one("#description", Static).update(
                COMMAND_CATEGORIES[category]["description"]
            )
            
            # Re-render commands
            self._render_commands(category)
            
            # Update button styles
            for btn in self.query(".category-button"):
                btn.variant = "primary" if btn.id == button_id else "default"
        
        elif button_id == "exit-button":
            # Exit button pressed
            self.app.exit()
        
        elif button_id and button_id.startswith("cmd-"):
            # Command selected - would trigger parameter form or execution
            # ID format: cmd-{category}-{command}
            parts = button_id.replace("cmd-", "").split("-", 1)
            if len(parts) == 2:
                category, command = parts
                self._execute_command(category, command)

    def _execute_command(self, category: str, command: str, params: dict | None = None) -> None:
        """Execute a command using the ModelXClient."""
        try:
            result = None
            
            # Autonomous commands
            if category == "autonomous":
                if command == "run":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "goal", "label": "Goal description", "type": "textarea"},
                            {"name": "budget", "label": "Budget (tokens)", "type": "text", "default": "10000"},
                            {"name": "duration", "label": "Duration (seconds)", "type": "text", "default": "300"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Running autonomous execution..."))
                    result = self.client.run_autonomous(params)
                    self.app.pop_screen()
                elif command == "status":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "execution_id", "label": "Execution ID", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Fetching execution status..."))
                    result = self.client.get_execution_status(params["execution_id"])
                    self.app.pop_screen()
            
            # Goal commands
            elif category == "goal":
                if command == "list":
                    self.app.push_screen(LoadingScreen("Fetching goals..."))
                    result = self.client.list_goals()
                    self.app.pop_screen()
                elif command == "create":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "description", "label": "Goal description", "type": "textarea"},
                            {"name": "priority", "label": "Priority", "type": "select", "options": ["low", "medium", "high"], "default": "medium"},
                            {"name": "deadline", "label": "Deadline (ISO format)", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Creating goal..."))
                    result = self.client.create_goal(params)
                    self.app.pop_screen()
                elif command == "get":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "goal_id", "label": "Goal ID", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Fetching goal..."))
                    result = self.client.get_goal(params["goal_id"])
                    self.app.pop_screen()
                elif command == "delete":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "goal_id", "label": "Goal ID", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Deleting goal..."))
                    self.client.delete_goal(params["goal_id"])
                    self.app.pop_screen()
                    result = {"message": "Goal deleted successfully"}
            
            # Task commands
            elif category == "task":
                if command == "list":
                    self.app.push_screen(LoadingScreen("Fetching tasks..."))
                    result = self.client.list_tasks()
                    self.app.pop_screen()
                elif command == "create":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "goal_id", "label": "Goal ID", "type": "text"},
                            {"name": "description", "label": "Task description", "type": "textarea"},
                            {"name": "priority", "label": "Priority", "type": "select", "options": ["low", "medium", "high"], "default": "medium"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Creating task..."))
                    result = self.client.create_task(params)
                    self.app.pop_screen()
                elif command == "get":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "task_id", "label": "Task ID", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Fetching task..."))
                    result = self.client.get_task(params["task_id"])
                    self.app.pop_screen()
                elif command == "execute":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "task_id", "label": "Task ID", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Executing task..."))
                    result = self.client.execute_task(params["task_id"])
                    self.app.pop_screen()
            
            # Memory commands
            elif category == "memory":
                if command == "list":
                    self.app.push_screen(LoadingScreen("Fetching memories..."))
                    result = self.client.list_memories()
                    self.app.pop_screen()
                elif command == "add":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "content", "label": "Memory content", "type": "textarea"},
                            {"name": "type", "label": "Memory type", "type": "select", "options": ["episodic", "semantic", "procedural"], "default": "episodic"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Adding memory..."))
                    result = self.client.add_memory(params)
                    self.app.pop_screen()
                elif command == "search":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "query", "label": "Search query", "type": "text"},
                            {"name": "limit", "label": "Result limit", "type": "text", "default": "10"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Searching memory..."))
                    result = self.client.search_memory(params["query"], int(params.get("limit", 10)))
                    self.app.pop_screen()
            
            # Meta-learning commands
            elif category == "meta":
                if command == "analyze":
                    self.app.push_screen(LoadingScreen("Analyzing meta-learning..."))
                    result = self.client.analyze_meta_learning()
                    self.app.pop_screen()
                elif command == "strategies":
                    self.app.push_screen(LoadingScreen("Fetching strategies..."))
                    result = self.client.list_strategies()
                    self.app.pop_screen()
            
            # Reflection commands
            elif category == "reflect":
                if command == "list":
                    self.app.push_screen(LoadingScreen("Fetching reflections..."))
                    result = self.client.list_reflections()
                    self.app.pop_screen()
                elif command == "create":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "topic", "label": "Reflection topic", "type": "textarea"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Creating reflection..."))
                    result = self.client.create_reflection(params)
                    self.app.pop_screen()
            
            # Swarm commands
            elif category == "swarm":
                if command == "metrics":
                    self.app.push_screen(LoadingScreen("Fetching swarm metrics..."))
                    result = self.client.get_swarm_metrics()
                    self.app.pop_screen()
                elif command == "initialize":
                    self.app.push_screen(LoadingScreen("Initializing swarm..."))
                    result = self.client.initialize_swarm()
                    self.app.pop_screen()
                elif command == "shutdown":
                    self.app.push_screen(LoadingScreen("Shutting down swarm..."))
                    result = self.client.shutdown_swarm()
                    self.app.pop_screen()
                elif command == "submit":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "goal", "label": "Swarm goal", "type": "textarea"},
                            {"name": "agent_count", "label": "Agent count", "type": "text", "default": "5"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Submitting swarm goal..."))
                    result = self.client.submit_swarm_goal(params)
                    self.app.pop_screen()
                elif command == "status":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "goal_id", "label": "Goal ID", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Fetching swarm status..."))
                    result = self.client.get_swarm_goal_status(params["goal_id"])
                    self.app.pop_screen()
                elif command == "scale":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "target_count", "label": "Target agent count", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Scaling swarm..."))
                    result = self.client.scale_swarm(params)
                    self.app.pop_screen()
            
            # Knowledge commands
            elif category == "knowledge":
                if command == "compress":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "content", "label": "Content to compress", "type": "textarea"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Compressing knowledge..."))
                    result = self.client.add_knowledge(params)
                    self.app.pop_screen()
                elif command == "abstract":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "knowledge_id", "label": "Knowledge ID", "type": "text"},
                        ])
                        return
                    result = {"message": "Abstract operation - requires implementation"}
                elif command == "distill":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "source_ids", "label": "Source knowledge IDs (comma-separated)", "type": "text"},
                        ])
                        return
                    result = {"message": "Distill operation - requires implementation"}
            
            # Vision commands
            elif category == "vision":
                if command == "analyze":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "image_path", "label": "Image file path", "type": "text"},
                            {"name": "query", "label": "Analysis query", "type": "text"},
                        ])
                        return
                    result = {"message": "Vision analyze - requires file upload handling"}
                elif command == "capture":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "url", "label": "Web page URL", "type": "text"},
                        ])
                        return
                    self.app.push_screen(LoadingScreen("Capturing web page..."))
                    result = self.client.capture_web_page(params)
                    self.app.pop_screen()
                elif command == "detect":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "image_path", "label": "Image file path", "type": "text"},
                        ])
                        return
                    result = {"message": "Element detection - requires file upload handling"}
            
            # Cognitive commands
            elif category == "cognitive":
                if command == "status":
                    result = {"message": "Cognitive OS status - requires API endpoint"}
                elif command == "reason":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "query", "label": "Reasoning query", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Reasoning operation - requires API endpoint"}
                elif command == "attend":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "focus", "label": "Attention focus", "type": "text"},
                        ])
                        return
                    result = {"message": "Attend operation - requires API endpoint"}
            
            # Concept commands
            elif category == "concepts":
                if command == "create":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "name", "label": "Concept name", "type": "text"},
                            {"name": "definition", "label": "Definition", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Concept create - requires API endpoint"}
                elif command == "search":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "query", "label": "Search query", "type": "text"},
                        ])
                        return
                    result = {"message": "Concept search - requires API endpoint"}
                elif command == "relate":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "source_id", "label": "Source concept ID", "type": "text"},
                            {"name": "target_id", "label": "Target concept ID", "type": "text"},
                            {"name": "relation", "label": "Relation type", "type": "text"},
                        ])
                        return
                    result = {"message": "Concept relate - requires API endpoint"}
                elif command == "list":
                    result = {"message": "Concept list - requires API endpoint"}
                elif command == "lineage":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "concept_id", "label": "Concept ID", "type": "text"},
                        ])
                        return
                    result = {"message": "Concept lineage - requires API endpoint"}
            
            # Config commands
            elif category == "config":
                if command == "add_provider":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "provider_name", "label": "Provider name", "type": "text"},
                            {"name": "api_key", "label": "API key", "type": "text"},
                        ])
                        return
                    result = {"message": "Add provider - requires local config handling"}
                elif command == "remove_provider":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "provider_name", "label": "Provider name", "type": "text"},
                        ])
                        return
                    result = {"message": "Remove provider - requires local config handling"}
                elif command == "list_providers":
                    result = {"message": "List providers - requires local config handling"}
                elif command == "set":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "key", "label": "Config key", "type": "text"},
                            {"name": "value", "label": "Config value", "type": "text"},
                        ])
                        return
                    result = {"message": "Set config - requires local config handling"}
                elif command == "get":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "key", "label": "Config key", "type": "text"},
                        ])
                        return
                    result = {"message": "Get config - requires local config handling"}
            
            # Develop commands
            elif category == "develop":
                if command == "analyze":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "code_path", "label": "Code path", "type": "text"},
                        ])
                        return
                    result = {"message": "Code analysis - requires API endpoint"}
                elif command == "optimize":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "code_path", "label": "Code path", "type": "text"},
                        ])
                        return
                    result = {"message": "Code optimization - requires API endpoint"}
                elif command == "improve":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "code_path", "label": "Code path", "type": "text"},
                            {"name": "goal", "label": "Improvement goal", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Code improvement - requires API endpoint"}
            
            # Discover commands
            elif category == "discover":
                if command == "run":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "domain", "label": "Research domain", "type": "text"},
                            {"name": "hypothesis", "label": "Initial hypothesis", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Discovery loop - requires API endpoint"}
            
            # Identity commands
            elif category == "identity":
                if command == "status":
                    result = {"message": "Identity status - requires API endpoint"}
                elif command == "create_mission":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "mission", "label": "Mission statement", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Create mission - requires API endpoint"}
                elif command == "missions":
                    result = {"message": "List missions - requires API endpoint"}
            
            # Research commands
            elif category == "research":
                if command == "create_program":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "title", "label": "Program title", "type": "text"},
                            {"name": "description", "label": "Description", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Create research program - requires API endpoint"}
                elif command == "schedule":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "program_id", "label": "Program ID", "type": "text"},
                        ])
                        return
                    result = {"message": "Schedule research - requires API endpoint"}
                elif command == "list":
                    result = {"message": "List research programs - requires API endpoint"}
            
            # Society commands
            elif category == "society":
                if command == "create":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "society_name", "label": "Society name", "type": "text"},
                        ])
                        return
                    result = {"message": "Create society - requires API endpoint"}
                elif command == "list":
                    result = {"message": "List societies - requires API endpoint"}
                elif command == "add_agent":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "society_id", "label": "Society ID", "type": "text"},
                            {"name": "agent_config", "label": "Agent config (JSON)", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Add agent - requires API endpoint"}
            
            # Theories commands
            elif category == "theories":
                if command == "create":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "statement", "label": "Theory statement", "type": "textarea"},
                            {"name": "domain", "label": "Domain", "type": "text"},
                        ])
                        return
                    result = {"message": "Create theory - requires API endpoint"}
                elif command == "strengthen":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "theory_id", "label": "Theory ID", "type": "text"},
                            {"name": "evidence", "label": "Supporting evidence", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Strengthen theory - requires API endpoint"}
                elif command == "weaken":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "theory_id", "label": "Theory ID", "type": "text"},
                            {"name": "evidence", "label": "Contradicting evidence", "type": "textarea"},
                        ])
                        return
                    result = {"message": "Weaken theory - requires API endpoint"}
                elif command == "list":
                    result = {"message": "List theories - requires API endpoint"}
                elif command == "validate":
                    if params is None:
                        self._show_parameter_form(category, command, [
                            {"name": "theory_id", "label": "Theory ID", "type": "text"},
                        ])
                        return
                    result = {"message": "Validate theory - requires API endpoint"}
            
            # Lineage commands
            elif category == "lineage":
                result = {"message": "Lineage tracking - requires API endpoint"}
            
            else:
                result = {"message": f"Command {category} {command} not yet implemented in TUI"}
            
            # Display result
            if result:
                self._show_output(result)
        
        except Exception as e:
            self._show_output(f"Error: {str(e)}", is_error=True)

    def _show_parameter_form(self, category: str, command: str, fields: list) -> None:
        """Show parameter input form for a command."""
        self.app.push_screen(
            ParameterInputScreen(category, command, fields, self._execute_command)
        )

    def _show_output(self, result: Any, is_error: bool = False) -> None:
        """Show command output in a new screen."""
        import json
        
        if isinstance(result, dict) or isinstance(result, list):
            output = json.dumps(result, indent=2)
        else:
            output = str(result)
        
        self.app.push_screen(OutputScreen(output, is_error))


class LoadingScreen(Screen):
    """Screen for showing loading state during async operations."""

    CSS = """
    LoadingScreen {
        layout: vertical;
        align: center middle;
    }
    
    #loading-container {
        align: center middle;
        padding: 2;
    }
    
    #loading-text {
        text-align: center;
        margin-top: 1;
    }
    """

    def __init__(self, message: str = "Processing...") -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        with Vertical(id="loading-container"):
            yield LoadingIndicator()
            yield Static(self.message, id="loading-text")


class OutputScreen(Screen):
    """Screen for displaying command output."""

    CSS = """
    OutputScreen {
        layout: vertical;
    }
    
    #output-content {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }
    
    #back-button {
        dock: bottom;
        margin: 1;
    }
    
    .error {
        text-style: bold;
        color: red;
    }
    
    .success {
        text-style: bold;
        color: green;
    }
    """

    def __init__(self, output: str, is_error: bool = False) -> None:
        super().__init__()
        self.output = output
        self.is_error = is_error

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        output_class = "error" if self.is_error else "success"
        yield Static(self.output, id="output-content", classes=output_class)
        yield Button("Back", id="back-button", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle back button."""
        if event.button.id == "back-button":
            self.app.pop_screen()


class ParameterInputScreen(Screen):
    """Screen for collecting command parameters."""

    CSS = """
    ParameterInputScreen {
        layout: vertical;
    }
    
    #form-container {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }
    
    .field-label {
        text-style: bold;
        margin: 1 0 0 0;
    }
    
    .field-input {
        margin: 0 0 1 0;
    }
    
    #button-container {
        dock: bottom;
        layout: horizontal;
        padding: 1;
    }
    
    #submit-button {
        margin-right: 1;
    }
    """

    def __init__(self, category: str, command: str, fields: list, callback) -> None:
        super().__init__()
        self.category = category
        self.command = command
        self.fields = fields
        self.callback = callback
        self.inputs = {}

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        with ScrollableContainer(id="form-container"):
            yield Static(f"Parameters for {self.category} {self.command}", classes="header")
            for field in self.fields:
                field_name = field["name"]
                field_type = field.get("type", "text")
                field_label = field.get("label", field_name)
                field_default = field.get("default", "")
                
                yield Label(field_label, classes="field-label")
                
                if field_type == "textarea":
                    yield TextArea(field_default, id=f"input-{field_name}", classes="field-input")
                elif field_type == "select":
                    options = field.get("options", [])
                    yield Select(
                        [(str(opt), str(opt)) for opt in options],
                        id=f"input-{field_name}",
                        classes="field-input",
                        value=str(field_default) if field_default else None
                    )
                else:
                    yield Input(
                        placeholder=field_label,
                        id=f"input-{field_name}",
                        classes="field-input",
                        value=field_default
                    )
        
        with Horizontal(id="button-container"):
            yield Button("Submit", id="submit-button", variant="primary")
            yield Button("Cancel", id="cancel-button", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-button":
            self.app.pop_screen()
        elif event.button.id == "submit-button":
            self._collect_and_submit()

    def _collect_and_submit(self) -> None:
        """Collect input values and submit."""
        try:
            params = {}
            for field in self.fields:
                field_name = field["name"]
                field_type = field.get("type", "text")
                
                if field_type == "textarea":
                    widget = self.query_one(f"#input-{field_name}", TextArea)
                    params[field_name] = widget.text
                elif field_type == "select":
                    widget = self.query_one(f"#input-{field_name}", Select)
                    params[field_name] = widget.value
                else:
                    widget = self.query_one(f"#input-{field_name}", Input)
                    params[field_name] = widget.value
            
            self.app.pop_screen()
            self.callback(self.category, self.command, params)
        except Exception as e:
            self.app.notify(f"Error collecting parameters: {str(e)}", severity="error")
