## SECTION 9: META-LEARNING DOCUMENTATION

The Meta-Learning subsystem transforms ModelX from a static pipeline into an adaptive cognitive architecture. It observes the agent's successes and failures and updates the operational parameters of the system over time.

### Key Components

#### Reflection
After every task execution sequence, the `ReflectionAgent` evaluates the traces. It compares the initial `Goal` against the actual `Outputs` and generates a structured critique identifying root causes of failure (e.g., "Dependency missing", "Syntax error", "Hallucinated API endpoint").

#### Learning Engine
Ingests reflections. If a root cause appears repeatedly (e.g., 3 failures due to missing environment variables), the `LearningEngine` abstracts this into a `LearningPattern`. 

#### Strategy Engine
When a task is classified by the `TaskClassifier` (e.g., as `code_refactor`), the `StrategyEngine` queries the database for `Strategies` tied to that task type. It ranks them by `confidence_score` (calculated as successful executions / total executions). The Orchestrator applies the highest-ranked strategy. If it fails, the score decreases. Over time, poor strategies fall out of rotation.

### Meta-Learning Workflow
```mermaid
sequenceDiagram
    participant Executor
    participant ReflectionAgent
    participant LearningEngine
    participant StrategyEngine
    
    Executor->>ReflectionAgent: Task Execution Failed
    ReflectionAgent->>LearningEngine: Submit Root Cause (Missing Package)
    LearningEngine->>LearningEngine: Detect Pattern (Occurred 3x)
    LearningEngine->>StrategyEngine: Update Strategy (Penalty)
    StrategyEngine->>StrategyEngine: Decrease Confidence Score
    LearningEngine->>StrategyEngine: Propose New Strategy Variant
```

---

## SECTION 10: AUTONOMOUS RESEARCH SYSTEM

This system allows ModelX to proactively construct its own goals without user input, effectively allowing it to research, code, and learn indefinitely in the background.

### Mechanisms

1. **Knowledge Gap Detection**: The `KnowledgeGraphReasoner` periodically queries Neo4j for nodes with a `CONTRADICTS` relationship, or nodes marked as `REQUIRES` but missing in the database.
2. **Curiosity Engine**: Evaluates the detected gaps using a heuristic: `Score = (Novelty + Uncertainty + Impact + Importance) / 4`. 
3. **Goal Generation**: Gaps with a Curiosity Score > 0.6 are passed to the `GoalGenerator` LLM to formulate an actionable research objective.
4. **Research Director**: Groups generated goals into long-term `ResearchPortfolios` and initializes a `ResearchTrack`.
5. **Long Horizon Planner**: Decomposes the high-level goal into a hierarchical tree of up to 100+ deterministic subgoals (`GoalTree`).

### Autonomous Workflow
```mermaid
graph TD
    A[(Neo4j Knowledge Graph)] -->|Contradictions/Gaps| B[Knowledge Gap Detector]
    B --> C[Curiosity Engine]
    C -->|Score > Threshold| D[Goal Generator]
    D --> E[Research Director]
    E --> F[Portfolio Manager]
    E --> G[Long Horizon Planner]
    G --> H[(Postgres: Goal Tree)]
    H --> I[Orchestrator Execution Loop]
    I -->|Results| J[Knowledge Graph Update]
    J --> A
```

---

## SECTION 11: LANGGRAPH STATE MACHINE

LangGraph enforces deterministic control flow over the LLM agents. The `AgentStateDict` is passed sequentially from node to node.

### Complete StateGraph Flow

```mermaid
stateDiagram-v2
    [*] --> AnalyzeGoal
    AnalyzeGoal --> RecallMemories
    RecallMemories --> ReplayExperiences
    ReplayExperiences --> DecomposeTasks
    DecomposeTasks --> ClassifyTask
    
    ClassifyTask --> SelectStrategy
    SelectStrategy --> RouteTask
    
    RouteTask --> ExecuteResearch : if Research
    RouteTask --> ExecuteTask : if Execution
    RouteTask --> ExecuteMemoryOp : if Memory
    RouteTask --> Reflect : if Max Iterations / Complete
    
    ExecuteResearch --> IntegrateResults
    ExecuteTask --> IntegrateResults
    ExecuteMemoryOp --> IntegrateResults
    
    IntegrateResults --> DynamicReplan : if Continue
    IntegrateResults --> Reflect : if Failed / Done
    
    DynamicReplan --> ClassifyTask
    
    Reflect --> ExtractLearnings
    ExtractLearnings --> UpdateStrategies
    UpdateStrategies --> KnowledgeGapDetection
    
    KnowledgeGapDetection --> GoalGeneration
    GoalGeneration --> CuriosityEvaluation
    CuriosityEvaluation --> ResearchDirector
    ResearchDirector --> ResearchPortfolio
    ResearchPortfolio --> KnowledgeGraphUpdate
    KnowledgeGraphUpdate --> GenerateReport
    GenerateReport --> [*]
```

### State Management
The graph relies on the `AgentStateDict`, a `TypedDict` containing all transient state:
- `task_plan`: List of tasks to execute.
- `current_task_index`: Pointer to current task.
- `task_results`: Dictionary accumulating outputs.
- `errors`: List of failures.
- `iteration_count`: Incremented per loop to prevent infinite loops (hard stop at `max_iterations`).
