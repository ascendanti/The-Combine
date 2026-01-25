# Research Report: Minimizing Claude Thinking Overhead Through Architecture
Generated: 2026-01-24T02:43:10

## Summary

This research identifies three architectural strategies for reducing Claude thinking token overhead: (1) function memoization with semantic caching that can cut costs by 60-90%, (2) model routing that directs simple tasks to cheaper models achieving 30-85% cost reduction, and (3) structured plan formats using markdown schemas that enable efficient parsing and machine-readable validation.

## Questions Answered

### Q1: How can iterated functions be cached/memoized for LLM contexts?
**Answer:** LLM prompt caching stores pre-computed KV-cache tensors for identical prompt prefixes. When the cache hits, processing skips redundant computation. Combined with semantic hashing for similar (not identical) prompts, this achieves 60-90% cost reduction.
**Source:** ngrok Prompt Caching Blog
**Confidence:** High

### Q2: What model routing patterns exist for cost optimization?
**Answer:** RouteLLM and similar frameworks use classifiers to route queries to appropriate model tiers. Simple queries go to cheap models (Haiku/GPT-3.5), complex queries to expensive models (Opus/GPT-4). This achieves 30-85% cost reduction while maintaining 95% quality.
**Source:** LMSYS RouteLLM
**Confidence:** High

### Q3: What structured plan formats work best for LLMs?
**Answer:** Markdown with hierarchical headers is optimal - lightweight, human-readable, and machine-parsable. For complex nested structures, XML provides explicit demarcation. The plan.md format offers a schema for structured plans.
**Source:** Wetrocloud Markdown for LLMs
**Confidence:** High

### Q4: How does speculative execution work in agentic workflows?
**Answer:** The Sherlock framework overlaps verification and computation - launching child tasks speculatively while parent verification runs in background. If verification fails, speculative results are rolled back. Achieves 48.7% latency reduction.
**Source:** Sherlock Paper (arxiv)
**Confidence:** Medium

---

## Detailed Findings

### Finding 1: Prompt/Function Caching Architecture

**Key Points:**
- KV-cache memoization stores computed attention tensors for reuse
- Complexity drops from O(n squared) to O(n) per token with caching
- AWS Bedrock reports up to 85% latency reduction
- Claude API has native 5-minute TTL caching for prompt prefixes

**Architecture Pattern:**
Request Router:
  1. Hash prompt prefix -> Check cache
  2. Cache HIT -> Return cached KV tensors
  3. Cache MISS -> Compute, store, return

### Finding 2: Pure Function Extraction Pattern

**Key Points:**
- Extract generalized reasoning patterns (methods) from LLM outputs
- Methods are stored structurally and reused across sessions
- Captures entire solution strategies, not just single steps
- Enables method transfer and modular composition

**Extraction Rules:**
1. Identify pure operations: No external state reads/writes
2. Extract input signature: All inputs must be explicit parameters
3. Verify determinism: Same inputs must produce same outputs
4. Define cache key: Hash of (function_name, sorted_inputs)

### Finding 3: Model Routing Architecture

**Tiered Model Strategy:**
| Tier     | Use Case                    | Model              | Cost |
|----------|-----------------------------|--------------------|------|
| Free     | Bulk ops, embeddings        | LocalAI/Mistral-7B | /usr/bin/bash   |
| Cheap    | Simple code, classification | GPT-4o-mini/Haiku  | $    |
| Standard | General tasks               | Sonnet             | 52974   |
| Premium  | Complex reasoning           | Opus               | 52974$  |

**Key Points:**
- Routes queries to appropriate model tier before execution
- Trained routers achieve same performance at 40-85% lower cost
- Three methods: preference-based, similarity-based, threshold-based

### Finding 4: Speculative Execution with Rollback

**Architecture:**
1. Fast model predicts next N actions
2. Execute speculatively in sandbox
3. Slow model verifies in parallel
4. If verified -> commit results
5. If failed -> rollback, use slow model result

**Safety Constraints:**
- Only speculate on idempotent or reversible operations
- Maintain rollback state for all speculative changes
- Semantic guards verify state equivalence before commit

### Finding 5: Extended Thinking Budget Optimization

**Key Points:**
- Minimum thinking budget: 1,024 tokens
- Thinking tokens billed as output tokens
- Start minimal, increase for complex tasks
- Batch processing recommended for 32k+ budgets
- Thinking block clearing (beta) auto-removes old blocks

**Budget Strategy:**
- simple_lookup: 0 (disable thinking)
- classification: 1024 (minimum)
- code_generation: 8192 (standard)
- architecture: 16384 (complex)
- multi_step_reasoning: 32000 (maximum practical)

---

## Comparison Matrix

| Strategy               | Cost Reduction | Latency Impact | Complexity |
|------------------------|----------------|----------------|------------|
| Prompt Caching         | 60-90%         | -85% latency   | Low        |
| Model Routing          | 30-85%         | Variable       | Medium     |
| Thinking Budget Tuning | 15-40%         | Proportional   | Low        |
| Speculative Execution  | 0%             | -48% latency   | High       |
| Structured Plans       | 10-20%         | Neutral        | Low        |
| Pure Function Extract  | 20-50%         | -30% latency   | Medium     |

---

## Recommendations For This Codebase

1. **Extend model_router.py with Thinking Budget Control**
   - Add thinking_budget parameter to RoutingDecision
   - Map task complexity to budget tiers
   - Track thinking token usage in stats

2. **Implement Semantic Caching Layer**
   - Use existing Dragonfly integration
   - Add embedding-based similarity for near-miss cache hits
   - Cache pure function results

3. **Adopt Structured Plan Format**
   - Use markdown schema for task.md
   - Enable machine validation of plans
   - Track token budgets per phase

4. **Add Thinking Block Clearing**
   - Enable context-management-2025-06-27 beta
   - Auto-clear older thinking blocks

---

## Sources

1. https://platform.claude.com/docs/en/build-with-claude/extended-thinking
2. https://ngrok.com/blog/prompt-caching/
3. https://lmsys.org/blog/2024-07-01-routellm/
4. https://arxiv.org/pdf/2510.04371
5. https://arxiv.org/pdf/2511.00330
6. https://medium.com/@wetrocloud/why-markdown-is-the-best-format-for-llms-aa0514a409a7
7. https://github.com/Digital-Tvilling/plan.md
8. https://arxiv.org/html/2508.04289v1
9. https://research.ibm.com/blog/LLM-routers
10. https://futureagi.com/blogs/llm-cost-optimization-2025
