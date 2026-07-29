"""Stats and dashboard endpoints — migrated from web_server.py."""

import json
import time

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps.legacy_auth import get_current_user
from src.api.services import chat_runtime
from src.config.logging import get_logger
from src.config.settings import get_settings
from src.utils.auth import TokenData

router = APIRouter(prefix="/api", tags=["Stats"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("/stats")
async def get_stats(current_user: TokenData = Depends(get_current_user)):
    try:
        conv_stats = await chat_runtime.conversation_manager.get_stats()
        rag_stats = chat_runtime.rag_service.get_rag_stats()

        learning_stats = {}
        if hasattr(chat_runtime.learner, "stats"):
            from dataclasses import asdict

            learning_stats = asdict(chat_runtime.learner.stats)

        # Compute feedback stats from feedback.jsonl
        feedback_path = settings.data_dir / "feedback.jsonl"
        feedback_total, feedback_positive = 0, 0
        if feedback_path.exists():
            try:
                with open(feedback_path) as fh:
                    for raw in fh:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            entry = json.loads(raw)
                            feedback_total += 1
                            if entry.get("is_positive"):
                                feedback_positive += 1
                        except json.JSONDecodeError:
                            continue
            except OSError:
                pass

        return {
            "conversations": conv_stats,
            "rag": rag_stats,
            "learning": learning_stats,
            "learning_active": chat_runtime._learning_active,
            "feedback": {
                "total": feedback_total,
                "positive": feedback_positive,
                "satisfaction_rate": (
                    round(feedback_positive / feedback_total, 2) if feedback_total > 0 else 0.0
                ),
            },
        }
    except Exception as e:
        logger.error("stats_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/dashboard")
async def get_dashboard_metrics(current_user: TokenData = Depends(get_current_user)):
    chunk_count = 0
    rag_enabled = getattr(chat_runtime.rag_service, "use_rag", False)
    try:
        if rag_enabled and hasattr(chat_runtime.rag_service, "knowledge_integrator"):
            vi = chat_runtime.rag_service.knowledge_integrator.vector_store
            if vi:
                chunk_count = vi.collection.count()
    except Exception:
        pass

    feedback_path = settings.data_dir / "feedback.jsonl"
    feedback_total, feedback_positive = 0, 0
    if feedback_path.exists():
        try:
            with open(feedback_path) as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entry = json.loads(raw)
                        feedback_total += 1
                        if entry.get("is_positive"):
                            feedback_positive += 1
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    conv_count = 0
    try:
        user_convs = await chat_runtime.conversation_manager.get_user_conversations(
            user_id=current_user.user_id, limit=9999
        )
        conv_count = len(user_convs) if user_convs else 0
    except Exception:
        pass

    uptime = round(time.time() - chat_runtime.SERVER_START_TIME, 1)

    return {
        "knowledge_base": {
            "chunk_count": chunk_count,
            "rag_enabled": rag_enabled,
        },
        "feedback": {
            "total": feedback_total,
            "positive": feedback_positive,
            "satisfaction_rate": (
                round(feedback_positive / feedback_total, 2) if feedback_total > 0 else 0.0
            ),
        },
        "conversations": {
            "total": conv_count,
        },
        "system": {
            "llm_provider": settings.llm_provider,
            "uptime_seconds": uptime,
            "version": settings.app_version,
            "learning_active": chat_runtime._learning_active,
        },
    }
