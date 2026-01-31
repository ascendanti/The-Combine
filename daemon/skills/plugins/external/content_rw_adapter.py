"""Content Research Writer adapter.

Collaborative writing assistant with:
- Research assistance
- Citation management
- Hook improvement
- Section feedback
- Voice preservation
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional
import logging

from .base_adapter import LocalToolAdapter

log = logging.getLogger(__name__)


class ContentResearchWriterAdapter(LocalToolAdapter):
    """Adapter for Content Research Writer skill.

    Capabilities:
    - Collaborative outlining
    - Research with citations
    - Hook improvement
    - Section feedback
    - Voice matching

    Usage:
        adapter = ContentResearchWriterAdapter()

        # Generate outline
        result = adapter.execute({
            "task": "outline",
            "topic": "AI in Education",
            "audience": "educators",
            "length": "medium"
        }, budget_tokens=2000)

        # Improve hook
        result = adapter.execute({
            "task": "improve_hook",
            "content": "AI is changing education...",
            "style": "provocative"
        }, budget_tokens=1000)

        # Section feedback
        result = adapter.execute({
            "task": "feedback",
            "section": "...",
            "criteria": ["clarity", "flow", "evidence"]
        }, budget_tokens=1500)
    """

    @property
    def tool_name(self) -> str:
        return "content-research-writer"

    def _invoke_local(self, input_data: Dict, budget: int) -> Dict:
        """Execute Content RW task.

        Args:
            input_data: Task-specific input
            budget: Token budget

        Returns:
            Task-specific output
        """
        task = input_data.get("task", "outline")
        self._track_tokens(50)

        if task == "outline":
            return self._generate_outline(input_data, budget)
        elif task == "improve_hook":
            return self._improve_hook(input_data, budget)
        elif task == "feedback":
            return self._section_feedback(input_data, budget)
        elif task == "citations":
            return self._manage_citations(input_data, budget)
        elif task == "voice_match":
            return self._match_voice(input_data, budget)
        else:
            return {"error": f"Unknown task: {task}"}

    def _generate_outline(self, input_data: Dict, budget: int) -> Dict:
        """Generate content outline."""
        topic = input_data.get("topic", "")
        audience = input_data.get("audience", "general")
        length = input_data.get("length", "medium")
        goals = input_data.get("goals", [])

        if not topic:
            return {"error": "No topic provided"}

        self._track_tokens(len(topic) // 4)

        # Determine section count by length
        section_counts = {"short": 3, "medium": 5, "long": 8}
        num_sections = section_counts.get(length, 5)

        # Generate structure
        outline = {
            "title": f"Guide: {topic}",
            "audience": audience,
            "sections": [],
            "research_needed": [],
        }

        # Common section patterns
        section_templates = [
            ("Introduction", "Hook and context for {topic}"),
            ("Background", "Essential background on {topic}"),
            ("Core Concepts", "Main ideas and principles"),
            ("Implementation", "How to apply {topic}"),
            ("Case Studies", "Real-world examples"),
            ("Best Practices", "Recommendations and tips"),
            ("Common Pitfalls", "What to avoid"),
            ("Future Outlook", "Where {topic} is heading"),
            ("Conclusion", "Summary and call to action"),
        ]

        # Select appropriate sections
        selected = []
        selected.append(section_templates[0])  # Always intro
        selected.extend(section_templates[1:num_sections - 1])
        selected.append(section_templates[-1])  # Always conclusion

        for title, desc in selected[:num_sections]:
            outline["sections"].append({
                "title": title,
                "description": desc.format(topic=topic),
                "estimated_words": 300 if length == "short" else 500,
                "subsections": [],
            })

        # Identify research gaps
        outline["research_needed"] = [
            f"Statistics on {topic}",
            f"Expert quotes about {topic}",
            f"Recent developments in {topic}",
        ]

        self._track_tokens(len(json.dumps(outline)) // 4)
        return outline

    def _improve_hook(self, input_data: Dict, budget: int) -> Dict:
        """Generate alternative hooks for content."""
        content = input_data.get("content", "")
        style = input_data.get("style", "engaging")
        count = input_data.get("count", 3)

        if not content:
            return {"error": "No content provided"}

        self._track_tokens(len(content) // 4)

        # Extract key topic from content
        words = content.split()[:20]
        topic_hint = " ".join(words)

        # Generate hook alternatives
        hooks = []
        hook_templates = {
            "provocative": [
                "What if everything you knew about {topic} was wrong?",
                "The uncomfortable truth about {topic} that no one talks about.",
                "Why {topic} will define the next decade.",
            ],
            "question": [
                "Have you ever wondered why {topic} matters?",
                "What makes {topic} so crucial in today's world?",
                "How would your life change if you mastered {topic}?",
            ],
            "statistic": [
                "87% of professionals say {topic} is their top priority.",
                "In the last year alone, {topic} has grown by 200%.",
                "Studies show that understanding {topic} can improve outcomes by 45%.",
            ],
            "story": [
                "When I first encountered {topic}, I had no idea it would change everything.",
                "Picture this: a world transformed by {topic}.",
                "The moment I understood {topic}, my perspective shifted entirely.",
            ],
            "engaging": [
                "Let's talk about {topic} — but not in the way you'd expect.",
                "Here's what makes {topic} fascinating.",
                "The secret to mastering {topic} might surprise you.",
            ],
        }

        templates = hook_templates.get(style, hook_templates["engaging"])
        for template in templates[:count]:
            hooks.append({
                "hook": template.format(topic=topic_hint[:30]),
                "style": style,
                "word_count": len(template.split()),
            })

        output = {
            "original_start": content[:100] + "..." if len(content) > 100 else content,
            "alternatives": hooks,
            "recommendation": hooks[0] if hooks else None,
        }

        self._track_tokens(len(json.dumps(output)) // 4)
        return output

    def _section_feedback(self, input_data: Dict, budget: int) -> Dict:
        """Provide feedback on a content section."""
        section = input_data.get("section", "")
        criteria = input_data.get("criteria", ["clarity", "flow", "evidence"])

        if not section:
            return {"error": "No section provided"}

        self._track_tokens(len(section) // 4)

        feedback = {
            "overall_score": 0.0,
            "criteria_scores": {},
            "suggestions": [],
            "strengths": [],
        }

        # Analyze each criterion
        for criterion in criteria:
            score, notes = self._analyze_criterion(section, criterion)
            feedback["criteria_scores"][criterion] = {
                "score": score,
                "notes": notes,
            }

        # Calculate overall score
        scores = [c["score"] for c in feedback["criteria_scores"].values()]
        feedback["overall_score"] = sum(scores) / len(scores) if scores else 0.0

        # Generate suggestions
        if feedback["overall_score"] < 0.7:
            feedback["suggestions"].append("Consider adding more specific examples.")
        if len(section.split()) < 100:
            feedback["suggestions"].append("Section may be too brief. Consider expanding key points.")
        if not re.search(r'\d+', section):
            feedback["suggestions"].append("Adding statistics or data could strengthen arguments.")

        # Identify strengths
        if re.search(r'"[^"]+"', section):
            feedback["strengths"].append("Good use of quotes.")
        if len(section.split('.')) > 5:
            feedback["strengths"].append("Well-structured with multiple points.")

        self._track_tokens(len(json.dumps(feedback)) // 4)
        return feedback

    def _manage_citations(self, input_data: Dict, budget: int) -> Dict:
        """Manage citations in content."""
        content = input_data.get("content", "")
        sources = input_data.get("sources", [])
        style = input_data.get("style", "inline")  # inline, numbered, footnotes

        if not content:
            return {"error": "No content provided"}

        self._track_tokens(len(content) // 4)

        # Find citation markers
        citation_pattern = r'\[(\d+)\]|\(([^)]+,\s*\d{4})\)'
        matches = re.findall(citation_pattern, content)

        citations_found = []
        for match in matches:
            citation = match[0] or match[1]
            citations_found.append(citation)

        # Format bibliography
        bibliography = []
        for i, source in enumerate(sources, 1):
            if style == "numbered":
                bibliography.append(f"[{i}] {source}")
            elif style == "footnotes":
                bibliography.append(f"^{i}. {source}")
            else:
                bibliography.append(source)

        output = {
            "citations_found": citations_found,
            "citation_count": len(citations_found),
            "bibliography": bibliography,
            "style": style,
            "needs_sources": len(citations_found) > len(sources),
        }

        self._track_tokens(len(json.dumps(output)) // 4)
        return output

    def _match_voice(self, input_data: Dict, budget: int) -> Dict:
        """Analyze and match writing voice."""
        sample = input_data.get("sample", "")
        target = input_data.get("target", "")

        if not sample:
            return {"error": "No sample provided"}

        self._track_tokens(len(sample) // 4)

        # Analyze voice characteristics
        voice_profile = {
            "formality": self._measure_formality(sample),
            "sentence_length": self._avg_sentence_length(sample),
            "vocabulary_complexity": self._vocabulary_complexity(sample),
            "tone_markers": self._detect_tone_markers(sample),
        }

        output = {
            "voice_profile": voice_profile,
            "style_guide": self._generate_style_guide(voice_profile),
        }

        if target:
            self._track_tokens(len(target) // 4)
            output["adaptation_suggestions"] = self._suggest_adaptations(
                target, voice_profile
            )

        self._track_tokens(len(json.dumps(output)) // 4)
        return output

    def _analyze_criterion(self, text: str, criterion: str) -> tuple:
        """Analyze text against a criterion."""
        if criterion == "clarity":
            # Check sentence length, jargon
            avg_len = self._avg_sentence_length(text)
            score = 1.0 if avg_len < 20 else 0.8 if avg_len < 30 else 0.6
            notes = f"Average sentence length: {avg_len:.0f} words"
        elif criterion == "flow":
            # Check transitions
            transitions = len(re.findall(r'\b(however|therefore|moreover|furthermore|consequently)\b', text.lower()))
            score = min(1.0, 0.5 + transitions * 0.1)
            notes = f"Found {transitions} transition words"
        elif criterion == "evidence":
            # Check for data, quotes, citations
            has_data = bool(re.search(r'\d+%|\d+ percent', text))
            has_quotes = bool(re.search(r'"[^"]+"', text))
            has_citations = bool(re.search(r'\[\d+\]|\([^)]+,\s*\d{4}\)', text))
            score = (0.33 if has_data else 0) + (0.33 if has_quotes else 0) + (0.34 if has_citations else 0)
            notes = f"Data: {has_data}, Quotes: {has_quotes}, Citations: {has_citations}"
        else:
            score = 0.7
            notes = "Generic assessment"

        return round(score, 2), notes

    def _measure_formality(self, text: str) -> str:
        """Measure formality level."""
        informal_markers = len(re.findall(r"\b(gonna|wanna|kinda|you're|I'm|don't)\b", text.lower()))
        formal_markers = len(re.findall(r"\b(therefore|consequently|furthermore|hereby)\b", text.lower()))

        if formal_markers > informal_markers * 2:
            return "formal"
        elif informal_markers > formal_markers * 2:
            return "casual"
        return "neutral"

    def _avg_sentence_length(self, text: str) -> float:
        """Calculate average sentence length."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0
        return sum(len(s.split()) for s in sentences) / len(sentences)

    def _vocabulary_complexity(self, text: str) -> str:
        """Assess vocabulary complexity."""
        words = text.lower().split()
        long_words = sum(1 for w in words if len(w) > 8)
        ratio = long_words / len(words) if words else 0

        if ratio > 0.2:
            return "advanced"
        elif ratio > 0.1:
            return "intermediate"
        return "accessible"

    def _detect_tone_markers(self, text: str) -> List[str]:
        """Detect tone markers."""
        markers = []
        if re.search(r'!', text):
            markers.append("enthusiastic")
        if re.search(r'\?', text):
            markers.append("inquisitive")
        if re.search(r'\b(I|we|you)\b', text.lower()):
            markers.append("personal")
        if re.search(r'\b(must|should|need to)\b', text.lower()):
            markers.append("directive")
        return markers

    def _generate_style_guide(self, profile: Dict) -> Dict:
        """Generate style guide from voice profile."""
        return {
            "sentence_target": f"Aim for {profile['sentence_length']:.0f} words per sentence",
            "formality": f"Maintain {profile['formality']} tone",
            "vocabulary": f"Use {profile['vocabulary_complexity']} vocabulary",
            "tone": f"Incorporate {', '.join(profile['tone_markers'])} elements" if profile['tone_markers'] else "Neutral tone",
        }

    def _suggest_adaptations(self, target: str, profile: Dict) -> List[str]:
        """Suggest how to adapt target text to match voice profile."""
        suggestions = []
        target_len = self._avg_sentence_length(target)

        if abs(target_len - profile['sentence_length']) > 5:
            if target_len > profile['sentence_length']:
                suggestions.append("Break longer sentences into shorter ones")
            else:
                suggestions.append("Combine short sentences for better flow")

        target_formality = self._measure_formality(target)
        if target_formality != profile['formality']:
            suggestions.append(f"Adjust formality from {target_formality} to {profile['formality']}")

        return suggestions
