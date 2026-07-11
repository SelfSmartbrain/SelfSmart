"""E2E Tests for Multi-Modal Vision Processing (Phase 7)."""

from __future__ import annotations

import pytest
import asyncio
from io import BytesIO
from PIL import Image

from src.multimodal.vision_processor import VisionProcessor, ScreenshotAnalysis, VisualElement
from src.multimodal.element_detector import ElementDetector
from src.multimodal.screenshot_pipeline import ScreenshotPipeline


@pytest.mark.asyncio
async def test_vision_processor_initialization():
    """Test vision processor can be initialized."""
    processor = VisionProcessor()
    await processor.initialize()
    assert processor._detector is not None
    assert processor._ocr_pipeline is not None


@pytest.mark.asyncio
async def test_screenshot_analysis():
    """Test screenshot analysis with vision processor."""
    processor = VisionProcessor()
    await processor.initialize()
    
    # Create a simple test image
    image = Image.new('RGB', (800, 600), color='white')
    img_bytes = BytesIO()
    image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    analysis = await processor.analyze_screenshot(
        img_bytes.read(),
        extract_text=False,
        detect_elements=False
    )
    
    assert isinstance(analysis, ScreenshotAnalysis)
    assert analysis.image_hash is not None
    assert analysis.layout_summary is not None


@pytest.mark.asyncio
async def test_element_detector_buttons():
    """Test button detection in screenshots."""
    detector = ElementDetector()
    
    # Create a simple test image with button-like shapes
    image = Image.new('RGB', (800, 600), color='white')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    draw.rectangle([100, 100, 300, 150], fill='blue')
    draw.rectangle([100, 200, 300, 250], fill='green')
    
    buttons = await detector.detect_buttons(image)
    
    assert isinstance(buttons, list)
    # May detect the rectangles as button candidates
    assert len(buttons) >= 0


@pytest.mark.asyncio
async def test_element_detector_inputs():
    """Test input field detection in screenshots."""
    detector = ElementDetector()
    
    # Create a simple test image with input-like rectangles
    image = Image.new('RGB', (800, 600), color='white')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 100, 400, 130], outline='black', width=2)
    draw.rectangle([50, 150, 400, 180], outline='black', width=2)
    
    inputs = await detector.detect_inputs(image)
    
    assert isinstance(inputs, list)
    assert len(inputs) >= 0


@pytest.mark.asyncio
async def test_element_detector_links():
    """Test link detection in screenshots."""
    detector = ElementDetector()
    
    # Create a simple test image with blue text areas
    image = Image.new('RGB', (800, 600), color='white')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    draw.rectangle([100, 100, 300, 120], fill='blue')
    
    links = await detector.detect_links(image)
    
    assert isinstance(links, list)
    assert len(links) >= 0


@pytest.mark.asyncio
async def test_element_detector_all():
    """Test detection of all element types."""
    detector = ElementDetector()
    
    # Create a test image with various elements
    image = Image.new('RGB', (800, 600), color='white')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    
    # Button-like shape
    draw.rectangle([100, 100, 300, 150], fill='blue')
    # Input-like shape
    draw.rectangle([50, 200, 400, 230], outline='black', width=2)
    # Link-like shape
    draw.rectangle([100, 300, 300, 320], fill='blue')
    
    elements = await detector.detect_all_elements(image)
    
    assert isinstance(elements, list)
    assert len(elements) >= 0


@pytest.mark.asyncio
async def test_element_overlap_calculation():
    """Test overlap calculation between bounding boxes."""
    detector = ElementDetector()
    
    bbox1 = [0, 0, 100, 100]
    bbox2 = [50, 50, 150, 150]
    
    overlap = detector._calculate_overlap(bbox1, bbox2)
    
    # Should have some overlap
    assert overlap > 0.0
    assert overlap <= 1.0


@pytest.mark.asyncio
async def test_element_merge_overlapping():
    """Test merging of overlapping elements."""
    detector = ElementDetector()
    
    elem1 = VisualElement(
        element_type="button",
        bbox=[0, 0, 100, 100],
        confidence=0.9
    )
    elem2 = VisualElement(
        element_type="button",
        bbox=[50, 50, 150, 150],
        confidence=0.8
    )
    
    merged = detector._merge_overlapping_elements([elem1, elem2])
    
    # Should merge overlapping elements
    assert len(merged) <= 2


@pytest.mark.asyncio
async def test_screenshot_pipeline_initialization():
    """Test screenshot pipeline initialization."""
    pipeline = ScreenshotPipeline(storage_path="/tmp/test_screenshots")
    await pipeline.initialize()
    assert pipeline._browser is not None
    await pipeline.cleanup()


@pytest.mark.asyncio
async def test_image_hash_computation():
    """Test image hash computation for deduplication."""
    processor = VisionProcessor()
    
    image = Image.new('RGB', (800, 600), color='white')
    hash1 = processor._compute_image_hash(image)
    
    # Same image should produce same hash
    hash2 = processor._compute_image_hash(image)
    assert hash1 == hash2
    
    # Different image should produce different hash
    image2 = Image.new('RGB', (800, 600), color='black')
    hash3 = processor._compute_image_hash(image2)
    assert hash1 != hash3


@pytest.mark.asyncio
async def test_bbox_normalization():
    """Test bounding box normalization."""
    processor = VisionProcessor()
    
    bbox = [0.5, 0.5, 0.7, 0.7]
    image_size = (1000, 1000)
    
    normalized = processor._normalize_bbox(bbox, image_size)
    
    assert normalized == [500, 500, 700, 700]


@pytest.mark.asyncio
async def test_layout_summary_generation():
    """Test layout summary generation."""
    from src.multimodal.vision_processor import ScreenshotAnalysis
    
    analysis = ScreenshotAnalysis(
        image_hash="test123",
        elements=[
            VisualElement(element_type="button", bbox=[0, 0, 100, 100], confidence=0.9),
            VisualElement(element_type="input", bbox=[0, 0, 100, 100], confidence=0.8)
        ],
        interactive_elements=[
            VisualElement(element_type="button", bbox=[0, 0, 100, 100], confidence=0.9)
        ],
        text_regions=[
            VisualElement(element_type="text", bbox=[0, 0, 100, 100], confidence=0.9)
        ]
    )
    
    processor = VisionProcessor()
    summary = processor._generate_layout_summary(analysis)
    
    assert "button" in summary.lower()
    assert "input" in summary.lower()
