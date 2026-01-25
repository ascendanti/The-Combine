#!/usr/bin/env python3
"""
Feedback Bridge - Connects MAPE Controller to Decision Engine

Enables:
- Strategic decision-making for control actions using MCDA
- Learning from action outcomes to improve future decisions
- Preference adaptation based on satisfaction metrics

Usage:
    from feedback_bridge import FeedbackBridge
    bridge = FeedbackBridge()

    # Get decision-informed action
    action = bridge.decide_action(analysis)

    # Record outcome for learning
    bridge.record_outcome(action_id, metrics_before, metrics_after)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import controller and decisions
from controller import MAPEController, Action, ActionType, MetricType, Metric
from decisions import DecisionEngine, Criterion, ConfidenceLevel


class FeedbackBridge:
    """
    Bridges MAPE Controller and Decision Engine for adaptive learning.

    The controller handles monitoring/analysis/execution.
    The decision engine provides multi-criteria evaluation for action selection.
    This bridge coordinates learning between them.
    """

    def __init__(self):
        self.controller = MAPEController()
        self.decisions = DecisionEngine()
        self.domain = "controller_actions"  # For preference learning

    # ========================================================================
    # Decision-Informed Action Selection
    # ========================================================================

    def decide_action(self, analysis: Dict[str, Any]) -> Optional[Action]:
        """
        Use decision engine to select best action from controller's planned actions.

        Evaluates each candidate action using multi-criteria analysis:
        - predicted_improvement (weight: 0.4)
        - confidence based on past outcomes (weight: 0.3)
        - risk/uncertainty (weight: 0.3)
        """
        # Get candidate actions from controller
        actions = self.controller.plan(analysis)

        if not actions:
            return None

        if len(actions) == 1:
            return actions[0]

        # Evaluate each action using decision engine
        evaluated = []
        learned_weights = self.decisions.get_learned_weights(self.domain)

        for action in actions:
            criteria = self._action_to_criteria(action, learned_weights)
            decision = self.decisions.evaluate(
                title=f"Action: {action.type.value}",
                criteria=criteria,
                context=self.domain,
                risk_aversion=0.4  # Moderate risk aversion
            )
            evaluated.append((action, decision))

        # Sort by risk-adjusted value
        evaluated.sort(key=lambda x: x[1].risk_adjusted_value, reverse=True)

        # Return best action
        best_action, best_decision = evaluated[0]

        # Log decision rationale
        self._log_decision(best_action, best_decision, len(actions))

        return best_action

    def _action_to_criteria(self, action: Action, learned_weights: Dict[str, float]) -> List[Criterion]:
        """Convert action attributes to decision criteria."""

        # Get learned weights or use defaults
        w_improvement = learned_weights.get("improvement", 0.4)
        w_confidence = learned_weights.get("confidence", 0.3)
        w_risk = learned_weights.get("risk", 0.3)

        # Normalize
        total = w_improvement + w_confidence + w_risk
        w_improvement, w_confidence, w_risk = w_improvement/total, w_confidence/total, w_risk/total

        # Calculate scores

        # Improvement score (0-10 based on predicted improvement)
        improvement_score = min(10, action.predicted_improvement * 100)

        # Confidence score based on action type history
        confidence_score = self._get_action_type_confidence(action.type)

        # Risk score (inverse of uncertainty - simpler actions = lower risk)
        risk_score = self._estimate_action_risk(action)

        return [
            Criterion(
                name="improvement",
                weight=w_improvement,
                score=improvement_score,
                confidence=0.6,  # Medium confidence in predictions
                reasoning=f"Predicted improvement: {action.predicted_improvement:.3f}"
            ),
            Criterion(
                name="confidence",
                weight=w_confidence,
                score=confidence_score,
                confidence=0.8,  # High confidence in historical data
                reasoning=f"Based on past {action.type.value} outcomes"
            ),
            Criterion(
                name="risk",
                weight=w_risk,
                score=risk_score,
                confidence=0.5,  # Medium confidence in risk estimation
                reasoning=action.rationale
            )
        ]

    def _get_action_type_confidence(self, action_type: ActionType) -> float:
        """Get confidence score based on historical outcomes for this action type."""
        # Query controller for strategy effectiveness (proxy for action outcomes)
        rankings = self.controller._get_strategy_rankings()

        # If we have outcome data, use it
        # For now, assign reasonable defaults based on action type
        defaults = {
            ActionType.ADJUST_CHUNK_SIZE: 6.0,  # Common, well-understood
            ActionType.CHANGE_OVERLAP: 5.5,     # Moderate confidence
            ActionType.SWITCH_STRATEGY: 4.0,    # Higher uncertainty
            ActionType.MODIFY_PROMPT: 3.5,      # Hard to predict
            ActionType.ENABLE_CACHING: 7.0,     # Usually safe
            ActionType.ADJUST_RETRIEVAL_K: 5.0  # Moderate
        }

        return defaults.get(action_type, 5.0)

    def _estimate_action_risk(self, action: Action) -> float:
        """Estimate risk score (higher = lower risk)."""
        # Simple heuristic: smaller parameter changes = lower risk
        params = action.parameters

        if "delta" in params:
            delta = abs(params["delta"])
            # Larger deltas = higher risk = lower score
            return max(3, 10 - delta / 25)

        if "strategy" in params:
            return 5.0  # Strategy changes have moderate risk

        return 7.0  # Default to moderate-low risk

    def _log_decision(self, action: Action, decision, num_candidates: int):
        """Log the decision for debugging/auditing."""
        print(f"[BRIDGE] Selected action: {action.type.value}")
        print(f"  Candidates: {num_candidates}")
        print(f"  Risk-adjusted value: {decision.risk_adjusted_value}/10")
        print(f"  Confidence: {decision.confidence_level.value}")
        print(f"  Recommendation: {decision.recommendation}")

    # ========================================================================
    # Outcome Recording & Learning
    # ========================================================================

    def record_outcome(
        self,
        action_id: str,
        metrics_before: Dict[str, float],
        metrics_after: Dict[str, float],
        success: bool
    ):
        """
        Record action outcome in both controller and decision engine.

        This enables:
        - Controller feedback loop (strategy effectiveness)
        - Decision engine preference learning (criterion weights)
        """

        # 1. Record in controller
        self.controller.feedback(action_id, metrics_before, metrics_after, success)

        # 2. Calculate satisfaction for decision engine
        # Satisfaction = how much improvement exceeded predictions
        improvements = []
        for key in metrics_after:
            if key in metrics_before:
                improvements.append(metrics_after[key] - metrics_before[key])

        avg_improvement = sum(improvements) / len(improvements) if improvements else 0

        # Map improvement to satisfaction (0-10)
        # -0.1 improvement = 3/10, 0 = 5/10, +0.1 = 7/10, +0.2 = 9/10
        satisfaction = min(10, max(0, 5 + avg_improvement * 20))

        # 3. Find corresponding decision and record outcome
        # We need to map action_id to decision_id
        # For now, create a new decision record for this outcome
        self._record_decision_outcome(action_id, satisfaction, success, avg_improvement)

        print(f"[BRIDGE] Outcome recorded:")
        print(f"  Action: {action_id}")
        print(f"  Success: {success}")
        print(f"  Improvement: {avg_improvement:.4f}")
        print(f"  Satisfaction: {satisfaction:.1f}/10")

    def _record_decision_outcome(
        self,
        action_id: str,
        satisfaction: float,
        success: bool,
        improvement: float
    ):
        """Record outcome for preference learning."""
        # Create minimal decision criteria for learning
        criteria = [
            Criterion("improvement", 0.4, 5, 0.7),
            Criterion("confidence", 0.3, 5, 0.7),
            Criterion("risk", 0.3, 5, 0.7)
        ]

        # Evaluate to get a decision ID
        decision = self.decisions.evaluate(
            title=f"Outcome: {action_id}",
            criteria=criteria,
            context=self.domain
        )

        # Record outcome
        result = "successful" if success else "failed"
        lessons = f"Improvement: {improvement:.4f}"

        self.decisions.record_outcome(
            decision.id,
            actual_result=result,
            satisfaction=satisfaction,
            lessons=lessons
        )

    # ========================================================================
    # Integrated MAPE Cycle with Decision Support
    # ========================================================================

    def run_cycle(self, new_metrics: List[Metric] = None) -> Dict[str, Any]:
        """
        Run MAPE cycle with decision-informed action selection.

        Monitor -> Analyze -> Decide -> Execute -> (Feedback later)
        """
        result = {"timestamp": datetime.now().isoformat()}

        # Monitor
        if new_metrics:
            self.controller.monitor(new_metrics)
            result["metrics_recorded"] = len(new_metrics)

        # Analyze
        analysis = self.controller.analyze()
        result["analysis"] = analysis

        # Decide (using decision engine instead of simple plan)
        best_action = self.decide_action(analysis)

        if best_action:
            result["selected_action"] = {
                "type": best_action.type.value,
                "parameters": best_action.parameters,
                "rationale": best_action.rationale
            }

            # Execute
            action_ids = self.controller.execute([best_action])
            result["executed_action_id"] = action_ids[0] if action_ids else None
        else:
            result["selected_action"] = None

        result["new_state"] = {
            "chunk_size": self.controller.state.chunk_size,
            "chunk_overlap": self.controller.state.chunk_overlap,
            "retrieval_k": self.controller.state.retrieval_k
        }

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get bridge status including learned preferences."""
        return {
            "controller_state": {
                "chunk_size": self.controller.state.chunk_size,
                "chunk_overlap": self.controller.state.chunk_overlap,
                "strategy": self.controller.state.strategy
            },
            "learned_preferences": self.decisions.get_learned_weights(self.domain),
            "targets": {k.value: v for k, v in self.controller.targets.items()}
        }


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Feedback Bridge CLI')
    parser.add_argument('--status', action='store_true', help='Show bridge status')
    parser.add_argument('--cycle', action='store_true', help='Run decision-informed MAPE cycle')
    parser.add_argument('--decide', action='store_true', help='Show what action would be selected')

    args = parser.parse_args()
    bridge = FeedbackBridge()

    if args.status:
        status = bridge.get_status()
        print(json.dumps(status, indent=2))

    elif args.cycle:
        result = bridge.run_cycle()
        print(json.dumps(result, indent=2, default=str))

    elif args.decide:
        analysis = bridge.controller.analyze()
        action = bridge.decide_action(analysis)
        if action:
            print(f"Selected: {action.type.value}")
            print(f"Parameters: {json.dumps(action.parameters)}")
            print(f"Rationale: {action.rationale}")
        else:
            print("No action needed")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
