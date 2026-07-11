"""Screenshot Pipeline for Multi-Modal Context (Phase 7).

Manages the end-to-end pipeline for capturing, processing, and storing screenshots.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from playwright.async_api import async_playwright, Browser, Page

from src.config.logging import get_logger
from src.multimodal.vision_processor import VisionProcessor, ScreenshotAnalysis

logger = get_logger(__name__)


class ScreenshotMetadata(BaseModel):
    """Metadata for a captured screenshot."""
    
    id: UUID = Field(default_factory=uuid4)
    url: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    viewport_size: tuple[int, int] = (1920, 1080)
    session_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    analysis_id: Optional[UUID] = None
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScreenshotPipeline:
    """Pipeline for capturing and processing screenshots."""
    
    def __init__(
        self,
        storage_path: str = "/tmp/screenshots",
        vision_processor: Optional[VisionProcessor] = None
    ):
        """Initialize screenshot pipeline."""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.vision_processor = vision_processor or VisionProcessor()
        self._browser: Optional[Browser] = None
        self._playwright = None
        
        logger.info(f"ScreenshotPipeline initialized with storage: {storage_path}")
    
    async def initialize(self) -> None:
        """Initialize browser and vision processor."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            await self.vision_processor.initialize()
            logger.info("ScreenshotPipeline browser initialized")
    
    async def cleanup(self) -> None:
        """Cleanup browser resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("ScreenshotPipeline cleaned up")
    
    async def capture_screenshot(
        self,
        url: str,
        viewport: tuple[int, int] = (1920, 1080),
        wait_for_selector: Optional[str] = None,
        session_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None
    ) -> ScreenshotMetadata:
        """Capture a screenshot of a web page."""
        await self.initialize()
        
        page = await self._browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        
        try:
            # Navigate to URL
            await page.goto(url, wait_until="networkidle")
            
            # Wait for specific element if provided
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=10000)
            
            # Capture screenshot
            screenshot_bytes = await page.screenshot(full_page=False)
            
            # Generate metadata
            metadata = ScreenshotMetadata(
                url=url,
                viewport_size=viewport,
                session_id=session_id,
                task_id=task_id
            )
            
            # Save screenshot to disk
            file_path = self.storage_path / f"{metadata.id}.png"
            file_path.write_bytes(screenshot_bytes)
            metadata.file_path = str(file_path)
            
            logger.info(f"Screenshot captured: {metadata.id} from {url}")
            return metadata
            
        finally:
            await page.close()
    
    async def capture_screenshot_batch(
        self,
        urls: List[str],
        viewport: tuple[int, int] = (1920, 1080),
        session_id: Optional[UUID] = None
    ) -> List[ScreenshotMetadata]:
        """Capture screenshots from multiple URLs in parallel."""
        tasks = [
            self.capture_screenshot(url, viewport, session_id=session_id)
            for url in urls
        ]
        return await asyncio.gather(*tasks)
    
    async def process_screenshot(
        self,
        metadata: ScreenshotMetadata,
        extract_text: bool = True,
        detect_elements: bool = True
    ) -> tuple[ScreenshotMetadata, ScreenshotAnalysis]:
        """Process a captured screenshot with vision analysis."""
        if not metadata.file_path or not Path(metadata.file_path).exists():
            raise ValueError(f"Screenshot file not found: {metadata.file_path}")
        
        # Read screenshot bytes
        image_data = Path(metadata.file_path).read_bytes()
        
        # Analyze with vision processor
        analysis = await self.vision_processor.analyze_screenshot(
            image_data,
            extract_text=extract_text,
            detect_elements=detect_elements
        )
        
        # Link analysis to metadata
        metadata.analysis_id = uuid4()
        metadata.metadata["analysis"] = analysis.model_dump()
        
        logger.info(f"Screenshot processed: {metadata.id}")
        return metadata, analysis
    
    async def capture_and_process(
        self,
        url: str,
        viewport: tuple[int, int] = (1920, 1080),
        wait_for_selector: Optional[str] = None,
        session_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None
    ) -> tuple[ScreenshotMetadata, ScreenshotAnalysis]:
        """Capture and process a screenshot in one operation."""
        metadata = await self.capture_screenshot(
            url, viewport, wait_for_selector, session_id, task_id
        )
        return await self.process_screenshot(metadata)
    
    async def get_interactive_elements(
        self,
        url: str,
        viewport: tuple[int, int] = (1920, 1080)
    ) -> List[Dict[str, Any]]:
        """Get interactive elements from a web page."""
        _, analysis = await self.capture_and_process(url, viewport)
        
        interactive_elements = []
        for elem in analysis.interactive_elements:
            interactive_elements.append({
                "type": elem.element_type,
                "bbox": elem.bbox,
                "confidence": elem.confidence,
                "text": elem.text_content
            })
        
        return interactive_elements
    
    async def compare_screenshots(
        self,
        screenshot1: ScreenshotMetadata,
        screenshot2: ScreenshotMetadata
    ) -> Dict[str, Any]:
        """Compare two screenshots for visual differences."""
        analysis1 = await self.process_screenshot(screenshot1)
        analysis2 = await self.process_screenshot(screenshot2)
        
        return {
            "hash_match": analysis1[0].image_hash == analysis2[0].image_hash,
            "element_count_diff": len(analysis1[1].elements) - len(analysis2[1].elements),
            "interactive_diff": len(analysis1[1].interactive_elements) - len(analysis2[1].interactive_elements),
            "text_region_diff": len(analysis1[1].text_regions) - len(analysis2[1].text_regions)
        }
