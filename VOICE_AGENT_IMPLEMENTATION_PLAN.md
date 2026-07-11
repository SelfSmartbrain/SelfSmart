# ModelX Terminal Voice Agent - Implementation Plan

## Overview
Create a standalone, downloadable voice agent that runs in terminal with pre-built voices, requiring only LLM API key configuration.

**Vision**: A plug-and-play voice experience where users install, add API key, and start talking immediately.

**Key Features**:
- 🎤 Real-time voice interaction
- 🧠 Multiple LLM provider support
- 🔊 Pre-built natural voices (no download needed)
- 💻 Beautiful terminal interface
- 🔄 Conversation memory
- 📦 One-line installation

---

## Phase 1: Core Voice Infrastructure (Week 1-2)

### 1.1 Terminal Voice Interface Architecture

**Components:**
```
Terminal Voice Agent
├── Audio Input Layer
│   ├── Microphone capture (real-time)
│   ├── Voice Activity Detection (VAD)
│   └── Audio buffer management
├── Speech-to-Text (STT)
│   ├── Whisper.cpp (local, fast)
│   ├── Fallback to cloud STT
│   └── Streaming transcription
├── ModelX Brain Integration
│   ├── LLM API client
│   ├── Context management
│   └── Response generation
├── Text-to-Speech (TTS)
│   ├── Piper TTS (local voices)
│   ├── Pre-built voice models
│   └── Audio output streaming
└── Terminal UI
    ├── Real-time transcription display
    ├── Voice activity indicator
    └── Response visualization
```

**Technical Stack:**
- **Audio**: `sounddevice` or `pyaudio` for capture/playback
- **STT**: `whisper.cpp` Python bindings (local, no API needed)
- **TTS**: `piper-tts` with pre-downloaded voice models
- **Terminal UI**: `rich` library for beautiful terminal output
- **Audio Processing**: `numpy` for signal processing

### 1.2 Pre-Built Voice System

**Voice Models to Include:**
```
voices/
├── en_US-amy-low.onnx      # Female, casual
├── en_US-lessac-medium.onnx # Male, professional  
├── en_US-libritts-medium.onnx # Female, clear
└── voice_config.json       # Voice selection config
```

**Voice Selection System:**
```python
# Automatic voice selection based on context
VOICE_PROFILES = {
    "casual": "en_US-amy-low.onnx",
    "professional": "en_US-lessac-medium.onnx",
    "clear": "en_US-libritts-medium.onnx",
   : "en_US-libritts-medium.onnx"
}
```

### 1.3 Streaming Audio Pipeline

**Architecture:**
```python
class AudioPipeline:
    def __init__(self):
        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.is_listening = False
        
    async def capture_audio(self):
        """Continuous audio capture with VAD"""
        while self.is_listening:
            audio_chunk = await self.microphone.read()
            if self.voice_activity_detected(audio_chunk):
                await self.input_queue.put(audio_chunk)
    
    async def transcribe_stream(self):
        """Real-time transcription"""
        async for audio_chunk in self.input_queue:
            text = await self.whisper.transcribe(audio_chunk)
            await self.process_text(text)
    
    async def synthesize_speech(self, text):
        """Convert response to speech"""
        audio = await self.piper.synthesize(text, voice=self.selected_voice)
        await self.output_queue.put(audio)
    
    async def play_audio(self):
        """Stream audio output"""
        async for audio_chunk in self.output_queue:
            await self.speaker.play(audio_chunk)
```

---

## Phase 2: Simple Configuration System (Week 2-3)

### 2.1 First-Run Setup Wizard

**User Experience:**
```bash
$ modelx-voice

╔═══════════════════════════════════════════════════════════════╗
║              ModelX Voice Assistant - Setup                   ║
╚═══════════════════════════════════════════════════════════════╝

Welcome! Let's configure your voice assistant.

? Choose your LLM provider:
  □ Anthropic (Claude) - Recommended
  □ OpenAI (GPT)
  □ OpenRouter (Multi-provider)
  □ Local (Ollama)

? Enter your API key: *********************************

? Select voice profile:
  ○ Professional (Male)
  ○ Casual (Female)  
  ● Clear (Female) - Default

✓ Configuration saved to ~/.modelx-voice/config.json
✓ Downloading voice models... (this happens once)
✓ Testing audio devices...
✓ Setup complete!

Press ENTER to start your voice assistant...
```

### 2.2 Configuration File Structure

**`~/.modelx-voice/config.json`:**
```json
{
  "api": {
    "provider": "anthropic",
    "api_key": "sk-ant-xxx",
    "model": "claude-sonnet-4-20250514",
    "base_url": null
  },
  "voice": {
    "selected_voice": "en_US-libritts-medium.onnx",
    "voice_profile": "clear",
    "speed": 1.0,
    "pitch": 1.0
  },
  "audio": {
    "input_device": "default",
    "output_device": "default",
    "sample_rate": 16000
  },
  "behavior": {
    "wake_word": "hey modelx",
    "auto_listen": true,
    "response_delay": 0.5
  }
}
```

### 2.3 API Key Management

**Secure Storage:**
```python
import keyring
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".modelx-voice"
        self.config_file = self.config_dir / "config.json"
        
    def save_api_key(self, provider, key):
        """Store API key securely in system keyring"""
        keyring.set_password("modelx-voice", provider, key)
        
    def get_api_key(self, provider):
        """Retrieve API key from keyring"""
        return keyring.get_password("modelx-voice", provider)
        
    def first_run_setup(self):
        """Interactive setup wizard"""
        if not self.config_file.exists():
            self.run_setup_wizard()
```

---

## Phase 3: Terminal Interface Design (Week 3-4)

### 3.1 Rich Terminal UI

**Interface Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  🎤 ModelX Voice Assistant                    [● Listening]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  You: What's the latest in quantum computing?                    │
│                                                                  │
│  🤖 ModelX: Recent breakthroughs include...                      │
│            • Google's quantum error correction                   │
│            • IBM's 1000-qubit processor                          │
│            • Advances in quantum machine learning                 │
│                                                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Context: Research | Mode: Professional | Voice: Clear         │
│  Tokens: 1,234 | Cost: $0.02 | Response Time: 2.3s             │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation with Rich:**
```python
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live

class VoiceTerminalUI:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.setup_layout()
        
    def setup_layout(self):
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
    def update_transcription(self, text):
        """Update real-time transcription display"""
        self.layout["main"].update(
            Panel(f"You: {text}", title="Transcription", border_style="blue")
        )
        
    def update_response(self, text):
        """Update AI response display"""
        self.layout["main"].update(
            Panel(f"🤖 ModelX: {text}", title="Response", border_style="green")
        )
        
    def update_status(self, status):
        """Update listening status indicator"""
        status_icon = "●" if status == "listening" else "○"
        self.layout["header"].update(
            f"🎤 ModelX Voice Assistant [{status_icon} {status.title()}]"
        )
```

### 3.2 Voice Activity Indicator

**Visual Feedback:**
```python
def display_voice_activity(audio_level):
    """Show real-time voice activity visualization"""
    bars = min(20, int(audio_level * 20))
    indicator = "█" * bars + "░" * (20 - bars)
    color = "green" if bars > 15 else "yellow" if bars > 5 else "red"
    console.print(f"[{color}]{indicator}[/{color}]", end="\r")
```

### 3.3 Command System

**Voice Commands:**
```python
VOICE_COMMANDS = {
    "stop": "Stop listening",
    "pause": "Pause response",
    "clear": "Clear conversation history",
    "save": "Save conversation",
    "help": "Show available commands",
    "switch voice": "Change voice profile",
    "status": "Show system status"
}

class CommandProcessor:
    def process_command(self, text):
        """Check if text is a voice command"""
        text_lower = text.lower().strip()
        if text_lower in VOICE_COMMANDS:
            return self.execute_command(text_lower)
        return None  # Not a command, send to LLM
```

---

## Phase 4: ModelX Brain Integration (Week 4-5)

### 4.1 Simplified LLM Client

**Lightweight Integration:**
```python
class ModelXVoiceBrain:
    def __init__(self, config):
        self.config = config
        self.client = self._init_llm_client()
        self.conversation_history = []
        
    def _init_llm_client(self):
        """Initialize LLM client based on provider"""
        if self.config["api"]["provider"] == "anthropic":
            from anthropic import AsyncAnthropic
            return AsyncAnthropic(api_key=self.config["api"]["api_key"])
        elif self.config["api"]["provider"] == "openai":
            from openai import AsyncOpenAI
            return AsyncOpenAI(api_key=self.config["api"]["api_key"])
            
    async def process_input(self, text):
        """Process user input through ModelX"""
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": text})
        
        # Generate response
        response = await self.client.messages.create(
            model=self.config["api"]["model"],
            messages=self.conversation_history,
            max_tokens=1000
        )
        
        # Extract response text
        response_text = response.content[0].text
        self.conversation_history.append({"role": "assistant", "content": response_text})
        
        return response_text
```

### 4.2 Context Management

**Memory System:**
```python
class ConversationMemory:
    def __init__(self, max_turns=20):
        self.history = []
        self.max_turns = max_turns
        
    def add_exchange(self, user_input, ai_response):
        """Add conversation exchange"""
        self.history.append({
            "user": user_input,
            "assistant": ai_response,
            "timestamp": datetime.now()
        })
        
        # Prune old conversations
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns:]
            
    def get_context(self, recent_turns=5):
        """Get recent conversation context"""
        return self.history[-recent_turns:]
        
    def save_conversation(self, filename):
        """Save conversation to file"""
        with open(filename, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)
```

---

## Phase 5: Packaging & Distribution (Week 5-6)

### 5.1 Standalone Package Structure

**Distribution Package:**
```
modelx-voice/
├── modelx_voice/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── audio/
│   │   ├── capture.py
│   │   ├── playback.py
│   │   └── vad.py
│   ├── stt/
│   │   ├── whisper_wrapper.py
│   │   └── transcriber.py
│   ├── tts/
│   │   ├── piper_wrapper.py
│   │   └── synthesizer.py
│   ├── brain/
│   │   ├── llm_client.py
│   │   └── context.py
│   ├── ui/
│   │   ├── terminal.py
│   │   └── display.py
│   ├── config/
│   │   ├── manager.py
│   │   └── setup_wizard.py
│   └── voices/              # Pre-built voice models
│       ├── en_US-amy-low.onnx
│       ├── en_US-lessac-medium.onnx
│       └── en_US-libritts-medium.onnx
├── pyproject.toml
├── README.md
├── INSTALL.md
└── setup.py
```

### 5.2 Installation Scripts

**One-Line Installation:**
```bash
# Install via pip
pip install modelx-voice

# Or download standalone package
curl -O https://releases.modelx.ai/modelx-voice-latest.tar.gz
tar -xzf modelx-voice-latest.tar.gz
cd modelx-voice
./install.sh
```

**Cross-Platform Install Script:**
```bash
#!/bin/bash
# install.sh

echo "Installing ModelX Voice Assistant..."

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

# Install system dependencies
if [[ "$OS" == "Darwin" ]]; then
    brew install portaudio ffmpeg
elif [[ "$OS" == "Linux" ]]; then
    sudo apt-get install -y portaudio19-dev ffmpeg
fi

# Install Python package
pip install -e .

# Download voice models
python -c "from modelx_voice.config import download_voices; download_voices()"

echo "Installation complete! Run 'modelx-voice' to start."
```

### 5.3 PyProject Configuration

**`pyproject.toml`:**
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "modelx-voice"
version = "1.0.0"
description = "Terminal voice assistant for ModelX"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "anthropic>=0.18.0",
    "openai>=1.0.0",
    "rich>=13.0.0",
    "sounddevice>=0.4.0",
    "numpy>=1.24.0",
    "keyring>=24.0.0",
    "aiohttp>=3.9.0",
]

[project.scripts]
modelx-voice = "modelx_voice.main:main"

[project.optional-dependencies]
audio = ["pyaudio>=0.2.13"]
dev = ["pytest>=7.0.0", "black>=23.0.0"]

[tool.hatch.build.targets.wheel]
packages = ["modelx_voice"]
include = ["modelx_voice/voices/*.onnx"]
```

### 5.4 Auto-Update System

**Update Checker:**
```python
import requests
from packaging import version

class UpdateManager:
    def __init__(self):
        self.current_version = "1.0.0"
        self.api_url = "https://api.modelx.ai/voice/version"
        
    async def check_for_updates(self):
        """Check for updates"""
        try:
            response = await requests.get(self.api_url)
            latest_version = response.json()["version"]
            
            if version.parse(latest_version) > version.parse(self.current_version):
                return self.prompt_update(latest_version)
        except Exception:
            pass  # Silent fail
            
        return False
            
    def prompt_update(self, new_version):
        """Prompt user to update"""
        console.print(f"\n[yellow]New version available: {new_version}[/yellow]")
        console.print("Run: pip install --upgrade modelx-voice")
        return True
```

---

## Phase 6: Testing & Optimization (Week 6-7)

### 6.1 Audio Testing Suite

**Automated Audio Tests:**
```python
class AudioTester:
    def test_microphone_access(self):
        """Test microphone access"""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            assert any('input' in str(d).lower() for d in devices)
            return True
        except Exception as e:
            console.print(f"[red]Microphone test failed: {e}[/red]")
            return False
            
    def test_speaker_output(self):
        """Test speaker output"""
        try:
            import sounddevice as sd
            sd.play(np.sin(440 * np.linspace(0, 1, 44100)), 44100)
            return True
        except Exception as e:
            console.print(f"[red]Speaker test failed: {e}[/red]")
            return False
```

### 6.2 Performance Optimization

**Optimization Targets:**
```python
PERFORMANCE_TARGETS = {
    "stt_latency": 500,      # ms
    "tts_latency": 300,      # ms
    "first_response": 2000,  # ms
    "memory_usage": 500,     # MB
    "cpu_usage": 30          # %
}

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
        
    def measure_latency(self, operation):
        """Measure operation latency"""
        start = time.time()
        result = operation()
        latency = (time.time() - start) * 1000
        self.metrics[operation.__name__] = latency
        return result
```

### 6.3 Error Handling

**Graceful Degradation:**
```python
class ErrorHandler:
    def handle_audio_error(self, error):
        """Handle audio-related errors"""
        console.print("[red]Audio error detected[/red]")
        console.print("Falling back to text-only mode...")
        self.enable_text_mode()
        
    def handle_network_error(self, error):
        """Handle network errors"""
        console.print("[yellow]Network error - using offline mode[/yellow]")
        self.enable_offline_mode()
        
    def handle_api_error(self, error):
        """Handle API errors"""
        console.print("[red]API error - check your API key[/red]")
        self.prompt_reconfigure()
```

---

## Phase 7: Documentation & Examples (Week 7-8)

### 7.1 User Documentation

**README.md Structure:**
```markdown
# ModelX Voice Assistant

## Quick Start
1. Install: `pip install modelx-voice`
2. Run: `modelx-voice`
3. Add API key when prompted
4. Start talking!

## Features
- 🎤 Real-time voice interaction
- 🧠 Multiple LLM provider support
- 🔊 Pre-built natural voices
- 💻 Beautiful terminal interface
- 🔄 Conversation memory

## Configuration
Edit `~/.modelx-voice/config.json` to customize:
- Voice selection
- Audio devices
- LLM provider
- Behavior settings

## Voice Commands
- "Stop" - Stop listening
- "Clear" - Clear history
- "Save" - Save conversation
- "Help" - Show commands
```

### 7.2 Example Conversations

**Demo Scenarios:**
```python
EXAMPLE_CONVERSATIONS = {
    "research": [
        "What's the latest in AI research?",
        "Explain quantum computing simply",
        "Compare Python vs Rust"
    ],
    "coding": [
        "Debug this function",
        "Write a REST API",
        "Optimize this code"
    ],
    "general": [
        "Tell me a joke",
        "What's the weather?",
        "Set a reminder"
    ]
}
```

---

## Implementation Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 1** | Week 1-2 | Audio pipeline, STT/TTS integration |
| **Phase 2** | Week 2-3 | Setup wizard, configuration system |
| **Phase 3** | Week 3-4 | Terminal UI, voice commands |
| **Phase 4** | Week 4-5 | LLM integration, context management |
| **Phase 5** | Week 5-6 | Packaging, distribution system |
| **Phase 6** | Week 6-7 | Testing, optimization |
| **Phase 7** | Week 7-8 | Documentation, examples |

**Total: 8 weeks for production-ready voice assistant**

---

## Key Success Metrics

- **Installation time**: < 5 minutes
- **First response latency**: < 2 seconds
- **Voice naturalness**: > 4/5 user rating
- **Setup completion rate**: > 90%
- **Cross-platform support**: Windows, macOS, Linux

---

## Technical Specifications

### System Requirements
- **Python**: 3.10+
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 500MB for voice models
- **Microphone**: Required for voice input
- **Speakers**: Required for voice output

### Supported LLM Providers
- Anthropic (Claude)
- OpenAI (GPT)
- OpenRouter (Multi-provider)
- Local (Ollama)

### Voice Profiles
- **Professional**: Male voice, formal tone
- **Casual**: Female voice, conversational tone
- **Clear**: Female voice, high clarity

### Audio Specifications
- **Sample Rate**: 16kHz
- **Bit Depth**: 16-bit
- **Channels**: Mono
- **Format**: WAV/PCM

---

## Security Considerations

### API Key Storage
- System keyring integration
- Never store in plain text
- Optional environment variable support

### Audio Privacy
- All processing done locally
- No audio data sent to cloud (except LLM)
- Optional offline mode

### Network Security
- HTTPS only for API calls
- Certificate validation
- Request/response encryption

---

## Future Enhancements

### Short-term (Post-Release)
- Additional voice models
- Multi-language support
- Custom voice training
- Plugin system

### Long-term (Future Versions)
- Web interface
- Mobile app
- Voice cloning
- Emotion detection
- Multi-user support

---

## Troubleshooting

### Common Issues

**No microphone detected:**
```bash
# Check audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Install system dependencies
# macOS: brew install portaudio
# Linux: sudo apt-get install portaudio19-dev
```

**Voice models not loading:**
```bash
# Re-download voice models
modelx-voice --download-voices

# Check voice directory
ls ~/.modelx-voice/voices/
```

**API key errors:**
```bash
# Reconfigure API key
modelx-voice --configure

# Test API connection
modelx-voice --test-api
```

---

## Development Guidelines

### Code Style
- Follow PEP 8
- Use type hints
- Document all functions
- Write unit tests

### Testing
- Unit tests for all components
- Integration tests for audio pipeline
- End-to-end tests for user flows

### Performance
- Profile audio processing
- Optimize memory usage
- Minimize latency
- Monitor CPU usage

---

## License & Distribution

- **License**: MIT
- **Distribution**: PyPI
- **Source**: GitHub
- **Support**: Discord community

---

## Conclusion

This implementation plan creates a truly plug-and-play voice experience where users only need to:

1. Install: `pip install modelx-voice`
2. Run: `modelx-voice`
3. Add API key via setup wizard
4. Start talking immediately

The combination of local STT/TTS (Whisper + Piper) with cloud LLM integration provides the best balance of privacy, performance, and intelligence. The beautiful terminal interface makes it accessible to both technical and non-technical users.
