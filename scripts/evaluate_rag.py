import asyncio
import json
import os
from src.llm.rag_service import RAGService
from src.llm.deepseek_client import DeepSeekClient
from src.llm.rag_evaluator import RAGEvaluator, EvalCase
from src.utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

async def main():
    # 1. Initialize services
    # Note: Assumes DEEPSEEK_API_KEY is in env
    try:
        llm_client = DeepSeekClient()
        rag_service = RAGService()
        evaluator = RAGEvaluator(rag_service, llm_client)
    except Exception as e:
        logger.error("initialization_failed", error=str(e))
        return

    # 2. Define test cases (Retail specific as per README vision)
    test_cases = [
        EvalCase(
            query="What are the current trends in organic milk pricing?",
            ground_truth="Organic milk prices are seeing a 5% increase due to supply chain constraints."
        ),
        EvalCase(
            query="How should I handle stockouts for electronics?",
            ground_truth="Increase safety stock by 20% and set up automated reorder alerts."
        ),
        EvalCase(
            query="Who is the founder of SmartSelf AI?",
            ground_truth="The project mentions it was founder-built but doesn't name a specific individual other than the GitHub handle genius-0963."
        )
    ]

    # 3. Run evaluation
    logger.info("starting_rag_evaluation", cases_count=len(test_cases))
    results = await evaluator.run_eval(test_cases)

    # 4. Report results
    avg_faithfulness = sum(r.faithfulness_score for r in results) / len(results)
    avg_relevance = sum(r.relevance_score for r in results) / len(results)
    avg_latency = sum(r.latency for r in results) / len(results)

    report = {
        "summary": {
            "avg_faithfulness": avg_faithfulness,
            "avg_relevance": avg_relevance,
            "avg_latency": avg_latency,
        },
        "details": [r.model_dump() for r in results]
    }

    print("\n--- RAG Evaluation Report ---")
    print(json.dumps(report, indent=2))
    
    # Save to file
    os.makedirs("docs/evals", exist_ok=True)
    with open("docs/evals/latest_rag_eval.json", "w") as f:
        json.dump(report, f, indent=2)
    logger.info("evaluation_complete", report_path="docs/evals/latest_rag_eval.json")

if __name__ == "__main__":
    asyncio.run(main())
