# Research Report: AI Pipeline Processing Speed Bottlenecks & Industry Solutions
Generated: 2026-01-24
## Summary
AI inference pipelines face three primary bottleneck categories: memory bandwidth (especially during LLM decode phase), GPU underutilization (30-50% typical), and serialization overhead. Industry solutions like vLLM PagedAttention achieve 85-92% GPU utilization through continuous batching, while TensorRT-LLM delivers 4x throughput improvements via kernel fusion and FP8 quantization.
## Questions Answered
### Q1: What are the common bottleneck types?
**Answer:** Memory bandwidth is the dominant bottleneck for LLM inference. The decode phase is memory-bound because it generates one token at a time, causing GPU cores to idle while waiting for memory fetches. GPU utilization typically hovers at 30-50%.
**Confidence:** High
### Q2: What industry solutions exist for continuous batching?
**Answer:** vLLM PagedAttention + continuous batching achieves 85-92% GPU utilization. Features include iteration-level scheduling, memory paging to prevent fragmentation, and 2-4x higher throughput than HuggingFace pipelines.
**Confidence:** High
### Q3: What profiling tools work for Python AI pipelines?
**Answer:** py-spy for low-overhead flame graphs, Scalene for line-level heatmaps, cProfile + flameprof for built-in profiling.
**Confidence:** High
### Q4: How should latency percentiles be monitored?
**Answer:** Track P50 (median), P95 (unlucky 5%), and P99 (near worst-case). Set SLOs around P95 for TTFT and P99 for total request latency.
**Confidence:** High
## Detailed Findings
### Finding 1: Memory Bandwidth as Primary Bottleneck
| Phase | Bound Type | Characteristic |
|-------|------------|----------------|
| Prefill | Compute-bound | Matrix multiplications parallelizable |
| Decode | Memory-bound | Sequential token generation, KV cache fetches |
| Data transfer | I/O-bound | CPU RAM to GPU DRAM transfers |
HBM4 (2025-2026) offers 2+ TB/s bandwidth, ~60% faster than HBM3E.
### Finding 2: vLLM Continuous Batching
Key configuration parameters:
- max_num_seqs: Concurrent sequences limit (higher = throughput, lower = latency)
- block_size: KV cache block size (16 typical)
- gpu_memory_utilization: 0.90 recommended
- enable_chunked_prefill: True for long prompts
### Finding 3: TensorRT-LLM Optimization
Quantization priority:
1. FP8 (Hopper/Blackwell) - best tradeoff
2. INT8 SmoothQuant (Ada fallback)
3. INT4 AWQ (memory-constrained)
H100 FP8 achieves >10,000 output tokens/sec, TTFT <100ms.
### Finding 4: ONNX Runtime Cross-Platform
Execution Provider priority: TensorRT EP -> CUDA EP -> CPU
3.8x faster inference for LLaMA-2 with fusion optimizations.
### Finding 5: Triton Inference Server
Dynamic batching config:
- preferred_batch_size: [8, 16, 32]
- max_queue_delay_microseconds: 100
- instance_group count: 2 (for memory transfer overlap)
WARNING: Default queue has no eviction - can accumulate unbounded backlog.
### Finding 6: Python Profiling Stack
py-spy commands:
- py-spy record -o profile.svg --pid PID (attach to running)
- py-spy record -o profile.svg -- python script.py (direct)
- py-spy record -f speedscope -o profile.json (interactive viewer)
Scalene: pip install scalene; scalene --html --outfile report.html script.py
### Finding 7: GPU Monitoring with DCGM
Key metrics:
- DCGM_FI_DEV_GPU_UTIL: GPU utilization %
- DCGM_FI_PROF_GR_ENGINE_ACTIVE: Compute engine active fraction
- DCGM_FI_PROF_SM_OCCUPANCY: Warp occupancy
- DCGM_FI_DEV_FB_USED: GPU memory used
- DCGM_FI_DEV_POWER_USAGE: Power in watts
Deploy: docker run -d --gpus all -p 9400:9400 nvcr.io/nvidia/k8s/dcgm-exporter
### Finding 8: Latency Percentile Monitoring
| Metric | What It Measures | Target |
|--------|------------------|--------|
| TTFT P95 | Time to first token | <100ms interactive |
| E2E P99 | End-to-end latency | SLA-dependent |
| Queue depth | Requests waiting | Low = healthy |
Use OpenTelemetry histograms for efficient percentile calculation.
## Comparison Matrix
### Inference Frameworks
| Framework | Best For | GPU Support | Complexity |
|-----------|----------|-------------|------------|
| vLLM | High-concurrency serving | NVIDIA, AMD | Low |
| TensorRT-LLM | Maximum NVIDIA perf | NVIDIA only | High |
| ONNX Runtime | Cross-platform | Multi-vendor | Medium |
| Triton Server | Multi-model | Multi-vendor | Medium |
### Profiling Tools
| Tool | Overhead | Flame Graph | Memory | GPU |
|------|----------|-------------|--------|-----|
| py-spy | Very low | Yes | No | No |
| Scalene | Low | Heatmap | Yes | No |
| DCGM | Negligible | No | Yes | Yes |
## Recommendations
1. Add GPU metrics collection - Deploy DCGM-exporter, scrape with Prometheus
2. Implement percentile tracking - OpenTelemetry histograms for TTFT, latency
3. Profile before optimizing - py-spy on daemon workers
4. Consider vLLM - PagedAttention provides immediate gains
## Sources
1. https://www.sdxcentral.com/news/ai-inference-crisis-google-engineers-on-why-network-latency-and-memory-trump-compute/
2. https://www.clarifai.com/blog/llm-inference-optimization/
3. https://docs.vllm.ai/en/latest/
4. https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html
5. https://github.com/NVIDIA/TensorRT-LLM
6. https://developer.nvidia.com/blog/llm-inference-benchmarking-performance-tuning-with-tensorrt-llm/
7. https://onnxruntime.ai/
8. https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/optimization.html
9. https://github.com/benfred/py-spy
10. https://github.com/NVIDIA/dcgm-exporter
11. https://bentoml.com/llm/inference-optimization/llm-inference-metrics
12. https://oneuptime.com/blog/post/2025-09-15-p50-vs-p95-vs-p99-latency-percentiles/view
