"""Visual Interaction Agent for Multi-Modal Context (Phase 7).

Agent that can autonomously interact with web applications using vision models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from playwright.async_api import async_playwright, Browser, Page

from src.config.logging import get_logger
from src.multimodal.screenshot_pipeline import ScreenshotPipeline
from src.multimodal.element_detector import ElementDetector
from src.multimodal.vision_processor import VisualElement

logger = get_logger(__name__)


class InteractionAction(BaseModel):
    """Represents a single interaction action."""
    
    action_type: str = Field(..., description="Type: click, type, select, scroll")
    element: Optional[VisualElement] = None
    coordinates: Optional[tuple[int, int]] = None
    text: Optional[str] = None
    selector: Optional[str] = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class InteractionResult(BaseModel):
    """Result of an interaction action."""
    
    success: bool
    action: InteractionAction
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VisualInteractionAgent:
    """Agent that interacts with web applications using vision."""
    
    def __init__(
        self,
        screenshot_pipeline: Optional[ScreenshotPipeline] = None,
        element_detector: Optional[ElementDetector] = None
    ):
        """Initialize visual interaction agent."""
        self.screenshot_pipeline = screenshot_pipeline or ScreenshotPipeline()
        self.element_detector = element_detector or ElementDetector()
        self._browser: Optional[Browser] = None
        self._playwright = None
        self._current_page: Optional[Page] = None
        
        logger.info("VisualInteractionAgent initialized")
    
    async def initialize(self) -> None:
        """Initialize browser and dependencies."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            await self.screenshot_pipeline.initialize()
            logger.info("VisualInteractionAgent browser initialized")
    
    async def cleanup(self) -> None:
        """Cleanup browser resources."""
        if self._current_page:
            await self._current_page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        await self.screenshot_pipeline.cleanup()
        logger.info("VisualInteractionAgent cleaned up")
    
    async def navigate_to(self, url: str) -> InteractionResult:
        """Navigate to a URL and capture initial state."""
        await self.initialize()
        
        self._current_page = await self._browser.new_page()
        
        try:
            await self._current_page.goto(url, wait_until="networkidle")
            
            # Capture screenshot
            metadata, analysis = await self.screenshot_pipeline.capture_and_process(url)
            
            return InteractionResult(
                success=True,
                action=InteractionAction(action_type="navigate", selector=url),
                screenshot_before=metadata.file_path,
                metadata={"analysis": analysis.model_dump()}
            )
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return InteractionResult(
                success=False,
                action=InteractionAction(action_type="navigate", selector=url),
                error_message=str(e)
            )
    
    async def click_element(
        self,
        element: VisualElement,
        timeout: int = 5000
    ) -> InteractionResult:
        """Click on a detected element."""
        if not self._current_page:
            raise RuntimeError("No active page. Call navigate_to first.")
        
        try:
            # Capture screenshot before
            screenshot_before = await self._current_page.screenshot()
            
            # Calculate center of element
            x1, y1, x2, y2 = element.bbox
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # Click at coordinates
            await self._current_page.mouse.click(center_x, center_y)
            
            # Wait for navigation or network idle
            try:
                await self._current_page.wait_for_load_state("networkidle", timeout=timeout)
            except:
                pass  # Some clicks don't cause navigation
            
            # Capture screenshot after
            screenshot_after = await self._current_page.screenshot()
            
            return InteractionResult(
                success=True,
                action=InteractionAction(
                    action_type="click",
                    element=element,
                    coordinates=(center_x, center_y)
                ),
                metadata={
                    "screenshot_before_size": len(screenshot_before),
                    "screenshot_after_size": len(screenshot_after)
                }
            )
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return InteractionResult(
                success=False,
                action=InteractionAction(
                    action_type="click",
                    element=element
                ),
                error_message=str(e)
            )
    
    async def type_text(
        self,
        element: VisualElement,
        text: str,
        clear_first: bool = True
    ) -> InteractionResult:
        """Type text into an input element."""
        if not self._current_page:
            raise RuntimeError("No active page. Call navigate_to first.")
        
        try:
            # Calculate center of element
            x1, y1, x2, y2 = element.bbox
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # Click to focus
            await self._current_page.mouse.click(center_x, center_y)
            
            # Clear if requested
            if clear_first:
                await self._current_page.keyboard.press("Control+A")
                await self._current_page.keyboard.press("Backspace")
            
            # Type text
            await self._current_page.keyboard.type(text)
            
            return InteractionResult(
                success=True,
                action=InteractionAction(
                    action_type="type",
                    element=element,
                    text=text
                )
            )
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return InteractionResult(
                success=False,
                action=InteractionAction(
                    action_type="type",
                    element=element,
                    text=text
                ),
                error_message=str(e)
            )
    
    async def scroll_page(
        self,
        direction: str = "down",
        amount: int = 500
    ) -> InteractionResult:
        """Scroll the page."""
        if not self._current_page:
            raise RuntimeError("No active page. Call navigate_to first.")
        
        try:
            if direction == "down":
                await self._current_page.mouse.wheel(0, amount)
            elif direction == "up":
                await self._current_page.mouse.wheel(0, -amount)
            elif direction == "right":
                await self._current_page.mouse.wheel(amount, 0)
            elif direction == "left":
                await self._current_page.mouse.wheel(-amount, 0)
            
            return InteractionResult(
                success=True,
                action=InteractionAction(
                    action_type="scroll",
                    text=f"{direction} {amount}px"
                )
            )
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return InteractionResult(
                success=False,
                action=InteractionAction(action_type="scroll"),
                error_message=str(e)
            )
    
    async def find_and_click(
        self,
        element_type: str,
        text_match: Optional[str] = None
    ) -> InteractionResult:
        """Find an element by type and optionally text, then click it."""
        if not self._current_page:
            raise RuntimeError("No active page. Call navigate_to first.")
        
        # Capture current screenshot
        screenshot_bytes = await self._current_page.screenshot()
        
        # Analyze screenshot
        from PIL import Image
        from io import BytesIO
        image = Image.open(BytesIO(screenshot_bytes))
        
        # Detect elements
        elements = await self.element_detector.detect_all_elements(image)
        
        # Filter by type
        matching_elements = [
            elem for elem in elements
            if elem.element_type == element_type
        ]
        
        # Filter by text if provided
        if text_match:
            matching_elements = [
                elem for elem in matching_elements
                if text_match.lower() in (elem.text_content or "").lower()
            ]
        
        if not matching_elements:
            return InteractionResult(
                success=False,
                action=InteractionAction(action_type="click"),
                error_message=f"No matching element found: {element_type}"
            )
        
        # Click the first matching element
        return await self.click_element(matching_elements[0])
    
    async def execute_interaction_sequence(
        self,
        actions: List[InteractionAction]
    ) -> List[InteractionResult]:
        """Execute a sequence of interaction actions."""
        results = []
        
        for action in actions:
            if action.action_type == "click" and action.element:
                result = await self.click_element(action.element)
            elif action.action_type == "type" and action.element and action.text:
                result = await self.type_text(action.element, action.text)
            elif action.action_type == "scroll":
                direction, amount = action.text.split() if action.text else ("down", "500")
                result = await self.scroll_page(direction, int(amount))
            else:
                result = InteractionResult(
                    success=False,
                    action=action,
                    error_message=f"Unknown action type: {action.action_type}"
                )
            
            results.append(result)
            
            # Stop if action failed
            if not result.success:
                logger.warning(f"Action failed, stopping sequence: {action.action_type}")
                break
        
        return results
    
    async def get_page_state(self) -> Dict[str, Any]:
        """Get current page state."""
        if not self._current_page:
            return {}
        
        screenshot_bytes = await self._current_page.screenshot()
        url = self._current_page.url
        title = await self._current_page.title()
        
        return {
            "url": url,
            "title": title,
            "screenshot_size": len(screenshot_bytes),
            "viewport": await self._current_page.viewport_size()
        }
