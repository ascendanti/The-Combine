#!/usr/bin/env python3
"""
Freqtrade Bridge - Integration layer for algorithmic trading module.

Connects freqtrade to the Claude cognitive architecture for:
1. Strategy optimization via decision engine
2. Market analysis via knowledge graph
3. Risk assessment via metacognition
4. Learning from trade outcomes

Usage:
    python freqtrade_bridge.py --status     # Show freqtrade status
    python freqtrade_bridge.py --analyze    # Analyze recent trades with KG
    python freqtrade_bridge.py --optimize   # Suggest strategy improvements
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

# Import cognitive modules
try:
    from decisions import DecisionEngine, DecisionCriteria, DecisionOption
    DECISIONS_AVAILABLE = True
except ImportError:
    DECISIONS_AVAILABLE = False

try:
    from metacognition import MetaCognition
    METACOGNITION_AVAILABLE = True
except ImportError:
    METACOGNITION_AVAILABLE = False

try:
    from coherence import GoalCoherence
    COHERENCE_AVAILABLE = True
except ImportError:
    COHERENCE_AVAILABLE = False

# ============================================================================
# Configuration
# ============================================================================

FREQTRADE_PATH = Path(__file__).parent.parent / "modules" / "freqtrade"
DB_PATH = Path(__file__).parent / "trading.db"

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TradeSignal:
    """Signal from freqtrade strategy."""
    signal_id: str
    pair: str
    signal_type: str  # buy, sell, hold
    confidence: float
    strategy: str
    indicators: Dict[str, float]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class TradeOutcome:
    """Outcome of a trade for learning."""
    trade_id: str
    pair: str
    entry_price: float
    exit_price: float
    profit_pct: float
    duration_hours: float
    strategy: str
    market_conditions: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class StrategyAssessment:
    """Assessment of strategy performance."""
    strategy: str
    win_rate: float
    avg_profit: float
    max_drawdown: float
    sharpe_ratio: float
    confidence_calibration: float  # How well predicted confidence matches outcomes
    recommendations: List[str]

# ============================================================================
# Database
# ============================================================================

def init_db():
    """Initialize trading database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_signals (
            signal_id TEXT PRIMARY KEY,
            pair TEXT,
            signal_type TEXT,
            confidence REAL,
            strategy TEXT,
            indicators TEXT,
            timestamp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_outcomes (
            trade_id TEXT PRIMARY KEY,
            pair TEXT,
            entry_price REAL,
            exit_price REAL,
            profit_pct REAL,
            duration_hours REAL,
            strategy TEXT,
            market_conditions TEXT,
            timestamp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strategy_assessments (
            strategy TEXT PRIMARY KEY,
            win_rate REAL,
            avg_profit REAL,
            max_drawdown REAL,
            sharpe_ratio REAL,
            confidence_calibration REAL,
            recommendations TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()

# ============================================================================
# Bridge Functions
# ============================================================================

class FreqtradeBridge:
    """Bridge between freqtrade and Claude cognitive architecture."""

    def __init__(self):
        init_db()
        self.decisions = DecisionEngine() if DECISIONS_AVAILABLE else None
        self.metacognition = MetaCognition() if METACOGNITION_AVAILABLE else None
        self.coherence = GoalCoherence() if COHERENCE_AVAILABLE else None

    def evaluate_signal(self, signal: TradeSignal) -> Dict[str, Any]:
        """
        Evaluate a trade signal using the decision engine.

        Returns recommendation with confidence and risk assessment.
        """
        if not self.decisions:
            return {"recommendation": "proceed", "reason": "Decision engine not available"}

        # Create decision criteria based on trading goals
        criteria = [
            DecisionCriteria("profit_potential", 0.3, "higher_better"),
            DecisionCriteria("risk_level", 0.25, "lower_better"),
            DecisionCriteria("confidence", 0.25, "higher_better"),
            DecisionCriteria("market_alignment", 0.2, "higher_better")
        ]

        # Create options: execute trade or wait
        options = [
            DecisionOption(
                "execute",
                f"Execute {signal.signal_type} on {signal.pair}",
                {
                    "profit_potential": signal.confidence * 0.8,
                    "risk_level": 1 - signal.confidence,
                    "confidence": signal.confidence,
                    "market_alignment": self._assess_market_alignment(signal)
                }
            ),
            DecisionOption(
                "wait",
                "Wait for better opportunity",
                {
                    "profit_potential": 0.3,
                    "risk_level": 0.1,
                    "confidence": 0.9,
                    "market_alignment": 0.5
                }
            )
        ]

        result = self.decisions.evaluate("trade_signal", criteria, options)

        # Store signal for learning
        self._store_signal(signal)

        return {
            "recommendation": result["best_option"],
            "score": result["score"],
            "reasoning": result.get("explanation", ""),
            "risk_assessment": self._assess_risk(signal)
        }

    def _assess_market_alignment(self, signal: TradeSignal) -> float:
        """Assess how well signal aligns with market conditions."""
        # Placeholder - would integrate with market analysis
        return signal.confidence * 0.9

    def _assess_risk(self, signal: TradeSignal) -> Dict[str, Any]:
        """Assess risk of trade using metacognition."""
        if not self.metacognition:
            return {"level": "unknown", "factors": []}

        # Check confidence calibration for this strategy
        calibration = self.metacognition.get_calibration(f"trading_{signal.strategy}")

        risk_factors = []
        if signal.confidence > 0.8 and calibration.get("overconfident", False):
            risk_factors.append("Strategy tends to be overconfident")

        if signal.confidence < 0.5:
            risk_factors.append("Low signal confidence")

        return {
            "level": "high" if len(risk_factors) > 1 else "medium" if risk_factors else "low",
            "factors": risk_factors,
            "calibration": calibration
        }

    def _store_signal(self, signal: TradeSignal):
        """Store signal in database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO trade_signals
            (signal_id, pair, signal_type, confidence, strategy, indicators, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.signal_id, signal.pair, signal.signal_type,
            signal.confidence, signal.strategy,
            json.dumps(signal.indicators), signal.timestamp
        ))
        conn.commit()
        conn.close()

    def record_outcome(self, outcome: TradeOutcome):
        """Record trade outcome for learning."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO trade_outcomes
            (trade_id, pair, entry_price, exit_price, profit_pct,
             duration_hours, strategy, market_conditions, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            outcome.trade_id, outcome.pair, outcome.entry_price,
            outcome.exit_price, outcome.profit_pct, outcome.duration_hours,
            outcome.strategy, json.dumps(outcome.market_conditions),
            outcome.timestamp
        ))
        conn.commit()
        conn.close()

        # Update decision engine with outcome
        if self.decisions:
            satisfaction = 1.0 if outcome.profit_pct > 0 else 0.0
            self.decisions.record_outcome(
                f"trade_{outcome.trade_id}",
                "execute" if outcome.profit_pct != 0 else "wait",
                satisfaction
            )

        # Update metacognition calibration
        if self.metacognition:
            self.metacognition.record_prediction(
                f"trading_{outcome.strategy}",
                predicted_confidence=0.7,  # Would come from original signal
                actual_success=outcome.profit_pct > 0
            )

    def analyze_strategy(self, strategy: str) -> StrategyAssessment:
        """Analyze strategy performance and generate recommendations."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM trade_outcomes WHERE strategy = ?
            ORDER BY timestamp DESC LIMIT 100
        """, (strategy,))

        outcomes = cursor.fetchall()
        conn.close()

        if not outcomes:
            return StrategyAssessment(
                strategy=strategy,
                win_rate=0.0, avg_profit=0.0, max_drawdown=0.0,
                sharpe_ratio=0.0, confidence_calibration=0.0,
                recommendations=["No trade history available"]
            )

        # Calculate metrics
        profits = [r["profit_pct"] for r in outcomes]
        wins = sum(1 for p in profits if p > 0)

        win_rate = wins / len(profits)
        avg_profit = sum(profits) / len(profits)
        max_drawdown = min(profits) if profits else 0

        # Simple Sharpe approximation
        import statistics
        if len(profits) > 1:
            sharpe = avg_profit / statistics.stdev(profits) if statistics.stdev(profits) > 0 else 0
        else:
            sharpe = 0

        # Get calibration from metacognition
        calibration = 0.5
        if self.metacognition:
            cal_data = self.metacognition.get_calibration(f"trading_{strategy}")
            calibration = cal_data.get("calibration_score", 0.5)

        # Generate recommendations
        recommendations = []
        if win_rate < 0.5:
            recommendations.append("Win rate below 50% - review entry conditions")
        if avg_profit < 0:
            recommendations.append("Negative average profit - tighten stop losses")
        if max_drawdown < -10:
            recommendations.append("Large drawdown detected - reduce position sizes")
        if calibration < 0.4:
            recommendations.append("Poor confidence calibration - adjust signal thresholds")

        if not recommendations:
            recommendations.append("Strategy performing within acceptable parameters")

        return StrategyAssessment(
            strategy=strategy,
            win_rate=win_rate,
            avg_profit=avg_profit,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            confidence_calibration=calibration,
            recommendations=recommendations
        )

    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get strategy optimization suggestions based on learning."""
        suggestions = []

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all strategies
        cursor.execute("SELECT DISTINCT strategy FROM trade_outcomes")
        strategies = [r["strategy"] for r in cursor.fetchall()]
        conn.close()

        for strategy in strategies:
            assessment = self.analyze_strategy(strategy)
            if assessment.recommendations:
                suggestions.append({
                    "strategy": strategy,
                    "win_rate": assessment.win_rate,
                    "avg_profit": assessment.avg_profit,
                    "recommendations": assessment.recommendations
                })

        return suggestions


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Freqtrade Bridge")
    parser.add_argument("--status", action="store_true", help="Show freqtrade status")
    parser.add_argument("--analyze", help="Analyze strategy performance")
    parser.add_argument("--optimize", action="store_true", help="Get optimization suggestions")
    parser.add_argument("--test-signal", action="store_true", help="Test signal evaluation")

    args = parser.parse_args()

    bridge = FreqtradeBridge()

    if args.status:
        print(f"Freqtrade path: {FREQTRADE_PATH}")
        print(f"Module exists: {FREQTRADE_PATH.exists()}")
        print(f"Decision engine: {'Available' if DECISIONS_AVAILABLE else 'Not available'}")
        print(f"Metacognition: {'Available' if METACOGNITION_AVAILABLE else 'Not available'}")
        print(f"Coherence: {'Available' if COHERENCE_AVAILABLE else 'Not available'}")

    elif args.analyze:
        assessment = bridge.analyze_strategy(args.analyze)
        print(f"\nStrategy: {assessment.strategy}")
        print(f"Win Rate: {assessment.win_rate:.1%}")
        print(f"Avg Profit: {assessment.avg_profit:.2f}%")
        print(f"Max Drawdown: {assessment.max_drawdown:.2f}%")
        print(f"Sharpe Ratio: {assessment.sharpe_ratio:.2f}")
        print(f"Confidence Calibration: {assessment.confidence_calibration:.2f}")
        print(f"\nRecommendations:")
        for rec in assessment.recommendations:
            print(f"  - {rec}")

    elif args.optimize:
        suggestions = bridge.get_optimization_suggestions()
        if not suggestions:
            print("No optimization suggestions (no trade history)")
        else:
            print("\nOptimization Suggestions:\n")
            for s in suggestions:
                print(f"Strategy: {s['strategy']}")
                print(f"  Win Rate: {s['win_rate']:.1%}, Avg Profit: {s['avg_profit']:.2f}%")
                for rec in s['recommendations']:
                    print(f"  - {rec}")
                print()

    elif args.test_signal:
        # Test with a sample signal
        signal = TradeSignal(
            signal_id="test_001",
            pair="BTC/USDT",
            signal_type="buy",
            confidence=0.75,
            strategy="test_strategy",
            indicators={"rsi": 35, "macd": 0.5, "volume": 1.2}
        )
        result = bridge.evaluate_signal(signal)
        print(f"\nSignal Evaluation:")
        print(f"  Recommendation: {result['recommendation']}")
        print(f"  Score: {result.get('score', 'N/A')}")
        print(f"  Risk Level: {result['risk_assessment']['level']}")
        if result['risk_assessment']['factors']:
            print(f"  Risk Factors: {result['risk_assessment']['factors']}")


if __name__ == "__main__":
    main()
