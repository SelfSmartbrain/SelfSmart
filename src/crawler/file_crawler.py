"""
SmartSelf Learning Chatbot - File Crawler
Specialized crawler for local files (PDF, Markdown, Text).
"""

import os
import logging
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from pypdf import PdfReader
from src.crawler.web_crawler import CrawlResult

logger = logging.getLogger(__name__)


class FileCrawler:
    """
    Crawler for local files including PDFs, Markdown, and Text files.
    """

    def __init__(self):
        logger.info("File crawler initialized")

    async def crawl_directory(self, directory_path: str) -> List[CrawlResult]:
        """Crawl all supported files in a directory"""
        results = []
        path = Path(directory_path)

        if not path.exists():
            logger.error(f"Directory not found: {directory_path}")
            return []

        for file_path in path.glob("**/*"):
            if file_path.is_file():
                result = await self.crawl_file(str(file_path))
                if result:
                    results.append(result)

        return results

    async def crawl_file(self, file_path: str) -> Optional[CrawlResult]:
        """Crawl a single file based on its extension"""
        try:
            path = Path(file_path)
            ext = path.suffix.lower()

            if ext == ".pdf":
                return self._process_pdf(path)
            elif ext in [".md", ".txt", ".markdown"]:
                return self._process_text(path)
            else:
                logger.debug(f"Skipping unsupported file type: {ext}")
                return None

        except Exception as e:
            logger.error(f"Error crawling file {file_path}: {e}")
            return None

    def _process_pdf(self, path: Path) -> Optional[CrawlResult]:
        """Extract text from a PDF file"""
        try:
            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"

            if not text.strip():
                return None

            return CrawlResult(
                url=f"file://{path.absolute()}",
                title=path.name,
                content=text,
                metadata={
                    "file_path": str(path.absolute()),
                    "file_size": path.stat().st_size,
                    "file_type": "pdf",
                    "page_count": len(reader.pages),
                },
                timestamp=datetime.utcnow(),
                source_type="file",
                quality_score=0.8,
                language="en",
            )
        except Exception as e:
            logger.error(f"Error processing PDF {path}: {e}")
            return None

    def _process_text(self, path: Path) -> Optional[CrawlResult]:
        """Read content from text or markdown file"""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if not content.strip():
                return None

            return CrawlResult(
                url=f"file://{path.absolute()}",
                title=path.name,
                content=content,
                metadata={
                    "file_path": str(path.absolute()),
                    "file_size": path.stat().st_size,
                    "file_type": path.suffix.lower().replace(".", ""),
                },
                timestamp=datetime.utcnow(),
                source_type="file",
                quality_score=0.9,
                language="en",
            )
        except Exception as e:
            logger.error(f"Error processing text file {path}: {e}")
            return None
