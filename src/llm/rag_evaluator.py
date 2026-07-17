import asyncio
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from src.llm.rag_service import RAGService
from src.llm.gemini_client import GeminiClient, Message
from src.config.logging import get_logger

logger = get_logger(__name__)

class EvalCase(BaseModel):
    query: str
    ground_truth: str
    context_required: bool = True

class EvalResult(BaseModel):
    query: str
    context_required: bool
    response: str
    ground_truth: str
    retrieved_contexts: List[str]
    faithfulness_score: float  # 0 to 1
    relevance_score: float      # 0 to 1
    latency: float

class RAGEvaluator:
    """
    Evaluates the RAG pipeline for quality and safety.
    """
    def __init__(self, rag_service: RAGService, llm_client: GeminiClient):
        self.rag_service = rag_service
        self.llm_client = llm_client

    async def evaluate_faithfulness(self, response: str, contexts: List[str]) -> float:
        """
        Calculates if the response is supported by the context (prevents hallucination).
        In a production setting, this would use a 'Judge LLM' or NLI model.
        """
        if not contexts:
            return 1.0 # Nothing to contradict

        combined_context = "\n".join(contexts)

        # Simple LLM-based judge prompt
        prompt = f"""
        Analyze the following response and the context it should be based on.
        Determine if the response contains any information NOT supported by the context or if it contradicts the context.

        Context:
        {combined_context}

        Response:
        {response}

        Output only a single number between 0.0 and 1.0, where 1.0 means perfectly faithful to the context and 0.0 means it hallucinated or contradicted.
        Score:"""

        try:
            # We use the LLM to judge itself or use a different provider if available
            judge_response = await self.llm_client.chat([Message(role="user", content=prompt)])
            score_str = judge_response.content.strip()
            # Extract number
            import re
            match = re.search(r"([0-1]\.\d+|[0-1])", score_str)
            return float(match.group(1)) if match else 0.5
        except Exception as e:
            logger.error("faithfulness_eval_failed", error=str(e))
            return 0.5

    async def evaluate_relevance(self, query: str, response: str) -> float:
        """
        Calculates if the response directly addresses the user query.
        """
        prompt = f"""
        Analyze the relevance of the response to the user query.
        Query: {query}
        Response: {response}

        Output only a single number between 0.0 and 1.0, where 1.0 means highly relevant and 0.0 means irrelevant.
        Score:"""

        try:
            judge_response = await self.llm_client.chat([Message(role="user", content=prompt)])
            score_str = judge_response.content.strip()
            import re
            match = re.search(r"([0-1]\.\d+|[0-1])", score_str)
            return float(match.group(1)) if match else 0.5
        except Exception as e:
            logger.error("relevance_eval_failed", error=str(e))
            return 0.5

    async def run_eval(self, cases: List[EvalCase]) -> List[EvalResult]:
        results = []
        async with self.llm_client:
            for case in cases:
                start_time = time.time()

                # 1. RAG Step
                enhanced_query, knowledge = await self.rag_service.enhance_query(case.query, llm_client=self.llm_client)
                contexts = [k.content for k in knowledge]

                # 2. Generation Step
                llm_response = await self.llm_client.chat([Message(role="user", content=enhanced_query)])
                latency = time.time() - start_time

                # 3. Scoring
                faithfulness = await self.evaluate_faithfulness(llm_response.content, contexts)
                relevance = await self.evaluate_relevance(case.query, llm_response.content)

                results.append(EvalResult(
                    query=case.query,
                    context_required=case.context_required,
                    response=llm_response.content,
                    ground_truth=case.ground_truth,
                    retrieved_contexts=contexts,
                    faithfulness_score=faithfulness,
                    relevance_score=relevance,
                    latency=latency
                ))

        return results
