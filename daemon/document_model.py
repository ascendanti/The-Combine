"""
Document Model - Hierarchical document representation with stable IDs.

Part of UTF v2 architecture. Provides addressable spans for:
- True provenance (claim → span → page)
- Stable cache keys
- Deduplication at paragraph/span level
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class Span:
    """Addressable text span with stable ID."""
    span_id: str
    section_path: str      # e.g., "introduction/contributions"
    page: int
    start_char: int
    end_char: int
    text: str
    span_hash: str         # Content hash for caching
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, text: str, section_path: str, page: int = 0,
               start_char: int = 0, end_char: int = 0) -> 'Span':
        """Create span with computed hashes."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        span_id = hashlib.sha256(
            f"{section_path}:{page}:{start_char}:{content_hash}".encode()
        ).hexdigest()[:12]

        return cls(
            span_id=span_id,
            section_path=section_path,
            page=page,
            start_char=start_char,
            end_char=end_char or start_char + len(text),
            text=text,
            span_hash=content_hash
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'span_id': self.span_id,
            'section_path': self.section_path,
            'page': self.page,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'text': self.text[:200] + '...' if len(self.text) > 200 else self.text,
            'span_hash': self.span_hash,
            'char_count': len(self.text)
        }


@dataclass
class Section:
    """Document section with heading hierarchy."""
    heading: str
    level: int             # 1=chapter, 2=section, 3=subsection
    path: str              # Normalized path like "introduction/contributions"
    spans: List[Span] = field(default_factory=list)
    children: List['Section'] = field(default_factory=list)
    page_start: int = 0
    page_end: int = 0

    def all_spans(self) -> List[Span]:
        """Get all spans including from children."""
        result = list(self.spans)
        for child in self.children:
            result.extend(child.all_spans())
        return result

    def find_section(self, pattern: str) -> Optional['Section']:
        """Find section by heading pattern (regex)."""
        if re.search(pattern, self.heading, re.IGNORECASE):
            return self
        for child in self.children:
            found = child.find_section(pattern)
            if found:
                return found
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'heading': self.heading,
            'level': self.level,
            'path': self.path,
            'span_count': len(self.spans),
            'char_count': sum(len(s.text) for s in self.spans),
            'children': [c.to_dict() for c in self.children]
        }


@dataclass
class DocumentModel:
    """Full document representation with hierarchical structure."""
    source_id: str
    title: str
    filename: str
    sections: List[Section] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    total_chars: int = 0

    @classmethod
    def from_text(cls, text: str, filename: str, title: str = None) -> 'DocumentModel':
        """Parse text into structured document model."""
        source_id = hashlib.sha256(text.encode()).hexdigest()[:16]

        doc = cls(
            source_id=source_id,
            title=title or Path(filename).stem,
            filename=filename,
            raw_text=text,
            total_chars=len(text)
        )

        doc.sections = parse_sections(text)
        return doc

    def get_span(self, span_id: str) -> Optional[Span]:
        """Find span by ID."""
        for section in self.sections:
            for span in section.all_spans():
                if span.span_id == span_id:
                    return span
        return None

    def find_sections(self, pattern: str) -> List[Section]:
        """Find all sections matching pattern."""
        results = []
        for section in self.sections:
            found = section.find_section(pattern)
            if found:
                results.append(found)
        return results

    def high_signal_spans(self) -> List[Span]:
        """Get spans from high-signal sections (for extraction)."""
        from span_selector import select_spans
        return select_spans(self)

    def all_spans(self) -> List[Span]:
        """Get all spans in document."""
        result = []
        for section in self.sections:
            result.extend(section.all_spans())
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'title': self.title,
            'filename': self.filename,
            'total_chars': self.total_chars,
            'section_count': len(self.sections),
            'span_count': len(self.all_spans()),
            'sections': [s.to_dict() for s in self.sections]
        }


# ============================================================================
# Section Parsing
# ============================================================================

# Heading patterns for academic papers
HEADING_PATTERNS = [
    # Markdown style
    (r'^#{1,6}\s+(.+)$', lambda m: len(m.group(0).split()[0])),
    # Numbered sections: "1. Introduction", "2.1 Methods"
    (r'^(\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', lambda m: m.group(1).count('.') + 1),
    # ALL CAPS headings
    (r'^([A-Z][A-Z\s]{3,50})$', lambda m: 1),
    # Title case with colon
    (r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):?\s*$', lambda m: 2),
]

# Section name normalization
SECTION_ALIASES = {
    'abstract': ['abstract', 'summary', 'executive summary'],
    'introduction': ['introduction', 'intro', 'background', 'overview'],
    'methods': ['methods', 'methodology', 'approach', 'materials and methods'],
    'results': ['results', 'findings', 'experiments', 'evaluation'],
    'discussion': ['discussion', 'analysis'],
    'conclusion': ['conclusion', 'conclusions', 'summary', 'final remarks'],
    'limitations': ['limitations', 'threats to validity', 'constraints'],
    'future_work': ['future work', 'future directions'],
    'references': ['references', 'bibliography', 'citations'],
}


def normalize_heading(heading: str) -> str:
    """Normalize heading to canonical path component."""
    heading_lower = heading.lower().strip()

    for canonical, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if alias in heading_lower:
                return canonical

    # Default: kebab-case the heading
    return re.sub(r'[^a-z0-9]+', '_', heading_lower).strip('_')


def parse_sections(text: str) -> List[Section]:
    """Parse text into section hierarchy."""
    lines = text.split('\n')
    sections = []
    current_section = None
    current_text = []
    section_stack = []  # For nesting

    def flush_text():
        """Convert accumulated text to span."""
        nonlocal current_text
        if current_section and current_text:
            combined = '\n'.join(current_text).strip()
            if combined:
                span = Span.create(
                    text=combined,
                    section_path=current_section.path,
                    page=0,  # Would need PDF metadata for real page
                    start_char=0
                )
                current_section.spans.append(span)
        current_text = []

    for i, line in enumerate(lines):
        heading_match = None
        level = 0

        for pattern, level_fn in HEADING_PATTERNS:
            match = re.match(pattern, line.strip())
            if match:
                heading_match = match
                level = level_fn(match) if callable(level_fn) else level_fn
                break

        if heading_match:
            # Flush previous section text
            flush_text()

            # Extract heading text
            groups = heading_match.groups()
            heading = groups[-1] if len(groups) > 1 else groups[0]
            heading = heading.strip()

            # Build section path
            normalized = normalize_heading(heading)

            # Handle nesting
            while section_stack and section_stack[-1][0] >= level:
                section_stack.pop()

            if section_stack:
                parent_path = section_stack[-1][1].path
                path = f"{parent_path}/{normalized}"
            else:
                path = normalized

            # Create section
            new_section = Section(
                heading=heading,
                level=level,
                path=path
            )

            # Add to parent or root
            if section_stack:
                section_stack[-1][1].children.append(new_section)
            else:
                sections.append(new_section)

            section_stack.append((level, new_section))
            current_section = new_section
        else:
            # Regular text line
            if line.strip():
                current_text.append(line)

    # Flush final section
    flush_text()

    # If no sections found, create a root section
    if not sections and text.strip():
        root = Section(heading="Document", level=0, path="document")
        root.spans.append(Span.create(
            text=text.strip(),
            section_path="document",
            page=0,
            start_char=0
        ))
        sections.append(root)

    return sections


# ============================================================================
# Caption Detection
# ============================================================================

CAPTION_PATTERNS = [
    r'Figure\s+\d+[.:]\s*(.+)',
    r'Fig\.\s*\d+[.:]\s*(.+)',
    r'Table\s+\d+[.:]\s*(.+)',
    r'Algorithm\s+\d+[.:]\s*(.+)',
    r'Listing\s+\d+[.:]\s*(.+)',
]


def extract_captions(text: str) -> List[Span]:
    """Extract figure/table captions as high-signal spans."""
    captions = []
    for pattern in CAPTION_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            caption_text = match.group(0)
            span = Span.create(
                text=caption_text,
                section_path="captions",
                page=0,
                start_char=match.start()
            )
            span.metadata['caption_type'] = pattern.split('\\')[0].lower()
            captions.append(span)
    return captions


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python document_model.py <file.txt|file.md>")
        print("       python document_model.py --test")
        sys.exit(1)

    if sys.argv[1] == "--test":
        # Test with sample academic text
        sample = """
# Abstract

This paper presents a novel approach to knowledge extraction.

# 1. Introduction

Knowledge extraction is fundamental to AI systems.

## 1.1 Contributions

Our main contributions are:
- A new extraction algorithm
- Evaluation on 10 datasets

# 2. Methods

We use transformer-based models.

## 2.1 Assumptions

We assume clean text input.

# 3. Results

Our method achieves 95% accuracy.

Table 1: Performance comparison across datasets.

# 4. Limitations

The method requires significant compute.

# 5. Conclusion

We presented an effective knowledge extraction approach.
"""
        doc = DocumentModel.from_text(sample, "test.md", "Test Paper")
        print(json.dumps(doc.to_dict(), indent=2))

        print("\n--- High Signal Spans ---")
        for span in doc.all_spans():
            print(f"[{span.section_path}] {span.text[:80]}...")
    else:
        filepath = Path(sys.argv[1])
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)

        text = filepath.read_text(encoding='utf-8', errors='replace')
        doc = DocumentModel.from_text(text, filepath.name)
        print(json.dumps(doc.to_dict(), indent=2))
