"""Tapestry adapter - Content extraction and action planning.

Integrates Tapestry skills for:
- YouTube transcript extraction
- Article content extraction
- Ship-Learn-Next action planning

Local execution - no MCP required.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
import logging

from .base_adapter import LocalToolAdapter

log = logging.getLogger(__name__)


class TapestryAdapter(LocalToolAdapter):
    """Adapter for Tapestry productivity skills.

    Capabilities:
    - Extract YouTube transcripts
    - Extract article content
    - Generate action plans

    Usage:
        adapter = TapestryAdapter()

        # Extract YouTube transcript
        result = adapter.execute({
            "task": "youtube",
            "url": "https://youtube.com/watch?v=..."
        }, budget_tokens=2000)

        # Extract article
        result = adapter.execute({
            "task": "article",
            "url": "https://example.com/article"
        }, budget_tokens=2000)

        # Generate action plan
        result = adapter.execute({
            "task": "action_plan",
            "content": "Learning content...",
            "goal": "Build a web app"
        }, budget_tokens=2000)
    """

    @property
    def tool_name(self) -> str:
        return "tapestry"

    def _invoke_local(self, input_data: Dict, budget: int) -> Dict:
        """Execute Tapestry skill.

        Args:
            input_data: {
                "task": "youtube" | "article" | "action_plan",
                "url": str (for youtube/article),
                "content": str (for action_plan),
                "goal": str (optional for action_plan)
            }
            budget: Token budget

        Returns:
            Task-specific output dict
        """
        task = input_data.get("task", "article")
        self._track_tokens(50)  # Base overhead

        if task == "youtube":
            return self._extract_youtube(input_data, budget)
        elif task == "article":
            return self._extract_article(input_data, budget)
        elif task == "action_plan":
            return self._generate_action_plan(input_data, budget)
        else:
            return {"error": f"Unknown task: {task}", "supported": ["youtube", "article", "action_plan"]}

    def _extract_youtube(self, input_data: Dict, budget: int) -> Dict:
        """Extract YouTube transcript.

        Uses youtube-transcript-api or yt-dlp as fallback.
        """
        url = input_data.get("url", "")
        if not url:
            return {"error": "No URL provided"}

        video_id = self._extract_video_id(url)
        if not video_id:
            return {"error": f"Could not extract video ID from: {url}"}

        try:
            # Try youtube-transcript-api first
            from youtube_transcript_api import YouTubeTranscriptApi

            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

            # Combine transcript segments
            full_text = " ".join(
                segment.get("text", "") for segment in transcript_list
            )

            # Deduplicate repeated phrases
            full_text = self._deduplicate_text(full_text)

            self._track_tokens(len(full_text) // 4)

            return {
                "video_id": video_id,
                "transcript": full_text,
                "segments": len(transcript_list),
                "word_count": len(full_text.split()),
            }

        except ImportError:
            log.warning("youtube_transcript_api_not_installed")
            return {
                "error": "youtube-transcript-api not installed",
                "install": "pip install youtube-transcript-api",
                "video_id": video_id,
            }

        except Exception as e:
            log.error("youtube_extract_error", error=str(e))
            return {"error": str(e), "video_id": video_id}

    def _extract_article(self, input_data: Dict, budget: int) -> Dict:
        """Extract article content, removing ads and clutter.

        Uses readability-lxml or newspaper3k.
        """
        url = input_data.get("url", "")
        html = input_data.get("html", "")

        if not url and not html:
            return {"error": "No URL or HTML provided"}

        try:
            if url and not html:
                import requests
                response = requests.get(url, timeout=30, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; TapestryBot/1.0)"
                })
                html = response.text

            # Try readability-lxml
            try:
                from readability import Document
                doc = Document(html)
                title = doc.title()
                content = doc.summary()

                # Strip HTML tags for plain text
                content_text = re.sub(r'<[^>]+>', '', content)
                content_text = re.sub(r'\s+', ' ', content_text).strip()

            except ImportError:
                # Fallback: basic extraction
                title = self._extract_title(html)
                content_text = self._basic_extract(html)

            self._track_tokens(len(content_text) // 4)

            return {
                "url": url,
                "title": title,
                "content": content_text,
                "word_count": len(content_text.split()),
            }

        except Exception as e:
            log.error("article_extract_error", error=str(e))
            return {"error": str(e), "url": url}

    def _generate_action_plan(self, input_data: Dict, budget: int) -> Dict:
        """Generate Ship-Learn-Next action plan.

        Converts learning content into actionable implementation steps.
        """
        content = input_data.get("content", "")
        goal = input_data.get("goal", "Apply this knowledge")

        if not content:
            return {"error": "No content provided"}

        self._track_tokens(len(content) // 4)

        # Extract key concepts
        concepts = self._extract_concepts(content)

        # Generate 5-rep implementation framework
        actions = []
        for i, concept in enumerate(concepts[:5], 1):
            actions.append({
                "rep": i,
                "concept": concept,
                "action": f"Implement: {concept}",
                "deliverable": f"Working code demonstrating {concept}",
                "time_box": "25 minutes",
            })

        # Ship-Learn-Next structure
        plan = {
            "goal": goal,
            "ship": {
                "description": "What to build/deliver",
                "actions": actions[:2] if actions else [],
            },
            "learn": {
                "description": "What to understand deeper",
                "concepts": concepts[2:4] if len(concepts) > 2 else concepts,
            },
            "next": {
                "description": "What comes after",
                "actions": actions[4:] if len(actions) > 4 else [],
            },
        }

        output = {
            "plan": plan,
            "total_actions": len(actions),
            "concepts_extracted": len(concepts),
        }

        self._track_tokens(len(json.dumps(output)) // 4)
        return output

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        patterns = [
            r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'(?:embed/)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _deduplicate_text(self, text: str) -> str:
        """Remove repeated phrases from transcript."""
        words = text.split()
        result = []
        prev_window = []
        window_size = 5

        for word in words:
            current_window = prev_window + [word]
            if len(current_window) > window_size:
                current_window = current_window[-window_size:]

            # Check for repetition
            window_str = " ".join(current_window)
            if len(result) >= window_size:
                last_window = " ".join(result[-window_size:])
                if window_str == last_window:
                    continue

            result.append(word)
            prev_window = current_window

        return " ".join(result)

    def _extract_title(self, html: str) -> str:
        """Extract title from HTML."""
        match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        return match.group(1).strip() if match else "Untitled"

    def _basic_extract(self, html: str) -> str:
        """Basic content extraction without libraries."""
        # Remove script and style
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content."""
        # Simple extraction: sentences with key indicators
        sentences = re.split(r'[.!?]', content)
        concepts = []

        indicators = ['is', 'are', 'means', 'defines', 'represents', 'allows', 'enables']

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and any(ind in sentence.lower() for ind in indicators):
                # Truncate long sentences
                if len(sentence) > 100:
                    sentence = sentence[:100] + "..."
                concepts.append(sentence)

        return concepts[:10]  # Limit to 10 concepts
