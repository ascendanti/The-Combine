"""
Span Selector - Deterministic selection of high-ROI spans.

Part of UTF v2 architecture. Replaces "chunk first 3" with structural selection.

High-signal sections for academic papers:
- Abstract
- Introduction contributions
- Method/assumptions
- Results/findings
- Limitations
- Conclusion
- Figure/table captions (shockingly high-signal)
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Import will work once document_model.py is in place
try:
    from document_model import DocumentModel, Section, Span, extract_captions
except ImportError:
    DocumentModel = None
    Section = None
    Span = None


# ============================================================================
# High Signal Section Patterns
# ============================================================================

HIGH_SIGNAL_SECTIONS = {
    # Section path pattern -> priority (lower = higher priority)
    'abstract': 1,
    'introduction/contributions': 2,
    'introduction/problem': 3,
    'introduction': 4,
    'methods': 5,
    'methodology': 5,
    'approach': 5,
    'assumptions': 6,
    'results': 7,
    'findings': 7,
    'experiments': 7,
    'evaluation': 7,
    'limitations': 8,
    'threats': 8,  # threats to validity
    'discussion': 9,
    'conclusion': 10,
    'summary': 10,
}

# Patterns to find contribution statements
CONTRIBUTION_PATTERNS = [
    r'our\s+(?:main\s+)?contributions?\s+(?:are|include)',
    r'we\s+contribute',
    r'the\s+contributions?\s+of\s+this',
    r'in\s+this\s+paper,?\s+we',
    r'we\s+present',
    r'we\s+propose',
    r'we\s+introduce',
    r'this\s+paper\s+presents',
]

# Patterns to find limitations
LIMITATION_PATTERNS = [
    r'limitations?\s+(?:of|include)',
    r'(?:our|the)\s+approach\s+(?:has|suffers)',
    r'does\s+not\s+(?:handle|support|work)',
    r'future\s+work\s+(?:could|should|will)',
    r'we\s+(?:do\s+not|don\'t)\s+(?:consider|handle)',
]

# Patterns for result claims
RESULT_PATTERNS = [
    r'achieves?\s+(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?)',
    r'outperforms?',
    r'improves?\s+(?:upon|over|by)',
    r'reduces?\s+(?:by|\d)',
    r'increases?\s+(?:by|\d)',
    r'(?:accuracy|precision|recall|f1)\s*(?:of|:)?\s*\d',
]


# ============================================================================
# Span Selection
# ============================================================================

@dataclass
class SelectionResult:
    """Result of span selection."""
    spans: List['Span']
    total_chars: int
    section_coverage: Dict[str, int]  # section -> char count
    priority_scores: Dict[str, int]   # span_id -> priority


def select_spans(doc: 'DocumentModel', max_chars: int = 50000) -> List['Span']:
    """
    Select high-signal spans using structural analysis.

    Algorithm:
    1. Score all sections by priority
    2. Find spans containing contribution/limitation/result patterns
    3. Extract captions
    4. Rank and select up to max_chars

    Returns spans sorted by priority (highest signal first).
    """
    if not doc or not doc.sections:
        return []

    candidates = []

    # 1. Score sections and collect spans
    for section in doc.sections:
        section_spans = collect_section_spans(section, doc.raw_text)
        candidates.extend(section_spans)

    # 2. Add caption spans
    captions = extract_captions(doc.raw_text)
    for cap in captions:
        cap.metadata['priority'] = 5  # High priority for captions
        candidates.append(cap)

    # 3. Boost spans with pattern matches
    boost_pattern_matches(candidates)

    # 4. Sort by priority (lower is better)
    candidates.sort(key=lambda s: s.metadata.get('priority', 100))

    # 5. Select up to max_chars
    selected = []
    total_chars = 0

    for span in candidates:
        if total_chars + len(span.text) > max_chars:
            continue
        selected.append(span)
        total_chars += len(span.text)

    return selected


def collect_section_spans(section: 'Section', raw_text: str = "") -> List['Span']:
    """Collect spans from section with priority scoring."""
    spans = []

    # Get base priority from section path
    priority = get_section_priority(section.path)

    for span in section.spans:
        span.metadata['priority'] = priority
        span.metadata['section'] = section.path
        spans.append(span)

    # Recursively process children
    for child in section.children:
        child_spans = collect_section_spans(child, raw_text)
        spans.extend(child_spans)

    return spans


def get_section_priority(path: str) -> int:
    """Get priority score for section (lower = higher priority)."""
    path_lower = path.lower()

    for pattern, priority in HIGH_SIGNAL_SECTIONS.items():
        if pattern in path_lower:
            return priority

    # Unknown sections get low priority
    return 50


def boost_pattern_matches(spans: List['Span']) -> None:
    """Boost priority of spans containing key patterns."""
    for span in spans:
        text_lower = span.text.lower()

        # Check contribution patterns
        for pattern in CONTRIBUTION_PATTERNS:
            if re.search(pattern, text_lower):
                span.metadata['priority'] = min(
                    span.metadata.get('priority', 100),
                    2  # Same as introduction/contributions
                )
                span.metadata['has_contribution'] = True
                break

        # Check limitation patterns
        for pattern in LIMITATION_PATTERNS:
            if re.search(pattern, text_lower):
                span.metadata['priority'] = min(
                    span.metadata.get('priority', 100),
                    8  # Same as limitations
                )
                span.metadata['has_limitation'] = True
                break

        # Check result patterns
        for pattern in RESULT_PATTERNS:
            if re.search(pattern, text_lower):
                span.metadata['priority'] = min(
                    span.metadata.get('priority', 100),
                    7  # Same as results
                )
                span.metadata['has_result'] = True
                break


# ============================================================================
# Alternative: Heuristic Selection (No Parse)
# ============================================================================

def select_spans_heuristic(text: str, max_chars: int = 50000) -> List[Dict]:
    """
    Fallback selection when full parsing fails.
    Uses regex patterns to find high-signal regions.

    Returns list of dicts with 'text', 'start', 'end', 'type'.
    """
    regions = []

    # Find abstract
    abstract_match = re.search(
        r'(?:abstract|summary)\s*\n+(.*?)(?=\n\s*(?:introduction|keywords|1\.|#))',
        text, re.IGNORECASE | re.DOTALL
    )
    if abstract_match:
        regions.append({
            'text': abstract_match.group(1).strip(),
            'start': abstract_match.start(1),
            'end': abstract_match.end(1),
            'type': 'abstract',
            'priority': 1
        })

    # Find introduction (first section after abstract)
    intro_match = re.search(
        r'(?:introduction|1\.?\s+introduction)\s*\n+(.*?)(?=\n\s*(?:2\.|##?\s+\d|methods|related))',
        text, re.IGNORECASE | re.DOTALL
    )
    if intro_match:
        intro_text = intro_match.group(1).strip()
        # Look for contributions within introduction
        contrib_match = re.search(
            r'((?:our|the)\s+(?:main\s+)?contributions?.*?)(?=\n\s*\n|\Z)',
            intro_text, re.IGNORECASE | re.DOTALL
        )
        if contrib_match:
            regions.append({
                'text': contrib_match.group(1).strip(),
                'start': intro_match.start(1) + contrib_match.start(1),
                'end': intro_match.start(1) + contrib_match.end(1),
                'type': 'contributions',
                'priority': 2
            })

    # Find conclusions
    concl_match = re.search(
        r'(?:conclusion|conclusions|summary)\s*\n+(.*?)(?=\n\s*(?:references|acknowledgments|\Z))',
        text, re.IGNORECASE | re.DOTALL
    )
    if concl_match:
        regions.append({
            'text': concl_match.group(1).strip()[:3000],  # Limit length
            'start': concl_match.start(1),
            'end': concl_match.end(1),
            'type': 'conclusion',
            'priority': 10
        })

    # Find limitations
    limit_match = re.search(
        r'(?:limitations?|threats\s+to\s+validity)\s*\n+(.*?)(?=\n\s*(?:##?|\d\.|conclusion|future))',
        text, re.IGNORECASE | re.DOTALL
    )
    if limit_match:
        regions.append({
            'text': limit_match.group(1).strip()[:2000],
            'start': limit_match.start(1),
            'end': limit_match.end(1),
            'type': 'limitations',
            'priority': 8
        })

    # Find all captions
    for match in re.finditer(
        r'((?:Figure|Fig\.|Table|Algorithm)\s+\d+[.:]\s*[^\n]+)',
        text, re.IGNORECASE
    ):
        regions.append({
            'text': match.group(1).strip(),
            'start': match.start(1),
            'end': match.end(1),
            'type': 'caption',
            'priority': 5
        })

    # Sort by priority and limit total chars
    regions.sort(key=lambda r: r['priority'])

    selected = []
    total = 0
    for r in regions:
        if total + len(r['text']) > max_chars:
            continue
        selected.append(r)
        total += len(r['text'])

    return selected


# ============================================================================
# Span Selection Analysis
# ============================================================================

def analyze_coverage(doc: 'DocumentModel', selected: List['Span']) -> Dict:
    """Analyze what's covered vs missed in selection."""
    total_chars = doc.total_chars
    selected_chars = sum(len(s.text) for s in selected)

    sections_covered = set(s.metadata.get('section', '') for s in selected)
    all_sections = set()
    for section in doc.sections:
        all_sections.add(section.path)
        for child in section.children:
            all_sections.add(child.path)

    return {
        'total_chars': total_chars,
        'selected_chars': selected_chars,
        'coverage_pct': round(100 * selected_chars / total_chars, 1) if total_chars else 0,
        'sections_covered': list(sections_covered),
        'sections_missed': list(all_sections - sections_covered),
        'span_count': len(selected),
        'has_abstract': any('abstract' in s.section_path for s in selected),
        'has_contributions': any(s.metadata.get('has_contribution') for s in selected),
        'has_results': any(s.metadata.get('has_result') for s in selected),
        'has_limitations': any(s.metadata.get('has_limitation') for s in selected),
        'has_captions': any('caption' in s.section_path for s in selected),
    }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    import json
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python span_selector.py <file.txt|file.md>")
        print("       python span_selector.py --test")
        sys.exit(1)

    if sys.argv[1] == "--test":
        # Test with sample text
        sample = """
# Abstract

This paper presents a novel knowledge extraction system achieving 95% accuracy.

# 1. Introduction

Knowledge extraction is fundamental.

Our main contributions are:
1. A new algorithm for claim extraction
2. Evaluation on 10 datasets
3. Open source implementation

# 2. Methods

We use transformer models.

## 2.1 Assumptions

We assume clean input text without OCR errors.

# 3. Results

Our method achieves 95.2% accuracy on benchmark.

Table 1: Performance comparison.

Figure 1: Architecture overview of our system.

# 4. Limitations

Our approach does not handle multi-modal input.
Future work could extend to images and tables.

# 5. Conclusion

We presented an effective extraction system.
"""
        from document_model import DocumentModel
        doc = DocumentModel.from_text(sample, "test.md")
        selected = select_spans(doc)

        print("=== Selected Spans ===")
        for span in selected:
            print(f"[P{span.metadata.get('priority', '?')}] {span.section_path}")
            print(f"    {span.text[:100]}...")
            print()

        print("=== Coverage Analysis ===")
        coverage = analyze_coverage(doc, selected)
        print(json.dumps(coverage, indent=2))

    else:
        from document_model import DocumentModel
        filepath = Path(sys.argv[1])
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)

        text = filepath.read_text(encoding='utf-8', errors='replace')
        doc = DocumentModel.from_text(text, filepath.name)
        selected = select_spans(doc)

        print(f"Selected {len(selected)} spans from {doc.total_chars} chars")
        print()

        for span in selected[:10]:  # Show first 10
            print(f"[{span.section_path}] {span.text[:80]}...")

        coverage = analyze_coverage(doc, selected)
        print(f"\nCoverage: {coverage['coverage_pct']}%")
        print(f"Has abstract: {coverage['has_abstract']}")
        print(f"Has contributions: {coverage['has_contributions']}")
        print(f"Has results: {coverage['has_results']}")
        print(f"Has limitations: {coverage['has_limitations']}")
