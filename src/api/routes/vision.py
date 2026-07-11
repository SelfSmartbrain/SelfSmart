"""Vision Processing API Routes (Phase 7)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from src.api.dependencies import get_db_session
from src.config.logging import get_logger
from src.multimodal.vision_processor import VisionProcessor, ScreenshotAnalysis
from src.multimodal.screenshot_pipeline import ScreenshotPipeline
from src.multimodal.element_detector import ElementDetector
from src.multimodal.visual_interaction import VisualInteractionAgent, InteractionAction, InteractionResult

logger = get_logger(__name__)

router = APIRouter(prefix="/vision", tags=["vision"])


# ---------------------------------------------------------------------------
# Request/Response Schemas
# ---------------------------------------------------------------------------


class ScreenshotUploadRequest(BaseModel):
    """Request to upload and analyze a screenshot."""
    
    url: str | None = Field(None, description="URL where screenshot was captured")
    session_id: UUID | None = Field(None, description="Associated session ID")
    task_id: UUID | None = Field(None, description="Associated task ID")
    extract_text: bool = Field(True, description="Extract text from screenshot")
    detect_elements: bool = Field(True, description="Detect UI elements")


class ScreenshotAnalysisResponse(BaseModel):
    """Response from screenshot analysis."""
    
    screenshot_id: str
    image_hash: str
    layout_summary: str
    elements_count: int
    interactive_elements_count: int
    text_regions_count: int
    analysis: dict[str, Any]


class ElementDetectionRequest(BaseModel):
    """Request to detect elements in a screenshot."""
    
    element_type: str = Field(..., description="Type of element to detect")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0)


class ElementDetectionResponse(BaseModel):
    """Response from element detection."""
    
    elements: list[dict[str, Any]]
    count: int


class InteractionRequest(BaseModel):
    """Request to perform visual interaction."""
    
    action_type: str = Field(..., description="Type: click, type, scroll, navigate")
    element_id: str | None = Field(None, description="ID of element to interact with")
    coordinates: tuple[int, int] | None = Field(None, description="Screen coordinates")
    text: str | None = Field(None, description="Text to type")
    url: str | None = Field(None, description="URL to navigate to")


class InteractionResponse(BaseModel):
    """Response from visual interaction."""
    
    success: bool
    action_type: str
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebCaptureRequest(BaseModel):
    """Request to capture screenshot from URL."""
    
    url: str = Field(..., description="URL to capture")
    viewport_width: int = Field(1920, description="Viewport width")
    viewport_height: int = Field(1080, description="Viewport height")
    wait_for_selector: str | None = Field(None, description="CSS selector to wait for")
    analyze: bool = Field(True, description="Analyze screenshot after capture")


class WebCaptureResponse(BaseModel):
    """Response from web capture."""
    
    screenshot_id: str
    url: str
    analysis: dict[str, Any] | None = None
    interactive_elements: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Global Instances
# ---------------------------------------------------------------------------


_vision_processor: VisionProcessor | None = None
_screenshot_pipeline: ScreenshotPipeline | None = None
_element_detector: ElementDetector | None = None
_visual_interaction_agent: VisualInteractionAgent | None = None


def get_vision_processor() -> VisionProcessor:
    """Get or create vision processor instance."""
    global _vision_processor
    if _vision_processor is None:
        _vision_processor = VisionProcessor()
    return _vision_processor


def get_screenshot_pipeline() -> ScreenshotPipeline:
    """Get or create screenshot pipeline instance."""
    global _screenshot_pipeline
    if _screenshot_pipeline is None:
        _screenshot_pipeline = ScreenshotPipeline()
    return _screenshot_pipeline


def get_element_detector() -> ElementDetector:
    """Get or create element detector instance."""
    global _element_detector
    if _element_detector is None:
        _element_detector = ElementDetector()
    return _element_detector


def get_visual_interaction_agent() -> VisualInteractionAgent:
    """Get or create visual interaction agent instance."""
    global _visual_interaction_agent
    if _visual_interaction_agent is None:
        _visual_interaction_agent = VisualInteractionAgent()
    return _visual_interaction_agent


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=ScreenshotAnalysisResponse)
async def analyze_screenshot(
    request: ScreenshotUploadRequest,
    file: UploadFile = File(...)
) -> ScreenshotAnalysisResponse:
    """Upload and analyze a screenshot for visual elements and text."""
    try:
        processor = get_vision_processor()
        
        # Read uploaded file
        image_data = await file.read()
        
        # Analyze screenshot
        analysis = await processor.analyze_screenshot(
            image_data,
            extract_text=request.extract_text,
            detect_elements=request.detect_elements
        )
        
        return ScreenshotAnalysisResponse(
            screenshot_id=analysis.image_hash,
            image_hash=analysis.image_hash,
            layout_summary=analysis.layout_summary,
            elements_count=len(analysis.elements),
            interactive_elements_count=len(analysis.interactive_elements),
            text_regions_count=len(analysis.text_regions),
            analysis=analysis.model_dump()
        )
    except Exception as e:
        logger.error(f"Error analyzing screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-elements", response_model=ElementDetectionResponse)
async def detect_elements(
    request: ElementDetectionRequest,
    file: UploadFile = File(...)
) -> ElementDetectionResponse:
    """Detect specific type of elements in a screenshot."""
    try:
        detector = get_element_detector()
        
        # Read uploaded file
        image_data = await file.read()
        
        # Convert to PIL Image
        from PIL import Image
        from io import BytesIO
        image = Image.open(BytesIO(image_data))
        
        # Detect elements
        if request.element_type == "button":
            elements = await detector.detect_buttons(image)
        elif request.element_type == "input":
            elements = await detector.detect_inputs(image)
        elif request.element_type == "link":
            elements = await detector.detect_links(image)
        else:
            elements = await detector.detect_all_elements(image)
        
        # Filter by confidence
        filtered_elements = [e for e in elements if e.confidence >= request.min_confidence]
        
        return ElementDetectionResponse(
            elements=[e.model_dump() for e in filtered_elements],
            count=len(filtered_elements)
        )
    except Exception as e:
        logger.error(f"Error detecting elements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture", response_model=WebCaptureResponse)
async def capture_web_page(request: WebCaptureRequest) -> WebCaptureResponse:
    """Capture screenshot from a URL and optionally analyze it."""
    try:
        pipeline = get_screenshot_pipeline()
        
        # Capture screenshot
        metadata, analysis = await pipeline.capture_and_process(
            url=request.url,
            viewport=(request.viewport_width, request.viewport_height),
            wait_for_selector=request.wait_for_selector
        )
        
        # Get interactive elements
        interactive_elements = []
        if analysis.interactive_elements:
            interactive_elements = [e.model_dump() for e in analysis.interactive_elements]
        
        return WebCaptureResponse(
            screenshot_id=str(metadata.id),
            url=request.url,
            analysis=analysis.model_dump() if request.analyze else None,
            interactive_elements=interactive_elements
        )
    except Exception as e:
        logger.error(f"Error capturing web page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interact", response_model=InteractionResponse)
async def perform_interaction(request: InteractionRequest) -> InteractionResponse:
    """Perform a visual interaction action."""
    try:
        agent = get_visual_interaction_agent()
        
        # Initialize agent if needed
        await agent.initialize()
        
        if request.action_type == "navigate" and request.url:
            result = await agent.navigate_to(request.url)
        elif request.action_type == "click":
            # For now, require coordinates
            if not request.coordinates:
                raise HTTPException(status_code=400, detail="Coordinates required for click")
            
            from src.multimodal.vision_processor import VisualElement
            element = VisualElement(
                element_type="manual",
                bbox=[request.coordinates[0], request.coordinates[1], 
                      request.coordinates[0] + 10, request.coordinates[1] + 10],
                confidence=1.0
            )
            result = await agent.click_element(element)
        elif request.action_type == "scroll":
            direction, amount = request.text.split() if request.text else ("down", "500")
            result = await agent.scroll_page(direction, int(amount))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action type: {request.action_type}")
        
        return InteractionResponse(
            success=result.success,
            action_type=request.action_type,
            error_message=result.error_message,
            metadata=result.metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/elements/{element_type}")
async def get_elements_by_type(
    element_type: str,
    file: UploadFile = File(...)
) -> ElementDetectionResponse:
    """Get all elements of a specific type from a screenshot."""
    try:
        detector = get_element_detector()
        
        # Read uploaded file
        image_data = await file.read()
        
        # Convert to PIL Image
        from PIL import Image
        from io import BytesIO
        image = Image.open(BytesIO(image_data))
        
        # Detect all elements
        all_elements = await detector.detect_all_elements(image)
        
        # Filter by type
        matching_elements = [e for e in all_elements if e.element_type == element_type]
        
        return ElementDetectionResponse(
            elements=[e.model_dump() for e in matching_elements],
            count=len(matching_elements)
        )
    except Exception as e:
        logger.error(f"Error getting elements by type: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_resources():
    """Cleanup vision processing resources."""
    try:
        global _vision_processor, _screenshot_pipeline, _element_detector, _visual_interaction_agent
        
        if _visual_interaction_agent:
            await _visual_interaction_agent.cleanup()
            _visual_interaction_agent = None
        
        if _screenshot_pipeline:
            await _screenshot_pipeline.cleanup()
            _screenshot_pipeline = None
        
        _vision_processor = None
        _element_detector = None
        
        return {"status": "cleaned up"}
    except Exception as e:
        logger.error(f"Error cleaning up resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))
