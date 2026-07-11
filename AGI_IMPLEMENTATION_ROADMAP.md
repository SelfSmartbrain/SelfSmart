# ModelX → AGI Implementation Roadmap

## Executive Summary
This roadmap addresses the 5 critical gaps identified in `docs/analysis/15_agi_readiness.md` to progress from "AGI-inspired agent platform" toward genuine autonomous general intelligence.

---

## 1. Dynamic Re-Planning & Continuous Reasoning (Planning: 80% → 95%)

### 1.1 Environmental Drift Detection
**File:** `src/reasoning/drift_detector.py` (NEW)
```python
class EnvironmentalDriftDetector:
    def __init__(self, memory_fabric, threshold=0.3):
        self.memory = memory_fabric
        self.threshold = threshold
    
    async def detect_drift(self, current_plan, execution_context):
        # Compare expected vs actual state using embeddings
        expected = await self._get_expected_state(current_plan)
        actual = await self._get_actual_state(execution_context)
        drift_score = cosine_similarity(expected.embedding, actual.embedding)
        return drift_score < self.threshold
```

### 1.2 Reactive Re-Planner
**File:** `src/reasoning/reactive_planner.py` (NEW)
```python
class ReactiveRePlanner:
    def __init__(self, llm, memory_fabric, drift_detector):
        self.llm = llm
        self.memory = memory_fabric
        self.drift_detector = drift_detector
    
    async def maybe_replan(self, plan_id, context):
        if await self.drift_detector.detect_drift(plan_id, context):
            new_plan = await self._generate_corrective_plan(plan_id, context)
            await self.memory.update_plan(plan_id, new_plan, version="auto")
            return new_plan
        return None
```

### 1.3 Integration Point
**Modify:** `src/reasoning/planner.py:45` — inject `ReactiveRePlanner` into planning loop

---

## 2. Hierarchical Multi-Agent Delegation (Multi-Agent: 60% → 90%)

### 2.1 Agent Registry & Capability Advertisement
**File:** `src/cognition/agent_registry.py` (NEW)
```python
class AgentRegistry:
    def __init__(self, neo4j_client):
        self.graph = neo4j_client
    
    async def register_agent(self, agent_id, capabilities, parent_id=None):
        # Store in Neo4j with capability vectors for discovery
        await self.graph.run("""
            MERGE (a:Agent {id: $id})
            SET a.capabilities = $caps, a.parent = $parent
        """, id=agent_id, caps=capabilities, parent=parent_id)
    
    async def find_capable_agents(self, required_capabilities):
        # Vector search over capability embeddings
        return await self.graph.vector_search("Agent", required_capabilities)
```

### 2.2 Delegation Protocol
**File:** `src/cognition/delegation_protocol.py` (NEW)
```python
class DelegationProtocol:
    def __init__(self, registry, message_broker):
        self.registry = registry
        self.broker = message_broker
    
    async def delegate(self, task, required_caps, delegator_id):
        agents = await self.registry.find_capable_agents(required_caps)
        selected = await self._select_best(agents, task)
        await self.broker.publish(f"agent.{selected.id}.tasks", {
            "task": task,
            "delegator": delegator_id,
            "deadline": self._calculate_deadline(task)
        })
        return selected.id
```

### 2.3 Sub-Agent Task Resolution
**Modify:** `src/cognition/swarm.py` — replace flat coordination with hierarchical delegation

---

## 3. Long-Horizon Task Persistence (Long-Horizon: 50% → 85%)

### 3.1 Context Compression Engine
**File:** `src/memory/context_compressor.py` (NEW)
```python
class ContextCompressor:
    def __init__(self, llm, vector_store):
        self.llm = llm
        self.vectors = vector_store
    
    async def compress(self, working_memory, max_tokens=8000):
        # 1. Cluster memories by topic (k-means on embeddings)
        clusters = await self._cluster_memories(working_memory)
        
        # 2. Summarize each cluster via LLM
        summaries = await asyncio.gather(*[
            self._summarize_cluster(c) for c in clusters
        ])
        
        # 3. Store summaries as compressed long-term memories
        for s in summaries:
            await self.vectors.upsert(s.embedding, s.content, metadata=s.meta)
        
        return summaries
    
    async def _summarize_cluster(self, cluster):
        prompt = f"Compress these memories into key insights:\n{cluster}"
        return await self.llm.ainvoke(prompt)
```

### 3.2 Automatic Compression Scheduler
**File:** `src/runtime/compression_scheduler.py` (NEW)
```python
class CompressionScheduler:
    def __init__(self, memory_fabric, compressor, trigger_threshold=0.8):
        self.memory = memory_fabric
        self.compressor = compressor
        self.threshold = trigger_threshold
    
    async def check_and_compress(self, agent_id):
        wm = await self.memory.get_working_memory(agent_id)
        if wm.token_usage / wm.max_tokens > self.threshold:
            await self.compressor.compress(wm)
```

### 3.3 Episodic Checkpointing
**Modify:** `src/memory/episodic_memory.py` — add `create_checkpoint(agent_id, task_id)` for resumable long tasks

---

## 4. MCP Standard Integration (Tool Use: 75% → 95%)

### 4.1 MCP Client Implementation
**File:** `src/tools/mcp_client.py` (NEW)
```python
class MCPClient:
    def __init__(self, transport="stdio"):
        self.transport = transport
        self.servers = {}
    
    async def connect_server(self, name, command, args):
        # Spawn MCP server subprocess
        proc = await asyncio.create_subprocess_exec(
            command, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE
        )
        self.servers[name] = {"proc": proc, "tools": await self._discover_tools(proc)}
    
    async def call_tool(self, server_name, tool_name, params):
        server = self.servers[server_name]
        request = {"jsonrpc": "2.0", "method": f"tools/{tool_name}", "params": params}
        server["proc"].stdin.write(json.dumps(request).encode() + b"\n")
        return json.loads((await server["proc"].stdout.readline()).decode())
```

### 4.2 Tool Registry Unification
**Modify:** `src/tools/base.py` — add `MCPTool` subclass that wraps MCP calls

### 4.3 Capability Discovery
**File:** `src/tools/mcp_discovery.py` (NEW)
```python
async def discover_mcp_capabilities(client: MCPClient) -> List[ToolSchema]:
    all_tools = []
    for name, server in client.servers.items():
        for tool in server["tools"]:
            all_tools.append(ToolSchema(
                name=f"{name}.{tool['name']}",
                description=tool["description"],
                parameters=tool["inputSchema"]
            ))
    return all_tools
```

---

## 5. Continuous Self-Improvement Loop (Self-Reflection: 90% → 98%)

### 5.1 Meta-Learning Engine Enhancement
**Modify:** `src/cognition/meta_learning.py` — add:
```python
async def evolve_strategies(self, performance_data):
    # Genetic algorithm over strategy parameters
    population = self._initialize_population(performance_data)
    for generation in range(10):
        fitness = await self._evaluate_fitness(population)
        population = self._crossover_mutation(population, fitness)
    return self._select_best(population)
```

### 5.2 Architecture Self-Modification
**File:** `src/autonomous_development/architecture_evolver.py` (NEW)
```python
class ArchitectureEvolver:
    def __init__(self, repo_optimizer, test_runner):
        self.optimizer = repo_optimizer
        self.tests = test_runner
    
    async def propose_improvements(self, metrics):
        # Analyze bottlenecks → propose code changes → validate via tests
        bottlenecks = self._analyze_bottlenecks(metrics)
        patches = await self.optimizer.generate_patches(bottlenecks)
        validated = []
        for patch in patches:
            if await self.tests.validate_patch(patch):
                validated.append(patch)
        return validated
```

---

## 6. Cross-Cutting Infrastructure

### 6.1 Unified Cognitive Bus
**File:** `src/cognition/cognitive_bus.py` (NEW)
```python
class CognitiveBus:
    """Central event bus for all cognitive modules"""
    def __init__(self):
        self.subscribers = defaultdict(list)
    
    async def emit(self, event_type, payload):
        for handler in self.subscribers[event_type]:
            await handler(payload)
    
    def subscribe(self, event_type, handler):
        self.subscribers[event_type].append(handler)
```

### 6.2 Configuration
**Modify:** `src/core/config.py` — add AGI feature flags:
```python
AGI_FEATURES = {
    "dynamic_replanning": True,
    "hierarchical_delegation": True,
    "context_compression": True,
    "mcp_integration": True,
    "architecture_evolution": False  # Requires human approval
}
```

---

## Implementation Priority & Timeline

| Phase | Focus | Duration | Key Deliverables |
|-------|-------|----------|------------------|
| **Phase 1** | Long-Horizon + MCP | 4 weeks | Context compression, MCP client, tool unification |
| **Phase 2** | Multi-Agent Hierarchy | 3 weeks | Agent registry, delegation protocol, sub-agent resolution |
| **Phase 3** | Dynamic Reasoning | 3 weeks | Drift detector, reactive replanner, integration |
| **Phase 4** | Self-Improvement Loop | 4 weeks | Meta-learning evolution, architecture evolver (human-gated) |
| **Phase 5** | Integration & Hardening | 2 weeks | Cognitive bus, config flags, full test coverage |

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Task completion (multi-day) | 50% | 85% | `tests/e2e/long_horizon_test.py` |
| Delegation success rate | 60% | 90% | `tests/integration/delegation_test.py` |
| Re-planning accuracy | N/A | 80% | `tests/unit/drift_detection_test.py` |
| MCP tool coverage | 0 | 20+ servers | `src/tools/mcp_catalog.json` |
| Self-improvement patches applied | 0 | 5+/month | CI/CD pipeline metrics |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Context compression loses critical info | Human-in-the-loop validation for first 100 compressions |
| Recursive self-modification instability | Architecture evolver requires explicit approval gate |
| MCP server security | Sandbox all MCP subprocesses; capability allowlists |
| Multi-agent deadlock | Timeout + fallback to monolithic execution |

---

## Getting Started

```bash
# 1. Create feature branches
git checkout -b agi/phase1-long-horizon
git checkout -b agi/phase2-multiagent
# ... etc

# 2. Run baseline tests
pytest tests/ -v --tb=short

# 3. Implement Phase 1 (start with context_compressor.py)
# 4. Add integration tests for each new module
# 5. Submit PRs with AGI_READINESS_UPDATE.md documenting score changes
```