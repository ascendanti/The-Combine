# Local Deployment Guide - Claude Cognitive System

*Run this build locally on a $2K CAD PC with voice + hologram*

---

## Hardware Requirements ($2K CAD Budget)

### Recommended Build

| Component | Spec | Price (CAD) |
|-----------|------|-------------|
| **CPU** | AMD Ryzen 7 7800X3D or Intel i7-14700K | $450-500 |
| **GPU** | RTX 4070 Super (12GB VRAM) | $700-800 |
| **RAM** | 64GB DDR5-5600 | $200-250 |
| **Storage** | 2TB NVMe SSD | $150-180 |
| **PSU** | 750W 80+ Gold | $100-120 |
| **Case** | Mid-tower with good airflow | $80-100 |
| **Motherboard** | B650/Z790 | $150-200 |
| **Total** | | **~$1,850-2,150** |

### Why This Spec?
- **GPU:** 12GB VRAM runs Mistral 7B, Whisper, Piper locally
- **RAM:** 64GB for multiple models + Docker containers
- **CPU:** Fast single-thread for Claude Code CLI
- **Storage:** Fast NVMe for model loading

---

## Software Stack

### Core System (Already Built)

```
┌─────────────────────────────────────────┐
│         Claude Code CLI (Claude)        │
├─────────────────────────────────────────┤
│    LocalAI     │ Dragonfly │ PostgreSQL │
│  (Mistral 7B)  │  (Cache)  │   (Data)   │
├─────────────────────────────────────────┤
│  Docker Compose - 5 Containers          │
└─────────────────────────────────────────┘
```

### Voice System (To Add)

| Component | Purpose | Model |
|-----------|---------|-------|
| **Whisper** | Speech-to-text | whisper-large-v3 |
| **Piper** | Text-to-speech | en_US-ryan-high |
| **VAD** | Voice activity detection | Silero VAD |

### Hologram System (Options)

| Option | Cost | Quality | Complexity |
|--------|------|---------|------------|
| **Looking Glass Portrait** | $400 CAD | Excellent | Low |
| **Pepper's Ghost DIY** | $50-100 | Good | Medium |
| **AR Glasses (Xreal Air)** | $500 CAD | Excellent | Medium |
| **Projector + Mesh** | $300 CAD | Good | High |

---

## Installation Steps

### Step 1: Base System

```bash
# Install Docker Desktop for Windows
winget install Docker.DockerDesktop

# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Clone this repo
git clone <repo-url> claude-cognitive
cd claude-cognitive
```

### Step 2: Start Docker Services

```bash
# Start all containers
docker-compose up -d

# Verify
docker ps
# Should see: localai, dragonfly, postgres, workers
```

### Step 3: Configure Claude Code

```bash
# Set API key
claude config set apiKey YOUR_ANTHROPIC_KEY

# Point to local services
claude config set localAI.endpoint http://localhost:8080/v1
```

### Step 4: Add Voice (Whisper + Piper)

```yaml
# Add to docker-compose.yaml
  whisper:
    image: onerahmet/openai-whisper-asr-webservice:latest
    ports:
      - "9000:9000"
    environment:
      - ASR_MODEL=large-v3
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  piper:
    image: rhasspy/piper:latest
    ports:
      - "5000:5000"
    volumes:
      - ./piper-voices:/data
```

### Step 5: Voice Interface Script

```python
# daemon/voice_interface.py
import sounddevice as sd
import requests
import numpy as np
from scipy.io import wavfile

WHISPER_URL = "http://localhost:9000/asr"
PIPER_URL = "http://localhost:5000/api/tts"

def listen():
    """Record until silence detected."""
    print("Listening...")
    audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1)
    sd.wait()
    return audio

def transcribe(audio):
    """Send to Whisper."""
    wavfile.write("/tmp/audio.wav", 16000, audio)
    with open("/tmp/audio.wav", "rb") as f:
        response = requests.post(WHISPER_URL, files={"audio_file": f})
    return response.json()["text"]

def speak(text):
    """Send to Piper TTS."""
    response = requests.post(PIPER_URL, json={"text": text})
    audio = np.frombuffer(response.content, dtype=np.int16)
    sd.play(audio, samplerate=22050)
    sd.wait()

def main():
    while True:
        audio = listen()
        text = transcribe(audio)
        print(f"You: {text}")

        # Send to Claude
        response = subprocess.run(
            ["claude", "-p", text],
            capture_output=True, text=True
        )
        answer = response.stdout
        print(f"Claude: {answer}")
        speak(answer)

if __name__ == "__main__":
    main()
```

### Step 6: Hologram Setup (Looking Glass)

```bash
# Install Looking Glass drivers
# Download from: https://lookingglassfactory.com/software

# Create hologram avatar
pip install looking-glass-sdk

# daemon/hologram_avatar.py
from lookinglass import LookingGlass
from avatar_generator import generate_face_mesh

class HologramAvatar:
    def __init__(self):
        self.display = LookingGlass()
        self.mesh = generate_face_mesh("assistant")

    def animate_speaking(self, audio_data):
        """Lip sync animation from audio."""
        phonemes = extract_phonemes(audio_data)
        for phoneme in phonemes:
            self.mesh.set_mouth_shape(phoneme)
            self.display.render(self.mesh)

    def set_emotion(self, emotion):
        """Change facial expression."""
        self.mesh.set_expression(emotion)
        self.display.render(self.mesh)
```

---

## Full Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    VOICE INTERFACE                       │
│  Microphone → Whisper → Text → Claude → Piper → Speaker │
├─────────────────────────────────────────────────────────┤
│                   HOLOGRAM DISPLAY                       │
│  Avatar Mesh → Lip Sync → Looking Glass/AR Glasses      │
├─────────────────────────────────────────────────────────┤
│                   CLAUDE COGNITIVE                       │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐              │
│  │ LocalAI │  │ Memory   │  │ Strategies│              │
│  │ Mistral │  │ KG + DB  │  │ Evolution │              │
│  └─────────┘  └──────────┘  └───────────┘              │
├─────────────────────────────────────────────────────────┤
│                     DOCKER                               │
│  localai │ dragonfly │ postgres │ workers │ whisper    │
└─────────────────────────────────────────────────────────┘
```

---

## Performance Expectations

| Task | Local (RTX 4070) | API (Claude) |
|------|------------------|--------------|
| Summarization | 50 tok/s | N/A |
| Embedding | 1000 docs/min | N/A |
| Voice STT | Real-time | N/A |
| Voice TTS | Real-time | N/A |
| Complex reasoning | Route to API | 100 tok/s |
| Token cost | $0 local | $15/M Opus |

---

## Cost Comparison

| Scenario | Cloud-Only | Hybrid (This Build) |
|----------|------------|---------------------|
| Hardware | $0 | $2,000 (one-time) |
| Monthly API | $500+ | $50-100 |
| Annual Cost | $6,000+ | $600-1,200 + amortized HW |
| 3-Year Total | $18,000+ | $4,400-5,600 |

**Savings:** 70-80% over 3 years

---

## Quick Start Checklist

- [ ] Order PC components
- [ ] Install Windows 11 Pro
- [ ] Install Docker Desktop
- [ ] Install Claude Code CLI
- [ ] Clone repo, run `docker-compose up`
- [ ] Test LocalAI endpoint
- [ ] Add Whisper container
- [ ] Add Piper container
- [ ] Test voice interface
- [ ] Order Looking Glass Portrait (optional)
- [ ] Setup hologram avatar

---

## Upgrade Path

### Phase 1: Basic ($2K)
- RTX 4070 + 64GB RAM
- LocalAI, Whisper, Piper
- Voice interface working

### Phase 2: Enhanced ($3K total)
- Add Looking Glass Portrait ($400)
- Better microphone ($100)
- Second monitor for dashboard

### Phase 3: Premium ($5K total)
- RTX 4090 (24GB VRAM)
- Larger models (34B params)
- AR glasses (Xreal Air 2)
- Smart home integration

---

*Generated: 2026-01-24*
