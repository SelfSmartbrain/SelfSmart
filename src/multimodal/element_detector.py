"""Element Detector for Multi-Modal Context (Phase 7).

Specialized detection of UI elements for web interaction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.multimodal.vision_processor import VisualElement

logger = get_logger(__name__)


class ElementDetectionConfig(BaseModel):
    """Configuration for element detection."""
    
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    merge_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    target_elements: List[str] = Field(
        default_factory=lambda: ["button", "input", "link", "select", "checkbox", "radio"]
    )


class ElementDetector:
    """Specialized detector for UI elements in screenshots."""
    
    def __init__(self, config: Optional[ElementDetectionConfig] = None):
        """Initialize element detector."""
        self.config = config or ElementDetectionConfig()
        logger.info("ElementDetector initialized")
    
    async def detect_buttons(
        self,
        image: Image.Image,
        min_confidence: float = 0.5
    ) -> List[VisualElement]:
        """Detect button elements in screenshot."""
        # Convert to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Use contour detection for button-like shapes
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        buttons = []
        for contour in contours:
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by aspect ratio and size (typical button characteristics)
            aspect_ratio = w / h if h > 0 else 0
            if 0.5 <= aspect_ratio <= 5.0 and w > 30 and h > 20:
                button = VisualElement(
                    element_type="button",
                    bbox=[x, y, x + w, y + h],
                    confidence=0.7,  # Placeholder confidence
                    attributes={
                        "width": w,
                        "height": h,
                        "aspect_ratio": aspect_ratio
                    }
                )
                buttons.append(button)
        
        logger.info(f"Detected {len(buttons)} button candidates")
        return buttons
    
    async def detect_inputs(
        self,
        image: Image.Image
    ) -> List[VisualElement]:
        """Detect input field elements in screenshot."""
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Input fields are typically rectangular with specific aspect ratios
        inputs = []
        
        # Use template matching or edge detection for input-like rectangles
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Input fields are typically wide rectangles
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio > 3.0 and w > 100 and h > 20:
                input_elem = VisualElement(
                    element_type="input",
                    bbox=[x, y, x + w, y + h],
                    confidence=0.6,
                    attributes={
                        "width": w,
                        "height": h,
                        "aspect_ratio": aspect_ratio
                    }
                )
                inputs.append(input_elem)
        
        logger.info(f"Detected {len(inputs)} input candidates")
        return inputs
    
    async def detect_links(
        self,
        image: Image.Image
    ) -> List[VisualElement]:
        """Detect link elements in screenshot."""
        # Links are typically text-based, use color analysis
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        
        # Detect blue/purple colors (typical link colors)
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        links = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if w > 20 and h > 10:
                link = VisualElement(
                    element_type="link",
                    bbox=[x, y, x + w, y + h],
                    confidence=0.5,
                    attributes={"color": "blue"}
                )
                links.append(link)
        
        logger.info(f"Detected {len(links)} link candidates")
        return links
    
    async def detect_all_elements(
        self,
        image: Image.Image
    ) -> List[VisualElement]:
        """Detect all UI elements in screenshot."""
        all_elements = []
        
        # Detect different element types
        buttons = await self.detect_buttons(image)
        inputs = await self.detect_inputs(image)
        links = await self.detect_links(image)
        
        all_elements.extend(buttons)
        all_elements.extend(inputs)
        all_elements.extend(links)
        
        # Merge overlapping elements
        merged_elements = self._merge_overlapping_elements(all_elements)
        
        # Filter by confidence
        filtered_elements = [
            elem for elem in merged_elements
            if elem.confidence >= self.config.min_confidence
        ]
        
        # Filter by target element types
        target_elements = [
            elem for elem in filtered_elements
            if elem.element_type in self.config.target_elements
        ]
        
        logger.info(f"Total elements detected: {len(target_elements)}")
        return target_elements
    
    def _merge_overlapping_elements(
        self,
        elements: List[VisualElement]
    ) -> List[VisualElement]:
        """Merge overlapping elements to avoid duplicates."""
        if not elements:
            return []
        
        # Sort by confidence (highest first)
        sorted_elements = sorted(elements, key=lambda x: x.confidence, reverse=True)
        
        merged = []
        for elem in sorted_elements:
            # Check if this element overlaps with any already merged element
            overlaps = False
            for merged_elem in merged:
                if self._calculate_overlap(elem.bbox, merged_elem.bbox) > self.config.merge_threshold:
                    overlaps = True
                    break
            
            if not overlaps:
                merged.append(elem)
        
        return merged
    
    def _calculate_overlap(self, bbox1: List[int], bbox2: List[int]) -> float:
        """Calculate IoU (Intersection over Union) between two bounding boxes."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection_area = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = area1 + area2 - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    async def get_element_at_position(
        self,
        elements: List[VisualElement],
        x: int,
        y: int
    ) -> Optional[VisualElement]:
        """Find element at specific screen coordinates."""
        for elem in elements:
            x1, y1, x2, y2 = elem.bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                return elem
        return None
    
    async def get_clickable_elements(
        self,
        elements: List[VisualElement]
    ) -> List[VisualElement]:
        """Filter elements that are clickable."""
        clickable_types = ["button", "link", "input", "select", "checkbox", "radio"]
        return [elem for elem in elements if elem.element_type in clickable_types]
