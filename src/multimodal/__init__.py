"""Multi-Modal Context Module (Phase 7).

This module enables agents to process visual information including:
- UI screenshot analysis
- Visual element detection
- Web page interaction via vision models
- Multi-modal memory integration
"""

from __future__ import annotations

from src.multimodal.vision_processor import VisionProcessor
from src.multimodal.screenshot_pipeline import ScreenshotPipeline
from src.multimodal.visual_interaction import VisualInteractionAgent
from src.multimodal.element_detector import ElementDetector

__all__ = [
    "VisionProcessor",
    "ScreenshotPipeline",
    "VisualInteractionAgent",
    "ElementDetector",
]
