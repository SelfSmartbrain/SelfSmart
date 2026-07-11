"""
Data Collector - Gather training data from the internet
Production-grade data collection for LLM fine-tuning.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import hashlib
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Production-grade data collector for internet data.
    Supports web crawling, API integration, and dataset downloading.
    """

    def __init__(
        self,
        output_dir: str = "./training_data",
        max_concurrent_requests: int = 10,
        delay_between_requests: float = 1.0
    ):
        """
        Initialize data collector.

        Args:
            output_dir: Directory to store collected data
            max_concurrent_requests: Max concurrent HTTP requests
            delay_between_requests: Delay between requests (seconds)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.max_concurrent_requests = max_concurrent_requests
        self.delay_between_requests = delay_between_requests
        self.session: Optional[aiohttp.ClientSession] = None

        # Data sources configuration
        self.sources = {
            "wikipedia": {
                "base_url": "https://en.wikipedia.org/api/rest_v1",
                "enabled": True
            },
            "hacker_news": {
                "base_url": "https://hacker-news.firebaseio.com/v0",
                "enabled": True
            },
            "reddit": {
                "base_url": "https://www.reddit.com",
                "enabled": False  # Requires API key
            }
        }

        logger.info(f"Data collector initialized with output directory: {self.output_dir}")

    def sanitize_content(self, content: str, min_length: int = 50, max_length: int = 10000) -> Optional[str]:
        """
        Sanitize content by removing HTML artifacts, excessive whitespace, and low-quality content.
        Also removes script tags and suspicious instruction-like phrases, and caps length.

        Args:
            content: Raw content to sanitize
            min_length: Minimum content length after sanitization
            max_length: Maximum content length after sanitization (truncates if exceeded)

        Returns:
            Sanitized content or None if content is too short/invalid
        """
        if not content or not isinstance(content, str):
            return None

        # Remove script tags and their content
        # Regex to match <script> tags and everything between them until </script>
        content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', ' ', content, flags=re.IGNORECASE)
        # Also remove any standalone opening or closing script tags (in case of malformed)
        content = re.sub(r'</?script\b[^>]*>', ' ', content, flags=re.IGNORECASE)

        # Remove suspicious instruction-like phrases (case-insensitive)
        suspicious_patterns = [
            r'ignore\s+previous\s+instructions',
            r'you\s+are\s+now',
            r'disregard\s+above',
            r'forget\s+everything\s+before',
            r'this\s+overrides\s+previous',
            r'new\s+instructions:',
            # Add more patterns as needed
        ]
        for pattern in suspicious_patterns:
            content = re.sub(pattern, ' ', content, flags=re.IGNORECASE)

        # Remove HTML tags (any remaining)
        content = re.sub(r'<[^>]+>', ' ', content)

        # Remove common HTML entities
        content = re.sub(r'&[a-zA-Z]+;', ' ', content)

        # Remove URLs
        content = re.sub(r'https?://\S+', ' ', content)

        # Remove email addresses
        content = re.sub(r'\S+@\S+', ' ', content)

        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)

        # Remove leading/trailing whitespace
        content = content.strip()

        # Truncate to max_length if still too long
        if len(content) > max_length:
            content = content[:max_length]
            # Try to cut at a space to avoid cutting words in half
            last_space = content.rfind(' ')
            if last_space > max_length * 0.8:  # Only if we don't lose too much
                content = content[:last_space]

        # Filter out very short content
        if len(content) < min_length:
            return None

        # Filter out content with too many special characters (potential spam)
        special_char_ratio = sum(1 for c in content if not c.isalnum() and not c.isspace()) / max(len(content), 1)
        if special_char_ratio > 0.5:
            return None

        return content

    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent_requests,
            ttl_dns_cache=300,
            use_dns_cache=True,
            force_close=False,
            enable_cleanup_closed=True
        )

        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'SmartSelf-AI-DataCollector/1.0'
            },
            trust_env=False
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_wikipedia_articles(
        self,
        count: int = 100,
        categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch Wikipedia articles for training data.

        Args:
            count: Number of articles to fetch
            categories: Specific categories to fetch

        Returns:
            List of article data
        """
        if not self.sources["wikipedia"]["enabled"]:
            logger.warning("Wikipedia source is disabled")
            return []

        logger.info(f"Fetching {count} Wikipedia articles")

        articles = []

        try:
            # Fetch random articles
            for _ in range(count):
                await asyncio.sleep(self.delay_between_requests)

                try:
                    async with self.session.get(
                        f"{self.sources['wikipedia']['base_url']}/page/random/summary"
                    ) as response:
                        if response.status == 200:
                            article = await response.json()

                            # Extract and sanitize content
                            raw_content = article.get("extract", "")
                            sanitized_content = self.sanitize_content(raw_content)

                            if sanitized_content:
                                article_data = {
                                    "source": "wikipedia",
                                    "title": article.get("title", ""),
                                    "content": sanitized_content,
                                    "url": article.get("content_urls", {}).get("desktop", {}).get("page", ""),
                                    "timestamp": datetime.now().isoformat(),
                                    "categories": article.get("categories", [])
                                }

                                articles.append(article_data)
                            else:
                                logger.debug(f"Skipped Wikipedia article due to sanitization: {article.get('title', '')}")

                except Exception as e:
                    logger.error(f"Error fetching Wikipedia article: {e}")
                    continue

            logger.info(f"Successfully fetched {len(articles)} Wikipedia articles")
            return articles

        except Exception as e:
            logger.error(f"Error in Wikipedia fetching: {e}")
            return []

    async def fetch_hacker_news_stories(
        self,
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch Hacker News stories for training data.

        Args:
            count: Number of stories to fetch

        Returns:
            List of story data
        """
        if not self.sources["hacker_news"]["enabled"]:
            logger.warning("Hacker News source is disabled")
            return []

        logger.info(f"Fetching {count} Hacker News stories")

        stories = []

        try:
            # Get top story IDs
            async with self.session.get(
                f"{self.sources['hacker_news']['base_url']}/topstories.json"
            ) as response:
                if response.status == 200:
                    story_ids = await response.json()
                    story_ids = story_ids[:count]

                    # Fetch story details
                    for story_id in story_ids:
                        await asyncio.sleep(self.delay_between_requests)

                        try:
                            async with self.session.get(
                                f"{self.sources['hacker_news']['base_url']}/item/{story_id}.json"
                            ) as story_response:
                                if story_response.status == 200:
                                    story = await story_response.json()

                                    # Extract and sanitize content
                                    raw_content = story.get("text", story.get("title", ""))
                                    sanitized_content = self.sanitize_content(raw_content)

                                    if sanitized_content:
                                        story_data = {
                                            "source": "hacker_news",
                                            "title": story.get("title", ""),
                                            "content": sanitized_content,
                                            "url": story.get("url", ""),
                                            "timestamp": datetime.now().isoformat(),
                                            "score": story.get("score", 0),
                                            "comments": story.get("descendants", 0)
                                        }

                                        stories.append(story_data)
                                    else:
                                        logger.debug(f"Skipped HN story due to sanitization: {story.get('title', '')}")

                        except Exception as e:
                            logger.error(f"Error fetching story {story_id}: {e}")
                            continue

            logger.info(f"Successfully fetched {len(stories)} Hacker News stories")
            return stories

        except Exception as e:
            logger.error(f"Error in Hacker News fetching: {e}")
            return []

    async def crawl_url(
        self,
        url: str,
        max_depth: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Crawl a single URL and extract content.

        Args:
            url: URL to crawl
            max_depth: Maximum crawl depth

        Returns:
            Extracted content or None
        """
        try:
            await asyncio.sleep(self.delay_between_requests)

            async with self.session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Extract text
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)

                # Extract metadata
                title = soup.find('title')
                title_text = title.get_text() if title else ""

                # Sanitize content
                sanitized_content = self.sanitize_content(text[:10000])

                if sanitized_content:
                    return {
                        "source": "web_crawl",
                        "title": title_text,
                        "content": sanitized_content,
                        "url": url,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.debug(f"Skipped web crawl due to sanitization: {url}")
                    return None

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return None

    async def collect_from_urls(
        self,
        urls: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Collect data from a list of URLs.

        Args:
            urls: List of URLs to crawl

        Returns:
            List of collected data
        """
        logger.info(f"Crawling {len(urls)} URLs")

        tasks = [self.crawl_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = []
        for result in results:
            if isinstance(result, dict):
                data.append(result)

        logger.info(f"Successfully crawled {len(data)} URLs")
        return data

    def save_data(
        self,
        data: List[Dict[str, Any]],
        filename: str
    ):
        """
        Save collected data to file.

        Args:
            data: Data to save
            filename: Output filename
        """
        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(data)} items to {output_path}")

    def load_data(self, filename: str) -> List[Dict[str, Any]]:
        """
        Load data from file.

        Args:
            filename: Input filename

        Returns:
            Loaded data
        """
        input_path = self.output_dir / filename

        if not input_path.exists():
            logger.warning(f"File not found: {input_path}")
            return []

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Loaded {len(data)} items from {input_path}")
        return data

    async def collect_all(
        self,
        wikipedia_count: int = 50,
        hacker_news_count: int = 50,
        urls: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect data from all enabled sources.

        Args:
            wikipedia_count: Number of Wikipedia articles
            hacker_news_count: Number of Hacker News stories
            urls: List of URLs to crawl

        Returns:
            Dictionary of collected data by source
        """
        all_data = {}

        # Collect from Wikipedia
        if self.sources["wikipedia"]["enabled"]:
            wikipedia_data = await self.fetch_wikipedia_articles(wikipedia_count)
            all_data["wikipedia"] = wikipedia_data
            self.save_data(wikipedia_data, "wikipedia_data.json")

        # Collect from Hacker News
        if self.sources["hacker_news"]["enabled"]:
            hn_data = await self.fetch_hacker_news_stories(hacker_news_count)
            all_data["hacker_news"] = hn_data
            self.save_data(hn_data, "hacker_news_data.json")

        # Collect from URLs
        if urls:
            crawl_data = await self.collect_from_urls(urls)
            all_data["web_crawl"] = crawl_data
            self.save_data(crawl_data, "web_crawl_data.json")

        total_items = sum(len(data) for data in all_data.values())
        logger.info(f"Collected total of {total_items} items from all sources")

        return all_data
