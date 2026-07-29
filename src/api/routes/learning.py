"""Learning and training endpoints — migrated from web_server.py."""

import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps.legacy_auth import get_current_user
from src.api.services import chat_runtime
from src.config.logging import get_logger
from src.tasks.learning_tasks import _run_learning_loop
from src.tasks.training_tasks import run_model_training
from src.utils.auth import TokenData

router = APIRouter(prefix="/api", tags=["Learning"])
logger = get_logger(__name__)


class LearnRequest(BaseModel):
    urls: List[str]


@router.post("/learning/start")
async def start_learning(current_user: TokenData = Depends(get_current_user)):
    if (
        chat_runtime._learning_active
        and chat_runtime._learning_task
        and not chat_runtime._learning_task.done()
    ):
        return {"success": False, "message": "Learning pipeline already running"}
    chat_runtime._learning_active = True
    chat_runtime._learning_task = asyncio.create_task(_run_learning_loop())
    logger.info("learning_started", user=current_user.email)
    return {"success": True, "message": "Learning pipeline started"}


@router.post("/learning/stop")
async def stop_learning(current_user: TokenData = Depends(get_current_user)):
    if chat_runtime._learning_task and not chat_runtime._learning_task.done():
        chat_runtime._learning_task.cancel()
        chat_runtime._learning_active = False
        logger.info("learning_stopped", user=current_user.email)
        return {"success": True, "message": "Learning pipeline stopped"}
    return {"success": False, "message": "No active learning task to stop"}


@router.post("/learning/learn")
async def learn_urls(request: LearnRequest, current_user: TokenData = Depends(get_current_user)):
    try:
        result = await chat_runtime.learner.manual_learning_session(request.urls)
        return result
    except Exception as e:
        logger.error("manual_learning_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/training/start")
async def start_training(current_user: TokenData = Depends(get_current_user)):
    try:
        task = run_model_training.delay()
        return {
            "success": True,
            "message": "Model training started in background",
            "task_id": task.id,
        }
    except Exception as e:
        logger.error("training_start_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, current_user: TokenData = Depends(get_current_user)):
    from celery.result import AsyncResult

    res = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": res.status,
        "result": res.result if res.ready() else None,
    }
