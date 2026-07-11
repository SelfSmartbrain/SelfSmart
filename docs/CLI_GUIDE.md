# ModelX CLI Guide

The ModelX CLI provides a comprehensive command-line interface for interacting with the ModelX AGI Platform.

## Installation

```bash
pip install -e .
```

This installs the `modelx` command globally.

## Configuration

### Setting up LLM Providers

Add LLM providers with your API keys:

```bash
# Add Anthropic provider
modelx config add-provider anthropic sk-ant-api03-...

# Add OpenAI provider
modelx config add-provider openai sk-proj-...

# Add custom provider
modelx config add-provider custom your-api-key --model custom-model-name
```

List configured providers:

```bash
modelx config list-providers
```

Remove a provider:

```bash
modelx config remove-provider anthropic
```

### Setting API URL and Key

Set the ModelX API URL:

```bash
modelx config set api_url http://localhost:8000
```

Set the ModelX API key:

```bash
modelx config set api_key your-modelx-api-key
```

Or use environment variables:

```bash
export MODELX_API_URL=http://localhost:8000
export MODELX_API_KEY=your-api-key
```

## Output Formats

The CLI supports three output formats:

- `table` (default): Rich table format
- `json`: JSON output
- `stream`: Streaming output for long-running operations

Use the `--output` flag:

```bash
modelx goal list --output json
modelx task list --output stream
```

## Goals Management

### Create a Goal

```bash
modelx goal create "Build a web application" --priority 7 --deadline "2024-12-31"
```

### List All Goals

```bash
modelx goal list
```

### Get Goal Details

```bash
modelx goal get <goal_id>
```

### Delete a Goal

```bash
modelx goal delete <goal_id>
```

## Tasks Management

### Create a Task

```bash
modelx task create <goal_id> "Implement user authentication" --priority 8
```

### List All Tasks

```bash
modelx task list
```

Filter by goal:

```bash
modelx task list --goal-id <goal_id>
```

Filter by status:

```bash
modelx task list --status "in_progress"
```

### Get Task Details

```bash
modelx task get <task_id>
```

### Execute a Task

```bash
modelx task execute <task_id>
```

## Memory Operations

### Add a Memory Entry

```bash
modelx memory add "User prefers dark mode" --type episodic
```

Memory types:
- `episodic`: Specific events and experiences
- `procedural`: How-to knowledge
- `semantic`: General knowledge

### Search Memory

```bash
modelx memory search "user preferences" --limit 10
```

### List All Memories

```bash
modelx memory list
```

## Knowledge Base

### Add Knowledge Entry

```bash
modelx knowledge add "Python async/await pattern for concurrent operations" --tags python,async,concurrency
```

### Search Knowledge Base

```bash
modelx knowledge search "async patterns"
```

## Meta-Learning

### Analyze Learning Patterns

```bash
modelx meta analyze
```

### List Learned Strategies

```bash
modelx meta strategies
```

## Reflections

### Create a Reflection

```bash
modelx reflect create "Review recent project performance"
```

### List All Reflections

```bash
modelx reflect list
```

## Autonomous Execution

### Run Autonomous Execution

```bash
modelx autonomous run "Build a complete e-commerce platform" --budget 100000 --duration 3600
```

### Get Execution Status

```bash
modelx autonomous status <execution_id>
```

## Vision Processing (Phase 7)

### Analyze an Image

```bash
modelx vision analyze screenshot.png --extract-text --detect-elements
```

### Capture Screenshot from URL

```bash
modelx vision capture https://example.com --width 1920 --height 1080
```

### Detect Specific Elements

```bash
modelx vision detect screenshot.png button --min-confidence 0.7
```

Element types: `button`, `input`, `link`, `text`

## Swarm Orchestration (Phase 8)

### Submit Goal to Swarm

```bash
modelx swarm submit "Build a large-scale distributed system" --priority 8 --complexity 9 --capabilities research,coding,testing
```

### Get Swarm Goal Status

```bash
modelx swarm status <goal_id>
```

### Get Swarm Metrics

```bash
modelx swarm metrics
```

### Scale the Swarm

```bash
modelx swarm scale --directors 10 --sub-orchestrators 20
```

### Initialize Swarm

```bash
modelx swarm initialize
```

### Shutdown Swarm

```bash
modelx swarm shutdown
```

## Global Options

- `--api-url`: ModelX API URL (default: http://localhost:8000)
- `--api-key`: ModelX API key
- `--output`: Output format (table, json, stream)
- `--help`: Show help message
- `--version`: Show version

## Examples

### Complete Workflow Example

```bash
# 1. Configure providers
modelx config add-provider anthropic sk-ant-api03-...

# 2. Create a goal
modelx goal create "Build a web application" --priority 7

# 3. Create tasks for the goal
modelx task create <goal_id> "Design database schema" --priority 8
modelx task create <goal_id> "Implement API endpoints" --priority 8
modelx task create <goal_id> "Create frontend UI" --priority 7

# 4. Execute tasks
modelx task execute <task_id_1>
modelx task execute <task_id_2>

# 5. Check progress
modelx task list --goal-id <goal_id>

# 6. Add learnings to memory
modelx memory add "PostgreSQL performs better for this use case" --type procedural
```

### Vision Processing Example

```bash
# Capture and analyze a web page
modelx vision capture https://github.com --width 1920 --height 1080

# Analyze a local screenshot
modelx vision analyze screenshot.png --extract-text --detect-elements

# Detect specific elements
modelx vision detect screenshot.png button --min-confidence 0.8
```

### Swarm Orchestration Example

```bash
# Initialize the swarm
modelx swarm initialize

# Submit a large-scale goal
modelx swarm submit "Build a complete SaaS platform" --priority 9 --complexity 10 --capabilities research,coding,testing,deployment

# Check swarm status
modelx swarm metrics

# Scale up if needed
modelx swarm scale --directors 10 --sub-orchestrators 50

# Monitor goal progress
modelx swarm status <goal_id>

# Shutdown when done
modelx swarm shutdown
```

## Troubleshooting

### Connection Issues

If you get connection errors, check the API URL:

```bash
modelx config get api_url
```

Set the correct URL:

```bash
modelx config set api_url http://localhost:8000
```

### Authentication Issues

If you get authentication errors, check your API key:

```bash
modelx config get api_key
```

Set the correct key:

```bash
modelx config set api_key your-api-key
```

### Provider Issues

Check configured providers:

```bash
modelx config list-providers
```

Re-add the provider if needed:

```bash
modelx config add-provider anthropic your-api-key
```
