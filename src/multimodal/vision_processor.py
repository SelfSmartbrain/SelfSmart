"""Vision Processor for Multi-Modal Context (Phase 7).

Handles integration with vision models for screenshot analysis and visual understanding.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any, Dict, List, Optional

from PIL import Image
from pydantic import BaseModel, Field
from transformers import pipeline

from src.config.logging import get_logger

logger = get_logger(__name__)


class VisualElement(BaseModel):
    """Detected visual element in a screenshot."""
    
    element_type: str = Field(..., description="Type of element (button, input, text, etc.)")
    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    text_content: Optional[str] = Field(None, description="Extracted text if any")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional attributes")


class ScreenshotAnalysis(BaseModel):
    """Complete analysis of a screenshot."""
    
    image_hash: str
    elements: List[VisualElement] = Field(default_factory=list)
    layout_summary: str = Field(default="")
    interactive_elements: List[VisualElement] = Field(default_factory=list)
    text_regions: List[VisualElement] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VisionProcessor:
    """Processes screenshots using vision models for UI understanding."""
    
    def __init__(self, model_name: str = "microsoft/layoutlmv3-base"):
        """Initialize vision processor with specified model."""
        self.model_name = model_name
        self._detector: Optional[Any] = None
        self._ocr_pipeline: Optional[Any] = None
        logger.info(f"VisionProcessor initialized with model: {model_name}")
    
    async def initialize(self) -> None:
        """Lazy load vision models."""
        if self._detector is None:
            logger.info("Loading vision models...")
            # Initialize object detection pipeline
            self._detector = pipeline(
                "object-detection",
                model="facebook/detr-resnet-50",
                device="cpu"  # Use GPU if available
            )
            # Initialize OCR pipeline
            self._ocr_pipeline = pipeline(
                "document-question-answering",
                model="impira/layoutlm-document-qa",
                device="cpu"
            )
            logger.info("Vision models loaded successfully")
    
    async def analyze_screenshot(
        self,
        image_data: bytes,
        extract_text: bool = True,
        detect_elements: bool = True
    ) -> ScreenshotAnalysis:
        """Analyze a screenshot and extract visual information."""
        await self.initialize()
        
        # Convert bytes to PIL Image
        image = Image.open(BytesIO(image_data))
        
        # Generate image hash for deduplication
        image_hash = self._compute_image_hash(image)
        
        analysis = ScreenshotAnalysis(image_hash=image_hash)
        
        if detect_elements and self._detector:
            elements = await self._detect_elements(image)
            analysis.elements = elements
            analysis.interactive_elements = [
                e for e in elements 
                if e.element_type in ["button", "input", "link", "select"]
            ]
        
        if extract_text and self._ocr_pipeline:
            text_regions = await self._extract_text_regions(image)
            analysis.text_regions = text_regions
        
        # Generate layout summary
        analysis.layout_summary = self._generate_layout_summary(analysis)
        
        logger.info(f"Screenshot analysis complete: {len(analysis.elements)} elements detected")
        return analysis
    
    async def _detect_elements(self, image: Image.Image) -> List[VisualElement]:
        """Detect UI elements in the screenshot."""
        try:
            results = self._detector(image)
            
            elements = []
            for result in results:
                element = VisualElement(
                    element_type=result.get("label", "unknown"),
                    bbox=self._normalize_bbox(result.get("box", [0, 0, 0, 0]), image.size),
                    confidence=result.get("score", 0.0),
                    attributes={"raw_result": result}
                )
                elements.append(element)
            
            return elements
        except Exception as e:
            logger.error(f"Error detecting elements: {e}")
            return []
    
    async def _extract_text_regions(self, image: Image.Image) -> List[VisualElement]:
        """Extract text regions from the screenshot."""
        try:
            # Use OCR to extract text with bounding boxes
            results = self._ocr_pipeline(
                image,
                question="What text is visible in this image?"
            )
            
            text_regions = []
            if isinstance(results, list):
                for result in results:
                    element = VisualElement(
                        element_type="text",
                        bbox=[0, 0, 0, 0],  # LayoutLM provides bbox in result
                        confidence=0.9,
                        text_content=result.get("answer", ""),
                        attributes={"ocr_result": result}
                    )
                    text_regions.append(element)
            
            return text_regions
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return []
    
    def _compute_image_hash(self, image: Image.Image) -> str:
        """Compute a hash of the image for deduplication."""
        import hashlib
        
        # Resize to small thumbnail for hashing
        thumbnail = image.copy()
        thumbnail.thumbnail((32, 32))
        
        # Convert to bytes and hash
        img_bytes = BytesIO()
        thumbnail.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        
        return hashlib.md5(img_bytes.read()).hexdigest()
    
    def _normalize_bbox(self, bbox: List[float], image_size: tuple[int, int]) -> List[int]:
        """Normalize bounding box coordinates."""
        width, height = image_size
        return [
            int(bbox[0] * width),
            int(bbox[1] * height),
            int(bbox[2] * width),
            int(bbox[3] * height)
        ]
    
    def _generate_layout_summary(self, analysis: ScreenshotAnalysis) -> str:
        """Generate a textual summary of the layout."""
        summary_parts = []
        
        if analysis.elements:
            element_counts = {}
            for elem in analysis.elements:
                element_counts[elem.element_type] = element_counts.get(elem.element_type, 0) + 1
            
            elements_str = ", ".join([f"{count} {elem_type}" for elem_type, count in element_counts.items()])
            summary_parts.append(f"Detected: {elements_str}")
        
        if analysis.interactive_elements:
            summary_parts.append(f"Interactive elements: {len(analysis.interactive_elements)}")
        
        if analysis.text_regions:
            summary_parts.append(f"Text regions: {len(analysis.text_regions)}")
        
        return "; ".join(summary_parts) if summary_parts else "Empty screenshot"
    
    async def encode_image_base64(self, image_data: bytes) -> str:
        """Encode image data to base64 string for API transmission."""
        return base64.b64encode(image_data).decode("utf-8")
    
    async def decode_image_base64(self, base64_string: str) -> bytes:
        """Decode base64 string to image bytes."""
        return base64.b64decode(base64_string)
