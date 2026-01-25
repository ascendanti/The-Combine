# Rumsfeld Matrix: Sci-Fi Plan Uncertainty Analysis

*Known Knowns, Known Unknowns, Unknown Knowns, Unknown Unknowns*

---

## Known Knowns
*Things we know we know - Certain capabilities and facts*

### Infrastructure (Verified Working)
| Component | Location | Status | Evidence |
|-----------|----------|--------|----------|
| LocalAI + Mistral 7B | Docker | Running | API responds, 4.1GB model loaded |
| Dragonfly Cache | Docker | Running | 41+ keys cached |
| PostgreSQL | Docker | Running | Tables populated |
| Knowledge Graph MCP | Global | Active | Entities stored |
| 5 Docker Containers | docker-compose | Healthy | `docker ps` confirms |

### Built Modules (Code Verified)
| Module | Status | Lines | Key Functions |
|--------|--------|-------|---------------|
| outcome_tracker.py | Complete | 450+ | record, query, patterns |
| strategy_evolution.py | Complete | 700+ | evolve, mutate, crossover |
| strategy_ops.py | Complete | 600+ | deploy, measure, drift |
| self_continue.py | Complete | 350+ | checkpoint, resume, queue |
| task_generator.py | Complete | 400+ | 9 detectors, approve/reject |
| local_autorouter.py | Complete | 500+ | route, classify, optimize |
| core/base.py | Complete | 300+ | Signal, Action, Outcome, Learning |
| core/bus.py | Complete | 250+ | publish, subscribe, persist |
| bisimulation.py | Complete | 400+ | state abstraction, transfer |
| gcrl.py | Complete | 350+ | HER, trajectory, causal |
| claim_similarity.py | Complete | 300+ | find_similar, clusters |
| utf_extractor.py | Complete | 500+ | claims, concepts, excerpts |

### Integration Points (Tested)
- Telegram → Claude bridge works
- Hooks fire correctly (SessionStart, PreToolUse, PostToolUse)
- model_router.py routes to LocalAI successfully
- UTF pipeline processes PDFs end-to-end

---

## Known Unknowns
*Things we know we don't know - Identified risks and gaps*

### Performance Questions
| Question | Impact | How to Resolve |
|----------|--------|----------------|
| LocalAI throughput limit? | Bottleneck capacity | Load test with 100 concurrent requests |
| Dragonfly cache hit rate? | Token savings actual | Add hit/miss logging |
| PostgreSQL query latency? | Memory tier viability | Benchmark with 10K rows |
| Bisimulation distance accuracy? | Transfer quality | Validate with known-similar states |

### Integration Unknowns
| Gap | Risk | Resolution Path |
|-----|------|-----------------|
| GCRL → decisions.py wiring | Learning not activated | 4 integration points identified |
| Message bus adoption | Components not communicating | Retrofit existing modules |
| Voice (Whisper) quality | Unusable if poor | Test with domain vocabulary |
| Calendar API OAuth | Permission denied | Test Google Calendar API flow |

### Scaling Unknowns
| Question | Impact | Experiment Needed |
|----------|--------|-------------------|
| Multi-instance coordination? | Distributed viability | Deploy 2 instances, test sync |
| Edge deployment latency? | Geographic distribution | Deploy to Fly.io, measure |
| Federated learning convergence? | Collective learning | Simulate with synthetic data |

### User Adoption Unknowns
| Question | Impact | How to Learn |
|----------|--------|--------------|
| Voice vs text preference? | UI direction | A/B test with user |
| Notification tolerance? | Proactive features | Track dismiss rate |
| Trust for autonomous actions? | Autonomy level | Gradual permission expansion |

---

## Unknown Knowns
*Things we don't know we know - Latent capabilities not recognized*

### Existing But Underutilized
| Capability | Location | Current Use | Potential |
|------------|----------|-------------|-----------|
| Bisimulation state matching | bisimulation.py | 0% | 100x learning speedup |
| GCRL hindsight learning | gcrl.py | 0% | Turn failures into training |
| Causal factor extraction | gcrl.py | 0% | Root cause identification |
| Claim similarity clustering | claim_similarity.py | 5% | Cross-paper synthesis |
| Strategy A/B testing | strategy_evolution.py | 0% | Statistically valid optimization |
| MAPE control loop | controller.py | 10% | Self-optimization |
| UTF closeness scoring | memory.py | 5% | Semantic search |
| Token spike detection | token_monitor.py | 20% | Automatic optimization |

### Emergent Capabilities (Not Designed But Present)
| Capability | Source | How It Emerges |
|------------|--------|----------------|
| Contradiction detection | claim_similarity + utf_extractor | Compare claims with opposite sentiment |
| Trend prediction | outcome_tracker + time-series | Pattern extrapolation from history |
| Goal inference | coherence + gcrl | What goals explain this trajectory? |
| Skill gaps | task_generator + metacognition | What tasks fail that should succeed? |
| Network effects | knowledge-graph traversal | Insight compounds as graph grows |

### Transferable Patterns
| Pattern | Exists In | Applicable To |
|---------|-----------|---------------|
| Fitness scoring | strategy_evolution.py | Any optimization problem |
| Drift detection | strategy_ops.py | Any metric tracking |
| Similarity clustering | claim_similarity.py | Any embeddings |
| Checkpoint/resume | self_continue.py | Any long-running process |
| Priority queue | task_generator.py | Any task system |

---

## Unknown Unknowns
*Things we don't know we don't know - Blind spots and surprises*

### Potential Failure Modes (Speculative)
| Category | Examples | Mitigation Strategy |
|----------|----------|---------------------|
| Emergent misbehavior | Optimization finds exploits, feedback loops destabilize | Add coherence checks, rate limiters |
| Integration conflicts | Modules interfere unexpectedly | Isolate with message bus |
| Resource exhaustion | Memory leaks, disk fills | Add monitoring and alerts |
| API changes | External services break | Abstract behind interfaces |
| Security gaps | Prompt injection, data leakage | Security audit, sandboxing |

### Unknown User Needs
| Category | Examples |
|----------|----------|
| Workflows not anticipated | User has needs we haven't imagined |
| Domain-specific requirements | Business rules we don't know exist |
| Integration points | Systems they want to connect |
| Privacy requirements | Data that can't be processed |

### Unknown Technical Limits
| Category | Examples |
|----------|----------|
| Model capability cliffs | Where do models fail catastrophically? |
| Embedding space limits | When does similarity break down? |
| Coordination overhead | At what scale does distribution hurt? |
| Latency thresholds | What response time is unacceptable? |

### Discovery Strategies
| Strategy | Purpose | Implementation |
|----------|---------|----------------|
| Chaos engineering | Find unknown failure modes | Random fault injection |
| User observation | Find unknown needs | Log all interactions, analyze |
| Fuzzing | Find unknown inputs | Random input generation |
| Red team | Find unknown security gaps | Adversarial testing |
| A/B everything | Find unknown preferences | Experiment by default |

---

## Converting Unknowns to Knowns

### This Week: Known Unknowns → Known Knowns
```
Performance questions:
├── Run LocalAI load test → Know throughput limit
├── Add cache hit logging → Know actual savings
├── Benchmark PostgreSQL → Know query latency
└── Test bisimulation accuracy → Know transfer quality

Integration questions:
├── Wire GCRL → decisions → Know if learning works
├── Add message bus to 3 modules → Know adoption friction
└── Test Whisper with domain vocab → Know voice viability
```

### This Month: Unknown Knowns → Known Knowns
```
Activate latent capabilities:
├── Wire bisimulation to production → Unlock 100x learning
├── Enable A/B testing → Get statistically valid results
├── Run MAPE daemon continuously → Enable self-optimization
└── Use cross-paper synthesis → Generate novel insights
```

### Ongoing: Unknown Unknowns → Known Unknowns
```
Discovery processes:
├── Chaos engineering weekly → Surface hidden failures
├── User session analysis → Find unknown needs
├── Security fuzzing monthly → Find unknown vulnerabilities
└── Metric anomaly alerts → Detect unknown behaviors
```

---

## Risk-Adjusted Priority

| Capability | Known Knowns | Known Unknowns | Unknown Unknowns | Risk Score | Priority |
|------------|--------------|----------------|------------------|------------|----------|
| Wire bisimulation | High (built) | Low (clear path) | Low | 2/10 | **1** |
| Enable GCRL learning | High (built) | Low (clear path) | Low | 2/10 | **1** |
| Cross-paper synthesis | High (data exists) | Medium (quality?) | Low | 3/10 | **2** |
| Voice interface | Medium (libs exist) | Medium (quality) | Medium | 5/10 | **3** |
| Multi-instance | Low (design only) | High (coordination) | High | 7/10 | **4** |
| Federated learning | Low (concept only) | High (convergence) | High | 8/10 | **5** |

---

*Reduce unknowns by experimenting, not by assuming.*

*Generated: 2026-01-24*
