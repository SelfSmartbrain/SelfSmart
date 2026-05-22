"""
SmartSelf Learning Chatbot - YouTube Crawler
Specialized crawler for extracting transcripts from YouTube videos.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
from youtube_transcript_api import YouTubeTranscriptApi
from src.crawler.web_crawler import CrawlResult

logger = logging.getLogger(__name__)

class YouTubeCrawler:
    """
    Crawler for extracting transcripts from YouTube videos.
    """
    
    def __init__(self):
        logger.info("YouTube crawler initialized")
        
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11}).*',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11}).*'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def crawl_video(self, url: str) -> Optional[CrawlResult]:
        """Extract transcript from a YouTube video URL"""
        video_id = self._extract_video_id(url)
        if not video_id:
            logger.warning(f"Could not extract video ID from URL: {url}")
            return None
            
        try:
            # Fetch transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Combine transcript parts
            text = " ".join([t['text'] for t in transcript_list])
            
            if not text.strip():
                return None
                
            return CrawlResult(
                url=url,
                title=f"YouTube Video: {video_id}",
                content=text,
                metadata={
                    'video_id': video_id,
                    'has_transcript': True,
                    'transcript_length': len(transcript_list)
                },
                timestamp=datetime.utcnow(),
                source_type='youtube',
                quality_score=0.7,
                language='en'
            )
        except Exception as e:
            logger.error(f"Error fetching YouTube transcript for {video_id}: {e}")
            return None

    async def crawl_videos_batch(self, urls: List[str]) -> List[CrawlResult]:
        """Crawl multiple YouTube videos"""
        results = []
        for url in urls:
            result = await self.crawl_video(url)
            if result:
                results.append(result)
        return results
