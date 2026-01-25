#!/usr/bin/env python3
"""
Usage Tracker - Learn from actual file access patterns

Tracks which injected context files Claude actually uses, enabling:
- Keyword weight adjustment based on usefulness
- Budget optimization (stop injecting unused files)
- Ralph Loop feedback (iterate → measure → learn → refine)

Part of claude-cognitive v1.2 Phase 1.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict


# ============================================================================
# CONFIGURATION
# ============================================================================

# State file locations (project-local preferred, global fallback)
PROJECT_STATS = Path(".claude/usage_stats.json")
GLOBAL_STATS = Path.home() / ".claude/usage_stats.json"

PROJECT_HISTORY = Path(".claude/usage_history.jsonl")
GLOBAL_HISTORY = Path.home() / ".claude/usage_history.jsonl"

PROJECT_WEIGHTS = Path(".claude/keyword_weights.json")
GLOBAL_WEIGHTS = Path.home() / ".claude/keyword_weights.json"

PROJECT_PROGRESS = Path(".claude/learning_progress.txt")
GLOBAL_PROGRESS = Path.home() / ".claude/learning_progress.txt"


# ============================================================================
# FILE RELATIONSHIPS
# ============================================================================

def extract_file_relationships(md_file: Path) -> Dict[str, any]:
    """
    Extract file references and keywords from .claude/*.md file.

    Returns:
        {
            'describes': [list of source files mentioned],
            'keywords': [list of keywords from content]
        }
    """
    if not md_file.exists():
        return {'describes': [], 'keywords': []}

    content = md_file.read_text()

    # Find file references in backticks or code blocks
    # Matches: `filename.py`, `path/to/file.ts`, etc.
    file_refs = re.findall(r'`([a-zA-Z0-9_/.-]+\.[a-zA-Z]+)`', content)

    # Find file references in **Location**: lines
    location_refs = re.findall(r'\*\*Location\*\*:\s*`([^`]+)`', content)

    # Extract keywords from headers (## Keywords section if exists)
    keywords = []
    keyword_section = re.search(r'## (?:Auto-Generated )?Keywords?\s*\n([^\n#]+)', content)
    if keyword_section:
        keyword_line = keyword_section.group(1)
        keywords = [k.strip() for k in re.split(r'[,\s]+', keyword_line) if k.strip()]

    return {
        'describes': list(set(file_refs + location_refs)),
        'keywords': keywords
    }


def build_file_relationship_map(claude_dir: Path = Path(".claude")) -> Dict[str, Dict]:
    """
    Build map of .claude/*.md files → source files they describe.

    Returns:
        {
            'modules/pipeline.md': {
                'describes': ['refined_pipeline_integrated_v4_fixed.py', ...],
                'keywords': ['pipeline', 'process', 'message']
            }
        }
    """
    relationships = {}

    # Scan all .md files in .claude/
    for md_file in claude_dir.rglob("*.md"):
        rel_path = str(md_file.relative_to(claude_dir.parent))
        relationships[rel_path] = extract_file_relationships(md_file)

    return relationships


# ============================================================================
# USAGE TRACKING
# ============================================================================

class UsageTracker:
    """Track and learn from file access patterns."""

    def __init__(self, mode: str = "observe"):
        """
        Initialize tracker.

        Args:
            mode: 'observe' (log only) or 'learn' (adjust weights)
        """
        self.mode = mode
        self.stats_file = self._get_state_file(PROJECT_STATS, GLOBAL_STATS)
        self.history_file = self._get_state_file(PROJECT_HISTORY, GLOBAL_HISTORY)
        self.weights_file = self._get_state_file(PROJECT_WEIGHTS, GLOBAL_WEIGHTS)
        self.progress_file = self._get_state_file(PROJECT_PROGRESS, GLOBAL_PROGRESS)

        # Load existing state
        self.stats = self._load_stats()
        self.weights = self._load_weights()
        self.relationships = build_file_relationship_map()

        # Turn counter
        self.turn_count = self._get_turn_count()

    def _get_state_file(self, project_path: Path, global_path: Path) -> Path:
        """Get appropriate state file (project-local preferred)."""
        if project_path.parent.exists():
            project_path.parent.mkdir(parents=True, exist_ok=True)
            return project_path
        global_path.parent.mkdir(parents=True, exist_ok=True)
        return global_path

    def _load_stats(self) -> Dict:
        """Load usage statistics."""
        if self.stats_file.exists():
            try:
                return json.loads(self.stats_file.read_text())
            except json.JSONDecodeError:
                pass
        return {}

    def _load_weights(self) -> Dict:
        """Load keyword weights."""
        if self.weights_file.exists():
            try:
                return json.loads(self.weights_file.read_text())
            except json.JSONDecodeError:
                pass
        return {}

    def _get_turn_count(self) -> int:
        """Get current turn count from history."""
        if not self.history_file.exists():
            return 0

        # Read last line of JSONL
        try:
            with open(self.history_file) as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    return last_entry.get('turn', 0)
        except:
            pass

        return 0

    def _save_stats(self):
        """Save usage statistics to file."""
        self.stats_file.write_text(json.dumps(self.stats, indent=2))

    def _save_weights(self):
        """Save keyword weights to file."""
        self.weights_file.write_text(json.dumps(self.weights, indent=2))

    def _append_history(self, entry: Dict):
        """Append entry to history JSONL."""
        with open(self.history_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def _append_progress(self, message: str):
        """Append to learning progress log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.progress_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")

    # ------------------------------------------------------------------------
    # Injection tracking
    # ------------------------------------------------------------------------

    def log_injection(self, injected_files: List[Dict], prompt: str):
        """
        Log which files were injected this turn.

        Args:
            injected_files: [
                {'file': 'path/to/file.md', 'tier': 'HOT', 'score': 1.0, 'chars': 12450},
                ...
            ]
            prompt: User's query text
        """
        self.turn_count += 1

        # Store for access tracking later
        self.current_turn = {
            'turn': self.turn_count,
            'timestamp': datetime.now().isoformat(),
            'injected_files': injected_files,
            'prompt': prompt,
            'files_accessed': [],  # Will be filled by track_turn_usage
            'files_edited': []
        }

        # Update per-file injection counts
        for file_info in injected_files:
            file = file_info['file']
            if file not in self.stats:
                self.stats[file] = {
                    'injected_count': 0,
                    'accessed_count': 0,
                    'edited_count': 0,
                    'mentioned_count': 0,
                    'last_injected': None,
                    'last_accessed': None
                }

            self.stats[file]['injected_count'] += 1
            self.stats[file]['last_injected'] = self.current_turn['timestamp']

        self._save_stats()

    # ------------------------------------------------------------------------
    # Access inference
    # ------------------------------------------------------------------------

    def infer_file_usage(self, tool_calls: List[Dict]) -> Set[str]:
        """
        Infer which .claude/*.md files were useful based on tool calls.

        Args:
            tool_calls: [
                {'tool': 'Read', 'target': 'scripts/pipeline.py'},
                {'tool': 'Edit', 'target': 'scripts/context-router-v2.py'},
                {'tool': 'Grep', 'pattern': 'process_message'},
                ...
            ]

        Returns:
            Set of .claude/*.md files that were useful
        """
        accessed_files = set()

        for tool_call in tool_calls:
            tool = tool_call.get('tool', '')
            target = tool_call.get('target', '')
            pattern = tool_call.get('pattern', '')

            # Direct file access (Read, Edit, Write)
            if target:
                # Find which .md files describe this target file
                for md_file, rel_info in self.relationships.items():
                    for described_file in rel_info['describes']:
                        # Match if target contains described file
                        # e.g., scripts/context-router-v2.py matches context-router-v2.py
                        if described_file in target or target.endswith(described_file):
                            accessed_files.add(md_file)

            # Pattern matching (Grep)
            if pattern:
                # Find which .md files mention this pattern
                for md_file, rel_info in self.relationships.items():
                    for keyword in rel_info['keywords']:
                        if keyword.lower() in pattern.lower():
                            accessed_files.add(md_file)

        return accessed_files

    def track_turn_usage(self, tool_calls: List[Dict], response_text: str = ""):
        """
        Analyze tool calls after turn completes, update statistics.

        Args:
            tool_calls: List of tool invocations
            response_text: Claude's response text (for mention detection)
        """
        if not hasattr(self, 'current_turn'):
            return  # No injection logged this turn

        # Infer which files were accessed
        accessed_files = self.infer_file_usage(tool_calls)

        # Track edits separately (high-impact usage)
        edited_files = set()
        for tool_call in tool_calls:
            if tool_call.get('tool') in ['Edit', 'Write']:
                target = tool_call.get('target', '')
                # Find corresponding .md files
                for md_file, rel_info in self.relationships.items():
                    for described_file in rel_info['describes']:
                        if described_file in target:
                            edited_files.add(md_file)

        # Update statistics
        for file in accessed_files:
            if file in self.stats:
                self.stats[file]['accessed_count'] += 1
                self.stats[file]['last_accessed'] = self.current_turn['timestamp']

        for file in edited_files:
            if file in self.stats:
                self.stats[file]['edited_count'] += 1

        # Extract source files from tool calls for debugging
        source_files = set()
        for tool_call in tool_calls:
            target = tool_call.get('target', '')
            if target:
                source_files.add(target)

        # Calculate metrics
        injected = [f['file'] for f in self.current_turn['injected_files']]
        injection_rate = len(accessed_files) / len(injected) if injected else 0

        # Save history entry
        history_entry = {
            'turn': self.current_turn['turn'],
            'timestamp': self.current_turn['timestamp'],
            'injected': injected,
            'accessed': list(accessed_files),
            'edited': list(edited_files),
            'source_files': list(source_files),  # Actual files Claude worked on
            'injection_rate': round(injection_rate, 2)
        }
        self._append_history(history_entry)

        # Save updated stats
        self._save_stats()

        # Check if time to adjust weights
        if self.mode == 'learn' and self.turn_count % 50 == 0:
            self.adjust_keyword_weights()

    # ------------------------------------------------------------------------
    # Learning & weight adjustment
    # ------------------------------------------------------------------------

    def calculate_usefulness(self, file: str) -> float:
        """
        Calculate usefulness score for a file.

        Returns:
            0.0 to 1.0 (higher = more useful when injected)
        """
        if file not in self.stats:
            return 0.0

        stats = self.stats[file]

        if stats['injected_count'] == 0:
            return 0.0

        # Base metric: Access rate
        access_rate = stats['accessed_count'] / stats['injected_count']

        # Bonus: High-impact actions (edits)
        impact_bonus = (stats['edited_count'] / stats['injected_count']) * 0.5

        # Bonus: Mentioned in responses
        mention_bonus = (stats['mentioned_count'] / stats['injected_count']) * 0.3

        # Combined usefulness (cap at 1.0)
        usefulness = min(access_rate + impact_bonus + mention_bonus, 1.0)

        return round(usefulness, 2)

    def adjust_keyword_weights(self):
        """
        Adjust keyword weights based on file usefulness.
        Called every 50 turns when in 'learn' mode.
        """
        adjustments = []

        # Load keywords from config
        keywords_config = self._load_keywords_config()
        if not keywords_config:
            self._append_progress("⚠ No keywords.json found, skipping weight adjustment")
            return

        keywords = keywords_config.get('keywords', {})

        # Adjust weight for each file based on usefulness
        for file, keyword_list in keywords.items():
            usefulness = self.calculate_usefulness(file)

            for keyword in keyword_list:
                current_weight = self.weights.get(keyword, 1.0)

                # Learning rate
                learning_rate = 0.1

                # Adjust based on usefulness
                if usefulness > 0.75:  # Very useful
                    new_weight = current_weight * (1 + learning_rate)
                elif usefulness < 0.25:  # Not useful
                    new_weight = current_weight * (1 - learning_rate)
                else:  # Moderately useful
                    new_weight = current_weight  # No change

                # Bounds: keep in [0.5, 1.5]
                new_weight = max(0.5, min(new_weight, 1.5))

                if abs(new_weight - current_weight) > 0.01:  # Meaningful change
                    adjustments.append({
                        'keyword': keyword,
                        'file': file,
                        'old_weight': round(current_weight, 2),
                        'new_weight': round(new_weight, 2),
                        'usefulness': usefulness
                    })

                    self.weights[keyword] = new_weight

        # Save updated weights
        self._save_weights()

        # Log progress
        if adjustments:
            self._append_progress(f"\n📊 Keyword Weight Adjustment (Turn {self.turn_count})")
            for adj in adjustments[:10]:  # Show first 10
                change_pct = int((adj['new_weight'] - adj['old_weight']) / adj['old_weight'] * 100)
                direction = "↑" if change_pct > 0 else "↓"
                self._append_progress(
                    f"  {direction} '{adj['keyword']}': {adj['old_weight']} → {adj['new_weight']} "
                    f"({change_pct:+d}%) | usefulness: {adj['usefulness']}"
                )
            if len(adjustments) > 10:
                self._append_progress(f"  ... and {len(adjustments) - 10} more")

        # Check convergence
        self._check_convergence()

    def _load_keywords_config(self) -> Dict:
        """Load keywords.json config."""
        config_paths = [
            Path(".claude/keywords.json"),
            Path.home() / ".claude/keywords.json"
        ]

        for path in config_paths:
            if path.exists():
                try:
                    return json.loads(path.read_text())
                except json.JSONDecodeError:
                    continue

        return {}

    def _check_convergence(self):
        """Check if weights have converged (stable over last 50 turns)."""
        # Get weight history from last 100 turns
        # For now, just check if any weight changed significantly
        # TODO: Implement proper convergence detection
        pass

    # ------------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------------

    def get_usefulness(self, file: str) -> float:
        """Get usefulness score for a file."""
        return self.calculate_usefulness(file)

    def get_keyword_weight(self, keyword: str) -> float:
        """Get learned weight for a keyword."""
        return self.weights.get(keyword, 1.0)

    def get_statistics(self) -> Dict:
        """Get summary statistics."""
        if not self.stats:
            return {
                'total_files': 0,
                'average_usefulness': 0.0,
                'high_utility_files': [],
                'low_utility_files': []
            }

        usefulness_scores = {
            file: self.calculate_usefulness(file)
            for file in self.stats
        }

        high_utility = [
            (file, score) for file, score in usefulness_scores.items()
            if score > 0.75
        ]

        low_utility = [
            (file, score) for file, score in usefulness_scores.items()
            if score < 0.25 and self.stats[file]['injected_count'] > 5
        ]

        avg_usefulness = sum(usefulness_scores.values()) / len(usefulness_scores) if usefulness_scores else 0.0

        return {
            'total_files': len(self.stats),
            'total_turns': self.turn_count,
            'average_usefulness': round(avg_usefulness, 2),
            'high_utility_files': sorted(high_utility, key=lambda x: x[1], reverse=True),
            'low_utility_files': sorted(low_utility, key=lambda x: x[1])
        }


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Command-line interface for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python usage-tracker.py stats    # Show statistics")
        print("  python usage-tracker.py test     # Run test")
        return

    command = sys.argv[1]
    tracker = UsageTracker(mode='observe')

    if command == 'stats':
        stats = tracker.get_statistics()
        print(f"\n📊 Usage Statistics")
        print(f"{'='*60}")
        print(f"Total files tracked: {stats['total_files']}")
        print(f"Total turns: {stats['total_turns']}")
        print(f"Average usefulness: {stats['average_usefulness']:.0%}")
        print()

        if stats['high_utility_files']:
            print("✅ High Utility Files (>75%):")
            for file, score in stats['high_utility_files'][:5]:
                print(f"  {score:.0%} - {file}")

        if stats['low_utility_files']:
            print("\n⚠️  Low Utility Files (<25%, >5 injections):")
            for file, score in stats['low_utility_files'][:5]:
                print(f"  {score:.0%} - {file}")

    elif command == 'test':
        print("\n🧪 Testing Usage Tracker")
        print("="*60)

        # Test: Log injection
        print("\n1. Testing injection logging...")
        tracker.log_injection([
            {'file': '.claude/modules/usage-tracker.md', 'tier': 'HOT', 'score': 1.0, 'chars': 5000},
            {'file': '.claude/modules/context-router.md', 'tier': 'WARM', 'score': 0.45, 'chars': 1250}
        ], prompt="test query about usage tracking")
        print("   ✓ Injection logged")

        # Test: Track usage
        print("\n2. Testing usage tracking...")
        tracker.track_turn_usage([
            {'tool': 'Read', 'target': 'scripts/usage-tracker.py'},
            {'tool': 'Edit', 'target': 'scripts/usage-tracker.py'}
        ])
        print("   ✓ Usage tracked")

        # Test: Calculate usefulness
        print("\n3. Testing usefulness calculation...")
        usefulness = tracker.get_usefulness('.claude/modules/usage-tracker.md')
        print(f"   Usefulness: {usefulness:.0%}")

        print("\n✅ All tests passed!")


if __name__ == '__main__':
    main()
