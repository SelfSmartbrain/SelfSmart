# V3.1 Benchmark Campaign

**Transition from Architecture-Driven Development to Evidence-Driven Architecture**

## Overview

V3.1 is a critical milestone in ModelX development. Instead of building more phases, we gather real performance data through benchmark campaigns to demonstrate actual capability.

### The Critical Distinction

**Can Measure Intelligence ≠ Has Demonstrated Intelligence**

V3.1 addresses the gap between having validation infrastructure and having validation results.

## Campaign Structure

### Repository Campaigns

- **Small Repository Campaign**: 200 tasks (1k-5k LOC)
- **Medium Repository Campaign**: 200 tasks (10k-50k LOC)
- **Large Repository Campaign**: 100-500 tasks (100k+ LOC)

### Task Types

- **Bug Fixing**: Fix bugs and errors in code
- **Refactoring**: Improve code structure without changing behavior
- **Test Generation**: Generate comprehensive test coverage
- **Feature Implementation**: Add new features and functionality

## Metrics Collected

For every task, we collect:

- **Task Success**: Did the task complete successfully?
- **Test Pass Rate**: Percentage of tests that pass
- **Patch Acceptance**: Were patches accepted (applied cleanly)?
- **Rollback Rate**: Did changes need to be rolled back?
- **Latency**: Time taken to complete the task
- **Cost**: USD cost of API calls
- **Memory Usage**: Memory consumption in MB
- **Planning Quality**: Quality of the execution plan (0-1 score)
- **Decision Quality**: Quality of decisions made during execution (0-1 score)

## Ablation Configurations

We run the same campaigns with different subsystems disabled to measure their impact:

1. **Full ModelX**: All subsystems enabled (baseline)
2. **Memory Disabled**: Memory system disabled
3. **Concepts Disabled**: Concept engine disabled
4. **World Model Disabled**: World model disabled
5. **Governance Disabled**: Governance system disabled
6. **Decision Intelligence Disabled**: Decision intelligence disabled

## Required Outputs

The campaign generates:

- **benchmark_results.json**: Comprehensive results across all campaigns
- **benchmark_report.md**: Human-readable benchmark report
- **capability_growth_report.md**: Analysis of subsystem contributions
- **ablation_results.json**: Detailed ablation study results

## Installation

```bash
cd /Users/subh/Documents/ModelX
```

## Usage

### Run All Campaigns

```bash
python tests/validation/v31_campaign.py
```

This will:
1. Run small, medium, and large repository campaigns
2. Run ablation study on the small campaign
3. Generate all required output files

### Run Specific Campaign

```bash
python tests/validation/v31_campaign.py --campaign small_repo_campaign
```

### Run Ablation Study Only

```bash
python tests/validation/v31_campaign.py --ablation small_repo_campaign
```

### Use Real Executor

To use the real ModelX executor instead of mock:

```python
# Modify the campaign initialization
campaign = V31BenchmarkCampaign(output_dir=args.output_dir, use_real_executor=True)
```

### Custom Output Directory

```bash
python tests/validation/v31_campaign.py --output-dir /path/to/output
```

## Architecture

### Components

1. **v31_campaign.py**: Main campaign runner
   - Campaign registration and execution
   - Ablation study coordination
   - Report generation

2. **v31_executor.py**: Task execution framework
   - RealTaskExecutor: Integrates with actual ModelX components
   - MockTaskExecutor: Simulates execution for testing
   - ExecutionContext: Context for task execution

3. **v31_metrics.py**: Metrics collection
   - Planning quality measurement
   - Decision quality measurement
   - Patch acceptance measurement
   - Rollback rate measurement
   - Test pass rate measurement
   - Resource usage measurement

### Integration with ModelX

The executor integrates with:
- `src/coding/planner.py`: Execution plan generation
- `src/coding/code_editor.py`: Code editing and patch application
- `src/coding/test_runner.py`: Test execution
- `src/coding/repository_analyzer.py`: Repository analysis

## Output Format

### benchmark_results.json

```json
{
  "campaign_version": "V3.1",
  "timestamp": "2026-06-24 03:22:00",
  "total_campaigns": 3,
  "total_tasks": 500,
  "campaigns": {
    "small_repo_campaign": {
      "config": { ... },
      "statistics": { ... }
    }
  },
  "aggregate_statistics": {
    "total_tasks": 500,
    "overall_success_rate": 0.84,
    "avg_test_pass_rate": 0.92,
    "patch_acceptance_rate": 0.88,
    "rollback_rate": 0.12,
    "avg_latency_seconds": 45.3,
    "total_cost_usd": 25.50,
    "avg_planning_quality": 0.82,
    "avg_decision_quality": 0.79,
    "by_task_type": { ... }
  }
}
```

### benchmark_report.md

Human-readable report with:
- Campaign summary
- Overall statistics
- Campaign details
- Performance breakdown

### capability_growth_report.md

Analysis answering:
- Which subsystem contributes the most to real coding performance?
- Impact of each subsystem on success rate
- Planning quality deltas
- Decision quality deltas

### ablation_results.json

Detailed ablation study results:
- Baseline vs ablated performance
- Impact percentages for each subsystem
- Statistical significance

## The Most Valuable Experiment

The ablation study is the most valuable experiment because it answers:

**Which subsystem contributes the most to real coding performance?**

This answer is worth more than any future phase because it drives evidence-driven architecture decisions.

## Evidence-Driven Architecture

After V3.1, V3.2, and V3.3 are complete, the roadmap should be driven by benchmark data:

```
Weakest Component
↓
Improve It
↓
Benchmark Again
↓
Measure Gain
```

Instead of:

```
New Idea
↓
New Phase
↓
More Modules
```

## Current Status

- ✅ Capability Verification Infrastructure
- ✅ Repository Benchmark Infrastructure
- ✅ Coding Runtime Infrastructure
- ✅ Long-Horizon Validation Infrastructure
- ✅ V3.1 Campaign Framework
- ⏳ Capability Verification Results (pending campaign execution)

## Next Steps

1. Run Small Repository Campaign (200 tasks)
2. Run Medium Repository Campaign (200 tasks)
3. Run Large Repository Campaign (100-500 tasks)
4. Analyze results
5. Identify weakest component
6. Improve it
7. Benchmark again
8. Measure gain

## Project Maturity Assessment

Based on the V3.1 framework:

- **Architecture Maturity**: 9/10
- **Validation Maturity**: 9/10
- **Evidence Maturity**: 6.5/10 (pending actual campaign results)

The next jump comes from data.

## Expected Results Example

If the benchmark campaign produces evidence like:

```
500 Tasks
Success Rate: 84%

Memory: +10%
Concepts: +4%
World Model: +8%
Governance: +12%
Decision Intelligence: +15%
```

Then ModelX has demonstrated evidence-driven architecture instead of architecture-driven development.

## Contact

For questions about V3.1, refer to the main ModelX documentation or the validation team.
