"""
RAG (Retrieval-Augmented Generation) Service - Production-Grade Implementation
Enhances LLM responses with knowledge from the integrated knowledge base.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import numpy as np

from src.knowledge.knowledge_integrator import KnowledgeIntegrator
from src.llm.deepseek_client import Message, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class RetrievedKnowledge:
    """Represents retrieved knowledge piece"""
    content: str
    source: str
    relevance_score: float
    metadata: Dict[str, Any]


@dataclass
class RAGContext:
    """Represents the RAG context for a query"""
    query: str
    retrieved_knowledge: List[RetrievedKnowledge]
    enhanced_prompt: str
    timestamp: datetime


class RAGService:
    """
    Production-grade RAG service that enhances LLM responses with knowledge
    from the integrated knowledge base using semantic search.
    """

    def __init__(self, knowledge_integrator: Optional[KnowledgeIntegrator] = None):
        """Initialize RAG service"""
        self.knowledge_integrator = knowledge_integrator
        self.max_knowledge_pieces = 5
        self.min_relevance_score = 0.3 # Lowered slightly to allow cross-encoder to rescue items
        self.use_rag = True
        self.reranker = None

        try:
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)
            logger.info("Cross-Encoder initialized for re-ranking.")
        except Exception as e:
            logger.warning(f"Could not initialize Cross-Encoder: {e}")

        if self.knowledge_integrator is None:
            try:
                self.knowledge_integrator = KnowledgeIntegrator()
                logger.info("RAG service initialized with knowledge integrator")
            except Exception as e:
                logger.warning(f"Could not initialize knowledge integrator: {e}")
                self.knowledge_integrator = None
                self.use_rag = False
        else:
            logger.info("RAG service initialized with provided knowledge integrator")

        # Source reputation scores (higher = more trusted)
        self.source_reputation = {
            "wikipedia": 1.0,
            "docs.python.org": 0.95,
            "developer.mozilla.org": 0.95,
            "react.dev": 0.9,
            "nextjs.org": 0.9,
            "pytorch.org": 0.9,
            "huggingface.co": 0.9,
            "kubernetes.io": 0.9,
            "docker.com": 0.9,
            "aws.amazon.com": 0.85,
            "hacker_news": 0.7,
            "web_crawl": 0.5,  # Default for unknown web sources
            "knowledge base": 0.6  # Default for ingested content
        }

    def get_source_reputation_score(self, source: str) -> float:
        """
        Get reputation score for a source.

        Args:
            source: Source URL or identifier

        Returns:
            Reputation score between 0.0 and 1.0
        """
        source_lower = source.lower()

        # Check for exact matches
        if source_lower in self.source_reputation:
            return self.source_reputation[source_lower]

        # Check for domain matches
        for domain, score in self.source_reputation.items():
            if domain in source_lower:
                return score

        # Default score for unknown sources
        return 0.5

    async def retrieve_relevant_knowledge(
        self,
        query: str,
        top_k: int = 5
    ) -> List[RetrievedKnowledge]:
        """
        Retrieve relevant knowledge pieces for a query using semantic search.
        """
        if not self.use_rag or self.knowledge_integrator is None:
            logger.debug("RAG disabled, skipping knowledge retrieval")
            return []

        try:
            knowledge_pieces = []
            search_results = []

            # 1. Vector Search
            if self.knowledge_integrator.vector_store:
                search_results = await self.knowledge_integrator.vector_store.search(
                    query=query,
                    n_results=top_k * 3  # Fetch more for re-ranking
                )

                for result in search_results:
                    metadata = result.get('metadata', {})
                    source = metadata.get('source_url', 'knowledge base')

                    # Get base relevance from semantic search
                    base_relevance = 1.0 - result.get('distance', 1.0)

                    # Apply source reputation weighting
                    source_reputation = self.get_source_reputation_score(source)
                    weighted_relevance = base_relevance * (0.7 + 0.3 * source_reputation)

                    knowledge_piece = RetrievedKnowledge(
                        content=result.get('document', ''),
                        source=source,
                        relevance_score=weighted_relevance,
                        metadata=metadata
                    )
                    knowledge_pieces.append(knowledge_piece)

            # 2. Graph Search Expansion
            expanded_pieces = []
            if self.knowledge_integrator.graph_store and search_results:
                # Grab the ID of the top hit to expand
                top_id = search_results[0].get('id')
                if top_id:
                    graph_results = await self.knowledge_integrator.get_related_content(top_id)
                    for gr in graph_results:
                        content = gr.get('content', '')
                        source = gr.get('metadata', {}).get('source_url', 'graph base')
                        metadata = gr.get('metadata', {})
                        # Get base relevance (we don't have distance from graph, so use a default base relevance of 0.5)
                        base_relevance = 0.5
                        # Apply source reputation weighting
                        source_reputation = self.get_source_reputation_score(source)
                        weighted_relevance = base_relevance * (0.7 + 0.3 * source_reputation)
                        expanded_pieces.append(RetrievedKnowledge(
                            content=content,
                            source=source,
                            relevance_score=weighted_relevance,
                            metadata=metadata
                        ))

            # Combine and deduplicate
            all_pieces = knowledge_pieces + expanded_pieces
            unique_contents = set()
            deduped = []
            for p in all_pieces:
                if p.content not in unique_contents:
                    unique_contents.add(p.content)
                    deduped.append(p)

            if not deduped:
                return []

            # 3. Cross-Encoder Re-ranking
            if self.reranker:
                pairs = [[query, p.content] for p in deduped]
                scores = self.reranker.predict(pairs)
                for p, score in zip(deduped, scores):
                    # Sigmoid to normalize score to 0-1 range
                    p.relevance_score = float(1 / (1 + np.exp(-score)))

                # Sort by new relevance score
                deduped.sort(key=lambda x: x.relevance_score, reverse=True)
            else:
                deduped.sort(key=lambda x: x.relevance_score, reverse=True)

            # Filter by relevance threshold and limit to top_k
            final_pieces = [p for p in deduped if p.relevance_score >= self.min_relevance_score][:top_k]
            return final_pieces

        except Exception as e:
            logger.error(f"Error retrieving knowledge: {e}")
            return []

    def build_enhanced_prompt(
        self,
        query: str,
        knowledge: List[RetrievedKnowledge],
        conversation_history: Optional[List[Message]] = None
    ) -> str:
        """
        Build an enhanced prompt that includes retrieved knowledge.
        """
        if not knowledge:
            return query

        knowledge_context = "Relevant knowledge from the system's learning:\n\n"
        for i, piece in enumerate(knowledge, 1):
            knowledge_context += f"{i}. {piece.content}\n"
            knowledge_context += f"   Source: {piece.source}\n"
            knowledge_context += f"   Relevance: {piece.relevance_score:.2f}\n\n"

        enhanced_prompt = f"""User Query: {query}

{knowledge_context}

Instructions:
- Use the provided knowledge to answer the user's question
- CRITICAL: If the provided knowledge (retrieved in real-time) contradicts your internal training data, prioritize the provided knowledge.
- Cite sources when using specific information from the knowledge
- If the knowledge is insufficient, acknowledge this and provide general guidance
- Maintain natural, conversational tone
- Be accurate and honest about what you know from the knowledge vs general knowledge

Answer:"""

        return enhanced_prompt

    async def enhance_query(
        self,
        query: str,
        conversation_history: Optional[List[Message]] = None,
        llm_client: Optional[Any] = None
    ) -> Tuple[str, List[RetrievedKnowledge]]:
        """
        Enhance a query with retrieved knowledge and optional query transformation.
        """
        search_query = query

        # Query Transformation
        if llm_client:
            try:
                transform_prompt = f"Rewrite the following user query to be highly optimized for a vector database search. Output ONLY the optimized query. Original: {query}"
                # Use duck typing for LLM Client (it has a chat method taking Messages)
                from src.llm.gemini_client import Message as GMessage
                resp = await llm_client.chat([GMessage(role="user", content=transform_prompt)])
                search_query = resp.content.strip()
                logger.info(f"Query transformed: {query} -> {search_query}")
            except Exception as e:
                logger.error(f"Query transformation failed: {e}")

        # Retrieve relevant knowledge
        knowledge = await self.retrieve_relevant_knowledge(search_query)

        if not knowledge:
            logger.debug("No relevant knowledge found, returning original query")
            return query, knowledge

        # Build enhanced prompt
        enhanced_query = self.build_enhanced_prompt(query, knowledge, conversation_history)

        logger.info(f"Enhanced query with {len(knowledge)} knowledge pieces")
        return enhanced_query, knowledge

    async def process_llm_response(
        self,
        llm_response: LLMResponse,
        retrieved_knowledge: List[RetrievedKnowledge]
    ) -> LLMResponse:
        """
        Process LLM response and add knowledge sources.
        """
        if not retrieved_knowledge:
            return llm_response

        sources = list(set([piece.source for piece in retrieved_knowledge]))
        llm_response.sources = sources

        return llm_response

    async def critique_response(
        self,
        query: str,
        response: str,
        knowledge: List[RetrievedKnowledge],
        llm_client: Any
    ) -> Tuple[str, bool]:
        """
        Critique the LLM response against retrieved knowledge.
        Returns (refined_response, was_changed).
        """
        if not knowledge:
            return response, False

        combined_context = "\n".join([f"- {k.content}" for k in knowledge])

        critique_prompt = f"""
        You are an accuracy reviewer. Review the following AI response against the provided facts.

        User Query: {query}

        Facts:
        {combined_context}

        AI Response:
        {response}

        Check for:
        1. Hallucinations (information not in facts).
        2. Contradictions.
        3. Missing critical details from the facts.

        If the response is accurate and complete, return 'ACCURATE'.
        If it needs correction, provide the fully corrected response.

        Review Outcome:"""

        try:
            critique_result = await llm_client.chat([Message(role="user", content=critique_prompt)])
            outcome = critique_result.content.strip()

            if outcome == "ACCURATE":
                return response, False
            else:
                logger.info("self_correction_applied", query=query)
                return outcome, True
        except Exception as e:
            logger.error("critique_failed", error=str(e))
            return response, False

    def get_rag_stats(self) -> Dict[str, Any]:
        stats = {
            "rag_enabled": self.use_rag,
            "knowledge_integrator_available": self.knowledge_integrator is not None,
            "max_knowledge_pieces": self.max_knowledge_pieces,
            "min_relevance_score": self.min_relevance_score
        }

        if self.knowledge_integrator and self.knowledge_integrator.vector_store:
            try:
                vector_stats = asyncio.create_task(
                    self.knowledge_integrator.vector_store.get_stats()
                )
                stats["vector_store"] = vector_stats.result()
            except Exception as e:
                logger.warning(f"Could not get vector store stats: {e}")

        return stats

    def enable_rag(self, enabled: bool = True):
        self.use_rag = enabled
        logger.info(f"RAG {'enabled' if enabled else 'disabled'}")

    def set_relevance_threshold(self, threshold: float):
        self.min_relevance_score = max(0.0, min(1.0, threshold))
        logger.info(f"Relevance threshold set to {self.min_relevance_score}")
