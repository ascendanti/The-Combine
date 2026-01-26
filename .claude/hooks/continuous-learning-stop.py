#!/usr/bin/env python3
"""
Continuous Learning Stop Hook
Extracts patterns from session and stores in memory system.

Runs at session end to capture:
- Error resolutions
- User corrections
- Workarounds discovered
- Debugging techniques used
- Project-specific patterns
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add daemon to path
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

def get_session_summary():
    """Extract session summary from stdin if provided by Stop hook."""
    try:
        if not sys.stdin.isatty():
            data = sys.stdin.read()
            if data.strip():
                return json.loads(data)
    except:
        pass
    return None

def extract_patterns_from_summary(summary: dict) -> list:
    """Extract learnable patterns from session summary."""
    patterns = []
    
    # Check for error resolutions
    if summary.get("errors_encountered"):
        for error in summary["errors_encountered"]:
            if error.get("resolved"):
                patterns.append({
                    "type": "error_resolution",
                    "content": f"Error: {error.get('message', 'unknown')} -> Fix: {error.get('resolution', 'unknown')}",
                    "confidence": "high" if error.get("verified") else "medium"
                })
    
    # Check for tool usage patterns
    if summary.get("tools_used"):
        tool_counts = {}
        for tool in summary["tools_used"]:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        # Identify frequently used tools (potential optimization targets)
        for tool, count in tool_counts.items():
            if count >= 5:
                patterns.append({
                    "type": "tool_usage",
                    "content": f"Heavy usage of {tool} ({count}x) - consider optimization",
                    "confidence": "medium"
                })
    
    return patterns

def store_learning(learning: dict):
    """Store learning in daemon memory system."""
    try:
        from daemon.memory import MemoryManager
        manager = MemoryManager()
        manager.store_learning(
            session_id=f"stop-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            learning_type=learning.get("type", "SESSION_PATTERN"),
            content=learning.get("content", ""),
            context="continuous-learning-stop-hook",
            tags=["auto-extracted", learning.get("type", "unknown")],
            confidence=learning.get("confidence", "medium")
        )
        return True
    except Exception as e:
        # Fallback: write to file
        learned_path = Path.home() / ".claude" / "skills" / "learned"
        learned_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = learned_path / f"learning_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump({
                "timestamp": timestamp,
                "learning": learning,
                "error": str(e)
            }, f, indent=2)
        return False

def trigger_self_improvement():
    """Trigger self-improvement analysis if available."""
    try:
        from daemon.self_improvement import SelfImprovementEngine
        engine = SelfImprovementEngine()

        # Record this session
        engine.record_session_analysis(
            session_id=f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            analysis_type="stop_hook",
            findings={"source": "continuous-learning-stop-hook"},
            recommendations=[]
        )
        return True
    except Exception as e:
        return False


def trigger_emergent_cycle():
    """
    WIRED: Trigger emergent learning cycle on session stop.
    This runs pattern detection, task generation, and goal refinement.
    """
    try:
        from daemon.emergent import run_emergent_cycle
        results = run_emergent_cycle()
        print(f"[Emergent] Detected {results['patterns_detected']} patterns, "
              f"generated {results['tasks_generated']} tasks", file=sys.stderr)
        return results
    except ImportError as e:
        print(f"[Emergent] Module not available: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Emergent] Error in cycle: {e}", file=sys.stderr)
        return None


def trigger_feedback_cycle():
    """
    WIRED: Trigger feedback loop analytics on session stop.
    Analyzes outcomes, updates strategy fitness, stores learnings.
    """
    try:
        from daemon.feedback_loop import run_feedback_cycle
        run_feedback_cycle()
        print(f"[FeedbackLoop] Analytics cycle complete", file=sys.stderr)
        return True
    except ImportError as e:
        print(f"[FeedbackLoop] Module not available: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[FeedbackLoop] Error: {e}", file=sys.stderr)
        return False

def main():
    """Main entry point for Stop hook."""
    output = {
        "status": "ok",
        "learnings_extracted": 0,
        "stored": False,
        "emergent_cycle": None
    }

    try:
        # Get session summary if available
        summary = get_session_summary()

        if summary:
            # Extract patterns
            patterns = extract_patterns_from_summary(summary)
            output["learnings_extracted"] = len(patterns)

            # Store each pattern
            for pattern in patterns:
                if store_learning(pattern):
                    output["stored"] = True

        # Always trigger self-improvement analysis
        trigger_self_improvement()

        # WIRED: Run emergent learning cycle
        # This detects patterns, generates tasks, refines goals, identifies learning targets
        emergent_results = trigger_emergent_cycle()
        if emergent_results:
            output["emergent_cycle"] = {
                "patterns": emergent_results.get("patterns_detected", 0),
                "tasks": emergent_results.get("tasks_generated", 0),
                "refinements": emergent_results.get("goal_refinements", 0),
                "learning_targets": emergent_results.get("learning_targets", 0)
            }

        # WIRED: Run feedback loop analytics
        # Analyzes outcomes, updates strategy fitness, stores learnings
        feedback_ran = trigger_feedback_cycle()
        output["feedback_loop"] = feedback_ran

        # Output for hook system
        print(f"[ContinuousLearning] Extracted {output['learnings_extracted']} patterns", file=sys.stderr)

    except Exception as e:
        output["error"] = str(e)
        print(f"[ContinuousLearning] Error: {e}", file=sys.stderr)

    # Return success to not block session end
    print(json.dumps(output))

if __name__ == "__main__":
    main()
