# Free API Models (OpenRouter)

Reference for free AI models available via OpenRouter API.
Source: https://openrouter.ai/models?max_price=0

## Free Models (as of 2026-01-27)

| Model | Context | Provider | Notes |
|-------|---------|----------|-------|
| **Google: Gemini 2.0 Flash Experimental** | 1.05M | Google | Expiring March 3, 2026. Faster TTFT, multimodal, agentic capabilities |
| **Meta: Llama 3.3 70B Instruct** | 131K | Meta | Multilingual (8 languages), optimized for dialogue |
| **Meta: Llama 3.2 3B Instruct** | 131K | Meta | Lightweight, 9T tokens training, tool use |
| **Qwen: Qwen2.5-VL 7B Instruct** | 33K | Qwen | Vision + language, 20min video understanding, agentic |
| **Nous: Hermes 3 405B Instruct** | 131K | Nous Research | Frontier-level, superior function calling, steering |
| **Meta: Llama 3.1 405B Instruct** | 131K | Meta | 128K context, competes with GPT-4o and Claude 3.5 |
| **Upstage: Solar Pro 3** | 128K | Upstage | 102B MoE (12B active), Korean/English/Japanese |

## Usage with OpenRouter

```python
import requests

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "google/gemini-2.0-flash-exp:free",  # Note: :free suffix
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
```

## Model IDs (for API calls)

- `google/gemini-2.0-flash-exp:free`
- `meta-llama/llama-3.3-70b-instruct:free`
- `meta-llama/llama-3.2-3b-instruct:free`
- `qwen/qwen-2.5-vl-7b-instruct:free`
- `nousresearch/hermes-3-llama-3.1-405b:free`
- `meta-llama/llama-3.1-405b-instruct:free`
- `upstage/solar-pro-3:free`

## Recommendations

| Use Case | Recommended Model |
|----------|-------------------|
| Fast inference | Gemini 2.0 Flash (lowest TTFT) |
| Long context | Gemini 2.0 Flash (1M context) |
| Multilingual | Llama 3.3 70B (8 languages) |
| Vision tasks | Qwen2.5-VL 7B |
| Complex reasoning | Llama 3.1 405B or Hermes 3 405B |
| Lightweight/Edge | Llama 3.2 3B |

## Integration Ideas

1. **Fallback routing**: Use free models as fallback when LocalAI times out
2. **Parallel processing**: Use free models for bulk extraction
3. **Cost optimization**: Route simple queries to free models, complex to paid

## Notes

- Free tier has rate limits (check OpenRouter docs)
- Some models expire (Gemini 2.0 Flash: March 3, 2026)
- `:free` suffix required for free tier access
