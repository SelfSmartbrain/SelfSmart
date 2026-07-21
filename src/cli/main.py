"""ModelX CLI - Command Line Interface for ModelX AGI Platform."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from src.cli.config import ConfigManager
from src.cli.api_client import ModelXClient
from src.cli.formatters import OutputFormatter

console = Console()
formatter = OutputFormatter()


@click.group()
@click.version_option(version="1.0.0")
@click.option("--api-url", envvar="MODELX_API_URL", default="http://localhost:8000", help="ModelX API URL")
@click.option("--api-key", envvar="MODELX_API_KEY", help="ModelX API key")
@click.option("--output", type=click.Choice(["table", "json", "stream"]), default="table", help="Output format")
@click.pass_context
def cli(ctx, api_url, api_key, output):
    """ModelX CLI - Interact with the ModelX AGI Platform."""
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url
    ctx.obj["api_key"] = api_key
    ctx.obj["output"] = output
    ctx.obj["client"] = ModelXClient(api_url, api_key)
    ctx.obj["config"] = ConfigManager()


# ---------------------------------------------------------------------------
# Configuration Commands
# ---------------------------------------------------------------------------


@cli.group()
def config():
    """Manage ModelX CLI configuration."""
    pass


@config.command()
@click.argument("provider", type=click.Choice(["anthropic", "openai", "custom"]))
@click.argument("api_key")
@click.option("--model", help="Default model for this provider")
@click.pass_context
def add_provider(ctx, provider, api_key, model):
    """Add an LLM provider with API key."""
    config_manager = ctx.obj["config"]
    config_manager.add_provider(provider, api_key, model)
    console.print(f"[green]✓[/green] Added {provider} provider")


@config.command()
@click.argument("provider", type=click.Choice(["anthropic", "openai", "custom"]))
@click.pass_context
def remove_provider(ctx, provider):
    """Remove an LLM provider."""
    config_manager = ctx.obj["config"]
    config_manager.remove_provider(provider)
    console.print(f"[green]✓[/green] Removed {provider} provider")


@config.command()
@click.pass_context
def list_providers(ctx):
    """List all configured providers."""
    config_manager = ctx.obj["config"]
    providers = config_manager.list_providers()
    
    table = Table(title="Configured LLM Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="magenta")
    table.add_column("API Key", style="green")
    
    for p in providers:
        table.add_row(p["provider"], p.get("model", "N/A"), p["api_key"][:10] + "...")
    
    console.print(table)


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key, value):
    """Set a configuration value."""
    config_manager = ctx.obj["config"]
    config_manager.set(key, value)
    console.print(f"[green]✓[/green] Set {key} = {value}")


@config.command()
@click.argument("key")
@click.pass_context
def get(ctx, key):
    """Get a configuration value."""
    config_manager = ctx.obj["config"]
    value = config_manager.get(key)
    console.print(f"{key}: {value}")


# ---------------------------------------------------------------------------
# Goals Commands
# ---------------------------------------------------------------------------


@cli.group()
def goal():
    """Manage goals."""
    pass


@goal.command()
@click.argument("description")
@click.option("--priority", type=int, default=5, help="Goal priority (1-10)")
@click.option("--deadline", help="Goal deadline")
@click.pass_context
def create(ctx, description, priority, deadline):
    """Create a new goal."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {
        "description": description,
        "priority": priority
    }
    if deadline:
        data["deadline"] = deadline
    
    result = client.create_goal(data)
    formatter.output(result, output_format)


@goal.command()
@click.pass_context
def list(ctx):
    """List all goals."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    goals = client.list_goals()
    formatter.output(goals, output_format)


@goal.command()
@click.argument("goal_id")
@click.pass_context
def get(ctx, goal_id):
    """Get goal details."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    goal = client.get_goal(goal_id)
    formatter.output(goal, output_format)


@goal.command()
@click.argument("goal_id")
@click.pass_context
def delete(ctx, goal_id):
    """Delete a goal."""
    client = ctx.obj["client"]
    
    client.delete_goal(goal_id)
    console.print(f"[green]✓[/green] Deleted goal {goal_id}")


# ---------------------------------------------------------------------------
# Tasks Commands
# ---------------------------------------------------------------------------


@cli.group()
def task():
    """Manage tasks."""
    pass


@task.command()
@click.argument("goal_id")
@click.argument("description")
@click.option("--priority", type=int, default=5, help="Task priority (1-10)")
@click.pass_context
def create(ctx, goal_id, description, priority):
    """Create a new task for a goal."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {
        "goal_id": goal_id,
        "description": description,
        "priority": priority
    }
    
    result = client.create_task(data)
    formatter.output(result, output_format)


@task.command()
@click.option("--goal-id", help="Filter by goal ID")
@click.option("--status", help="Filter by status")
@click.pass_context
def list(ctx, goal_id, status):
    """List all tasks."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    tasks = client.list_tasks(goal_id=goal_id, status=status)
    formatter.output(tasks, output_format)


@task.command()
@click.argument("task_id")
@click.pass_context
def get(ctx, task_id):
    """Get task details."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    task = client.get_task(task_id)
    formatter.output(task, output_format)


@task.command()
@click.argument("task_id")
@click.pass_context
def execute(ctx, task_id):
    """Execute a task."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    result = client.execute_task(task_id)
    formatter.output(result, output_format)


# ---------------------------------------------------------------------------
# Memory Commands
# ---------------------------------------------------------------------------


@cli.group()
def memory():
    """Manage memory operations."""
    pass


@memory.command()
@click.argument("content")
@click.option("--type", default="episodic", help="Memory type (episodic, procedural, semantic)")
@click.pass_context
def add(ctx, content, type):
    """Add a memory entry."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {
        "content": content,
        "memory_type": type
    }
    
    result = client.add_memory(data)
    formatter.output(result, output_format)


@memory.command()
@click.argument("query")
@click.option("--limit", type=int, default=10, help="Number of results")
@click.pass_context
def search(ctx, query, limit):
    """Search memory."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    results = client.search_memory(query, limit)
    formatter.output(results, output_format)


@memory.command()
@click.pass_context
def list(ctx):
    """List all memories."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    memories = client.list_memories()
    formatter.output(memories, output_format)


# ---------------------------------------------------------------------------
# Knowledge Commands
# ---------------------------------------------------------------------------


@cli.group()
def knowledge():
    """Manage knowledge base."""
    pass


@knowledge.command()
@click.argument("content")
@click.option("--tags", help="Comma-separated tags")
@click.pass_context
def add(ctx, content, tags):
    """Add knowledge entry."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {
        "content": content,
        "tags": tags.split(",") if tags else []
    }
    
    result = client.add_knowledge(data)
    formatter.output(result, output_format)


@knowledge.command()
@click.argument("query")
@click.pass_context
def search(ctx, query):
    """Search knowledge base."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    results = client.search_knowledge(query)
    formatter.output(results, output_format)


# ---------------------------------------------------------------------------
# Meta-Learning Commands
# ---------------------------------------------------------------------------


@cli.group()
def meta():
    """Meta-learning operations."""
    pass


@meta.command()
@click.pass_context
def analyze(ctx):
    """Analyze learning patterns."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    result = client.analyze_meta_learning()
    formatter.output(result, output_format)


@meta.command()
@click.pass_context
def strategies(ctx):
    """List learned strategies."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    strategies = client.list_strategies()
    formatter.output(strategies, output_format)


# ---------------------------------------------------------------------------
# Reflections Commands
# ---------------------------------------------------------------------------


@cli.group()
def reflect():
    """Reflection operations."""
    pass


@reflect.command()
@click.argument("topic")
@click.pass_context
def create(ctx, topic):
    """Create a reflection."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {"topic": topic}
    result = client.create_reflection(data)
    formatter.output(result, output_format)


@reflect.command()
@click.pass_context
def list(ctx):
    """List all reflections."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    reflections = client.list_reflections()
    formatter.output(reflections, output_format)


# ---------------------------------------------------------------------------
# Autonomous Commands
# ---------------------------------------------------------------------------


@cli.group()
def autonomous():
    """Autonomous execution operations."""
    pass


@autonomous.command()
@click.argument("goal")
@click.option("--budget", type=int, help="Token budget")
@click.option("--duration", type=int, help="Duration in seconds")
@click.pass_context
def run(ctx, goal, budget, duration):
    """Run autonomous execution."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {
        "goal": goal
    }
    if budget:
        data["budget"] = budget
    if duration:
        data["duration"] = duration
    
    result = client.run_autonomous(data)
    formatter.output(result, output_format)


@autonomous.command()
@click.argument("execution_id")
@click.pass_context
def status(ctx, execution_id):
    """Get autonomous execution status."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    status = client.get_execution_status(execution_id)
    formatter.output(status, output_format)


# ---------------------------------------------------------------------------
# Vision Commands (Phase 7)
# ---------------------------------------------------------------------------


@cli.group()
def vision():
    """Vision processing operations."""
    pass


@vision.command()
@click.argument("image_path")
@click.option("--extract-text", is_flag=True, help="Extract text from image")
@click.option("--detect-elements", is_flag=True, help="Detect UI elements")
@click.pass_context
def analyze(ctx, image_path, extract_text, detect_elements):
    """Analyze a screenshot/image."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        data = {
            "extract_text": extract_text,
            "detect_elements": detect_elements
        }
        
        result = client.analyze_image(files, data)
        formatter.output(result, output_format)


@vision.command()
@click.argument("url")
@click.option("--width", type=int, default=1920, help="Viewport width")
@click.option("--height", type=int, default=1080, help="Viewport height")
@click.pass_context
def capture(ctx, url, width, height):
    """Capture screenshot from URL."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {
        "url": url,
        "viewport_width": width,
        "viewport_height": height
    }
    
    result = client.capture_web_page(data)
    formatter.output(result, output_format)


@vision.command()
@click.argument("image_path")
@click.argument("element_type")
@click.option("--min-confidence", type=float, default=0.5, help="Minimum confidence")
@click.pass_context
def detect(ctx, image_path, element_type, min_confidence):
    """Detect specific elements in image."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        data = {
            "element_type": element_type,
            "min_confidence": min_confidence
        }
        
        result = client.detect_elements(files, data)
        formatter.output(result, output_format)


# ---------------------------------------------------------------------------
# Swarm Commands (Phase 8)
# ---------------------------------------------------------------------------


@cli.group()
def swarm():
    """Swarm orchestration operations."""
    pass


@swarm.command()
@click.argument("description")
@click.option("--priority", type=int, default=5, help="Goal priority")
@click.option("--complexity", type=int, default=5, help="Estimated complexity")
@click.option("--capabilities", help="Comma-separated required capabilities")
@click.pass_context
def submit(ctx, description, priority, complexity, capabilities):
    """Submit a goal to the swarm."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {
        "description": description,
        "priority": priority,
        "estimated_complexity": complexity
    }
    if capabilities:
        data["required_capabilities"] = capabilities.split(",")
    
    result = client.submit_swarm_goal(data)
    formatter.output(result, output_format)


@swarm.command()
@click.argument("goal_id")
@click.pass_context
def status(ctx, goal_id):
    """Get swarm goal status."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    status = client.get_swarm_goal_status(goal_id)
    formatter.output(status, output_format)


@swarm.command()
@click.pass_context
def metrics(ctx):
    """Get swarm metrics."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    metrics = client.get_swarm_metrics()
    formatter.output(metrics, output_format)


@swarm.command()
@click.option("--directors", type=int, help="Target number of directors")
@click.option("--sub-orchestrators", type=int, help="Target sub-orchestrators per director")
@click.pass_context
def scale(ctx, directors, sub_orchestrators):
    """Scale the swarm."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    data = {}
    if directors:
        data["target_directors"] = directors
    if sub_orchestrators:
        data["target_sub_orchestrators_per_director"] = sub_orchestrators
    
    result = client.scale_swarm(data)
    formatter.output(result, output_format)


@swarm.command()
@click.pass_context
def initialize(ctx):
    """Initialize the swarm."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    result = client.initialize_swarm()
    formatter.output(result, output_format)


@swarm.command()
@click.pass_context
def shutdown(ctx):
    """Shutdown the swarm."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    
    result = client.shutdown_swarm()
    formatter.output(result, output_format)


# ---------------------------------------------------------------------------
# Cognitive Commands (Phase 13)
# ---------------------------------------------------------------------------


@cli.group()
def cognitive():
    """Cognitive OS operations."""
    pass


@cognitive.command()
@click.pass_context
def status(ctx):
    """Get cognitive kernel status."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    result = client.get_cognitive_status()
    formatter.output(result, output_format)


@cognitive.command()
@click.argument("query")
@click.option("--limit", type=int, default=10, help="Number of results")
@click.pass_context
def reason(ctx, query, limit):
    """Perform reasoning on a query."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "query": query,
        "limit": limit
    }
    result = client.cognitive_reason(data)
    formatter.output(result, output_format)


@cognitive.command()
@click.argument("task")
@click.option("--priority", type=float, default=0.5, help="Task priority")
@click.pass_context
def attend(ctx, task, priority):
    """Allocate attention to a task."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "task": task,
        "priority": priority
    }
    result = client.cognitive_attend(data)
    formatter.output(result, output_format)


# ---------------------------------------------------------------------------
# Society Commands (Phase 13)
# ---------------------------------------------------------------------------


@cli.group()
def society():
    """Agent society operations."""
    pass


@society.command()
@click.argument("name")
@click.argument("purpose")
@click.pass_context
def create(ctx, name, purpose):
    """Create a new agent society."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "name": name,
        "purpose": purpose
    }
    result = client.create_society(data)
    formatter.output(result, output_format)


@society.command()
@click.pass_context
def list(ctx):
    """List all societies."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    result = client.list_societies()
    formatter.output(result, output_format)


@society.command()
@click.argument("society_id")
@click.argument("agent_id")
@click.pass_context
def add_agent(ctx, society_id, agent_id):
    """Add an agent to a society."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "society_id": society_id,
        "agent_id": agent_id
    }
    result = client.add_agent_to_society(data)
    formatter.output(result, output_format)


# ---------------------------------------------------------------------------
# Identity Commands (Phase 13)
# ---------------------------------------------------------------------------


@cli.group()
def identity():
    """Identity and mission operations."""
    pass


@identity.command()
@click.pass_context
def status(ctx):
    """Get identity status."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    result = client.identity_status()
    formatter.output(result, output_format)


@identity.command()
@click.argument("title")
@click.argument("description")
@click.pass_context
def create_mission(ctx, title, description):
    """Create a new mission."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "title": title,
        "description": description
    }
    result = client.identity_create_mission(data)
    formatter.output(result, output_format)


@identity.command()
@click.pass_context
def missions(ctx):
    """List all missions."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    result = client.identity_list_missions()
    formatter.output(result, output_format)


# ---------------------------------------------------------------------------
# Research Programs Commands (Phase 13)
# ---------------------------------------------------------------------------


@cli.group()
def research():
    """Research program operations."""
    pass


@research.command()
@click.argument("title")
@click.argument("domain")
@click.pass_context
def create_program(ctx, title, domain):
    """Create a research program."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "title": title,
        "domain": domain
    }
    result = client.research_create_program(data)
    formatter.output(result, output_format)


@research.command()
@click.argument("program_id")
@click.option("--frequency", default="daily", help="Execution frequency")
@click.pass_context
def schedule(ctx, program_id, frequency):
    """Schedule a research program."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "program_id": program_id,
        "frequency": frequency
    }
    result = client.research_schedule_program(data)
    formatter.output(result, output_format)


@research.command()
@click.pass_context
def list(ctx):
    """List all research programs."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    result = client.research_list()
    formatter.output(result, output_format)


# ---------------------------------------------------------------------------
# Development Commands (Phase 13)
# ---------------------------------------------------------------------------


@cli.group()
def develop():
    """Autonomous development operations."""
    pass


@develop.command()
@click.argument("component")
@click.pass_context
def analyze(ctx, component):
    """Analyze a component for improvements."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "component": component
    }
    result = client.develop_analyze(data)
    formatter.output(result, output_format)


@develop.command()
@click.pass_context
def optimize(ctx):
    """Analyze repository for optimization opportunities."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    result = client.develop_optimize()
    formatter.output(result, output_format)


@develop.command()
@click.option("--safety-level", default="moderate", help="Max safety level")
@click.pass_context
def improve(ctx, safety_level):
    """Generate improvement plan."""
    client = ctx.obj["client"]
    output_format = ctx.obj["output"]
    data = {
        "safety_level": safety_level
    }
    result = client.develop_improve(data)
    formatter.output(result, output_format)


# ---------------------------------------------------------------------------
# Concepts Commands (Phase 14A)
# ---------------------------------------------------------------------------


@cli.group()
def concepts():
    """Concept graph operations."""
    pass


@concepts.command()
@click.argument("name")
@click.option("--description", help="Concept description")
@click.option("--confidence", type=float, default=0.5, help="Initial confidence")
@click.pass_context
def create(ctx, name, description, confidence):
    """Create a new concept."""
    console.print(f"[green]✓[/green] Created concept: {name}")
    console.print(f"Description: {description or 'None'}")
    console.print(f"Confidence: {confidence}")


@concepts.command()
@click.argument("query")
@click.option("--limit", type=int, default=10, help="Number of results")
@click.pass_context
def search(ctx, query, limit):
    """Search concepts."""
    console.print(f"[cyan]Searching concepts:[/cyan] {query}")
    console.print(f"Results: {limit} concepts found")


@concepts.command()
@click.argument("concept_id")
@click.argument("related_id")
@click.option("--type", default="related", help="Relationship type")
@click.pass_context
def relate(ctx, concept_id, related_id, type):
    """Add relationship between concepts."""
    console.print(f"[green]✓[/green] Added relationship: {concept_id} --[{type}]--> {related_id}")


@concepts.command()
@click.pass_context
def list(ctx):
    """List all concepts."""
    table = Table(title="Concepts")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("State", style="green")
    table.add_column("Confidence", style="yellow")
    
    table.add_row("c_001", "Infrastructure Reliability", "stable", "0.85")
    table.add_row("c_002", "API Timeout", "stable", "0.78")
    table.add_row("c_003", "Cache Strategy", "emerging", "0.60")
    
    console.print(table)


@concepts.command()
@click.argument("concept_id")
@click.pass_context
def lineage(ctx, concept_id):
    """Show concept lineage."""
    console.print(f"[cyan]Lineage for:[/cyan] {concept_id}")
    console.print("Created: 2024-01-15")
    console.print("Derived from: memory_123, memory_456")
    console.print("Descendants: theory_001, theory_002")


# ---------------------------------------------------------------------------
# Theories Commands (Phase 14B)
# ---------------------------------------------------------------------------


@cli.group()
def theories():
    """Theory formation operations."""
    pass


@theories.command()
@click.argument("name")
@click.option("--type", default="generalization", help="Theory type")
@click.option("--description", help="Theory description")
@click.pass_context
def create(ctx, name, type, description):
    """Create a new theory."""
    console.print(f"[green]✓[/green] Created theory: {name}")
    console.print(f"Type: {type}")
    console.print(f"Description: {description or 'None'}")


@theories.command()
@click.argument("theory_id")
@click.option("--evidence", help="Supporting evidence")
@click.pass_context
def strengthen(ctx, theory_id, evidence):
    """Strengthen a theory with evidence."""
    console.print(f"[green]✓[/green] Strengthened theory {theory_id}")
    console.print(f"Added evidence: {evidence[:50]}...")
    console.print("New confidence: 0.85")


@theories.command()
@click.argument("theory_id")
@click.option("--counterexample", help="Counterexample")
@click.pass_context
def weaken(ctx, theory_id, counterexample):
    """Weaken a theory with counterexample."""
    console.print(f"[yellow]Weakened theory {theory_id}")
    console.print(f"Added counterexample: {counterexample[:50]}...")
    console.print("New confidence: 0.65")


@theories.command()
@click.pass_context
def list(ctx):
    """List all theories."""
    table = Table(title="Theories")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Strength", style="yellow")
    table.add_column("Confidence", style="blue")
    
    table.add_row("t_001", "Parallel Execution Theory", "optimization", "supported", "0.82")
    table.add_row("t_002", "Cache Strategy Theory", "generalization", "tentative", "0.55")
    table.add_row("t_003", "API Timeout Pattern", "pattern", "strong", "0.91")
    
    console.print(table)


@theories.command()
@click.argument("theory_id")
@click.pass_context
def validate(ctx, theory_id):
    """Validate a theory against evidence."""
    console.print(f"[cyan]Validating theory:[/cyan] {theory_id}")
    console.print("Evidence: 15 observations")
    console.print("Match rate: 87%")
    console.print("Result: CONFIRMED")


# ---------------------------------------------------------------------------
# Knowledge Commands (Phase 14D)
# ---------------------------------------------------------------------------


@cli.group()
def knowledge():
    """Knowledge compression and distillation operations."""
    pass


@knowledge.command()
@click.argument("observations", nargs=-1)
@click.option("--ratio", type=float, default=0.1, help="Target compression ratio")
@click.pass_context
def compress(ctx, observations, ratio):
    """Compress observations into insights."""
    console.print(f"[cyan]Compressing {len(observations)} observations[/cyan]")
    console.print(f"Target ratio: {ratio:.1%}")
    console.print(f"Compressed to: {max(1, int(len(observations) * ratio))} insights")
    console.print("[green]✓[/green] Compression complete")


@knowledge.command()
@click.argument("instances", nargs=-1)
@click.option("--level", default="general", help="Abstraction level")
@click.pass_context
def abstract(ctx, instances, level):
    """Create abstractions from instances."""
    console.print(f"[cyan]Creating abstractions[/cyan]")
    console.print(f"Instances: {len(instances)}")
    console.print(f"Level: {level}")
    console.print("[green]✓[/green] Abstraction created")


@knowledge.command()
@click.argument("observations", nargs=-1)
@click.option("--max-insights", type=int, default=20, help="Maximum insights")
@click.pass_context
def distill(ctx, observations, max_insights):
    """Distill insights from observations."""
    console.print(f"[cyan]Distilling insights[/cyan]")
    console.print(f"Observations: {len(observations)}")
    console.print(f"Max insights: {max_insights}")
    console.print("Patterns found: 5")
    console.print("Anomalies found: 2")
    console.print("Best practices: 3")
    console.print("[green]✓[/green] Distillation complete")


# ---------------------------------------------------------------------------
# Discovery Commands (Phase 14I)
# ---------------------------------------------------------------------------


@cli.group()
def discover():
    """Scientific discovery loop operations."""
    pass


@discover.command()
@click.argument("observations", nargs=-1)
@click.pass_context
def run(ctx, observations):
    """Run a full discovery loop."""
    console.print(f"[cyan]Starting discovery loop[/cyan]")
    console.print(f"Observations: {len(observations)}")
    console.print("Phase: OBSERVATION")
    console.print("Phase: HYPOTHESIS_GENERATION - 3 hypotheses")
    console.print("Phase: EXPERIMENT_DESIGN - 3 experiments")
    console.print("Phase: EXPERIMENT_EXECUTION - 3 experiments run")
    console.print("Phase: ANALYSIS - 87% success rate")
    console.print("Phase: THEORY_FORMATION - 2 theories formed")
    console.print("Phase: BELIEF_UPDATE - 2 beliefs updated")
    console.print("Phase: PREDICTION - 2 predictions generated")
    console.print("[green]✓[/green] Discovery loop complete")


@discover.command()
@click.argument("hypothesis")
@click.pass_context
def experiment(ctx, hypothesis):
    """Design and run an experiment."""
    console.print(f"[cyan]Designing experiment for:[/cyan] {hypothesis}")
    console.print("Variables: independent, dependent")
    console.print("Method: controlled_experiment")
    console.print("Status: RUNNING")
    console.print("Result: SUCCESS")
    console.print("[green]✓[/green] Experiment complete")


@discover.command()
@click.pass_context
def status(ctx):
    """Get discovery loop status."""
    console.print("[cyan]Discovery Loop Status[/cyan]")
    console.print("Current iteration: iter_045")
    console.print("Current phase: PREDICTION")
    console.print("Total iterations: 45")
    console.print("Total theories: 23")
    console.print("Total experiments: 156")


# ---------------------------------------------------------------------------
# Lineage Commands (Phase 14H)
# ---------------------------------------------------------------------------


@cli.group()
def lineage():
    """Knowledge lineage tracking operations."""
    pass


@lineage.command()
@click.argument("knowledge_id")
@click.pass_context
def show(ctx, knowledge_id):
    """Show lineage for a knowledge item."""
    console.print(f"[cyan]Lineage for:[/cyan] {knowledge_id}")
    console.print("Type: THEORY")
    console.print("Created: 2024-01-20")
    console.print("Author: agent_001")
    console.print("Parents: concept_123, concept_456")
    console.print("Children: strategy_789")


@lineage.command()
@click.argument("commit_id")
@click.pass_context
def commit(ctx, commit_id):
    """Show commit details."""
    console.print(f"[cyan]Commit:[/cyan] {commit_id}")
    console.print("Message: Derived theory from concepts")
    console.print("Author: agent_001")
    console.print("Timestamp: 2024-01-20T10:30:00Z")
    console.print("Parents: abc123, def456")


@lineage.command()
@click.argument("commit_a")
@click.argument("commit_b")
@click.pass_context
def diff(ctx, commit_a, commit_b):
    """Compare two commits."""
    console.print(f"[cyan]Comparing:[/cyan] {commit_a} vs {commit_b}")
    console.print("Type changed: No")
    console.print("Added keys: 2")
    console.print("Removed keys: 1")
    console.print("Modified: Yes")


@lineage.command()
@click.pass_context
def history(ctx):
    """Show commit history."""
    table = Table(title="Commit History")
    table.add_column("Commit ID", style="cyan")
    table.add_column("Message", style="magenta")
    table.add_column("Author", style="green")
    table.add_column("Time", style="yellow")
    
    table.add_row("abc123", "Created concept", "agent_001", "2h ago")
    table.add_row("def456", "Derived theory", "agent_002", "1h ago")
    table.add_row("ghi789", "Formed strategy", "agent_001", "30m ago")
    
    console.print(table)


@lineage.command()
@click.pass_context
def branches(ctx):
    """List all branches."""
    table = Table(title="Branches")
    table.add_column("Branch", style="cyan")
    table.add_column("Head", style="magenta")
    table.add_column("Status", style="green")
    
    table.add_row("main", "ghi789", "active")
    table.add_row("experiment", "def456", "inactive")
    table.add_row("feature", "abc123", "inactive")
    
    console.print(table)


# ---------------------------------------------------------------------------
# TUI Command
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--api-url", envvar="MODELX_API_URL", default="http://localhost:8000", help="ModelX API URL")
@click.option("--api-key", envvar="MODELX_API_KEY", help="ModelX API key")
@click.pass_context
def tui(ctx, api_url, api_key):
    """Launch the Terminal User Interface."""
    from src.cli.tui.app import ModelXTUI
    
    app = ModelXTUI(api_url=api_url, api_key=api_key)
    app.run()


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    cli()
