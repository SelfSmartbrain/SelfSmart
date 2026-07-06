"""
Voice Assistant - Complete Pipeline
Integrates STT -> LLM -> TTS with cognitive bus
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class AssistantState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class VoiceConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    vad_threshold: float = 0.5
    silence_duration: float = 1.0  # seconds of silence to end utterance
    language: str = "en"


class VoiceAssistant:
    """
    Complete voice assistant pipeline:
    Audio Input -> VAD -> STT -> Cognitive Bus -> LLM -> TTS -> Audio Output
    """

    def __init__(
        self,
        config: VoiceConfig,
        stt_engine: Any,  # Must have: transcribe(audio_bytes) -> str
        tts_engine: Any,  # Must have: synthesize(text) -> audio_bytes
        cognitive_bus: Any,  # Must have: emit(event), subscribe(type, handler)
        llm_client: Any,  # Must have: ainvoke(prompt) -> response
        wake_word_detector: Optional[Any] = None,
    ):
        self.config = config
        self.stt = stt_engine
        self.tts = tts_engine
        self.bus = cognitive_bus
        self.llm = llm_client
        self.wake_word = wake_word_detector

        self.state = AssistantState.IDLE
        self._audio_buffer = bytearray()
        self._silence_chunks = 0
        self._is_speaking = False

        # Callbacks
        self.on_transcript: Optional[Callable[[str], Any]] = None
        self.on_response: Optional[Callable[[str], Any]] = None
        self.on_state_change: Optional[Callable[[AssistantState], Any]] = None

    async def _set_state(self, state: AssistantState):
        self.state = state
        if self.on_state_change:
            await self.on_state_change(state)
        logger.info(f"State: {state.value}")

    async def process_audio_chunk(self, chunk: bytes):
        """Process incoming audio chunk (called from audio input callback)"""
        if self.state == AssistantState.SPEAKING:
            return  # Ignore input while speaking

        self._audio_buffer.extend(chunk)

        # Simple energy-based VAD
        energy = self._calculate_energy(chunk)
        is_speech = energy > self.config.vad_threshold

        if is_speech:
            self._silence_chunks = 0
            if self.state == AssistantState.IDLE:
                await self._set_state(AssistantState.LISTENING)
        else:
            self._silence_chunks += 1

        silence_chunks_needed = int(
            self.config.silence_duration * self.config.sample_rate / self.config.chunk_size
        )

        if (
            self.state == AssistantState.LISTENING
            and self._silence_chunks >= silence_chunks_needed
            and len(self._audio_buffer) > self.config.sample_rate * 0.5  # At least 0.5s
        ):
            await self._process_utterance()

    def _calculate_energy(self, chunk: bytes) -> float:
        """Calculate RMS energy of audio chunk"""
        import numpy as np

        # Ensure chunk size is multiple of 2 bytes (int16)
        if len(chunk) % 2 != 0:
            chunk = chunk[:-1]
        audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
        return np.sqrt(np.mean(audio**2)) / 32768.0

    async def _process_utterance(self):
        """Process complete utterance"""
        await self._set_state(AssistantState.PROCESSING)

        audio_data = bytes(self._audio_buffer)
        self._audio_buffer.clear()

        try:
            # STT
            transcript = await self.stt.transcribe(audio_data)
            if not transcript or not transcript.strip():
                await self._set_state(AssistantState.IDLE)
                return

            logger.info(f"Transcript: {transcript}")
            if self.on_transcript:
                await self.on_transcript(transcript)

            # Emit to cognitive bus
            await self.bus.emit(
                self.bus.create_event(
                    event_type="user.speech",
                    source="voice_assistant",
                    payload={
                        "text": transcript,
                        "audio_duration": len(audio_data) / self.config.sample_rate,
                    },
                )
            )

            # Get LLM response
            response = await self._get_llm_response(transcript)

            if response:
                logger.info(f"Response: {response}")
                if self.on_response:
                    await self.on_response(response)

                # TTS + Play
                await self._speak(response)

        except Exception as e:
            logger.error(f"Processing error: {e}")
        finally:
            await self._set_state(AssistantState.IDLE)

    async def _get_llm_response(self, user_input: str) -> str:
        """Get response from LLM with context"""
        # Build context from recent cognitive events
        context = self._build_context()

        prompt = f"""You are a helpful AI assistant. Respond naturally and concisely.

Context: {context}

User: {user_input}

Assistant:"""

        try:
            response = await self.llm.ainvoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "I'm having trouble thinking right now."

    def _build_context(self) -> str:
        """Build context from recent cognitive events"""
        events = self.bus.get_history(limit=10)
        if not events:
            return "No recent context."

        context_parts = []
        for e in events[-5:]:
            if e.event_type.value.startswith("user."):
                context_parts.append(f"User: {e.payload.get('text', '')}")
            elif e.event_type.value.startswith("assistant."):
                context_parts.append(f"Assistant: {e.payload.get('text', '')}")

        return "\n".join(context_parts) if context_parts else "No recent context."

    async def _speak(self, text: str):
        """Synthesize and play speech"""
        await self._set_state(AssistantState.SPEAKING)
        self._is_speaking = True

        try:
            audio = await self.tts.synthesize(text)
            if audio:
                await self._play_audio(audio)

            # Emit completion event
            await self.bus.emit(
                self.bus.create_event(
                    event_type="assistant.speech", source="voice_assistant", payload={"text": text}
                )
            )

        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            self._is_speaking = False
            await self._set_state(AssistantState.IDLE)

    async def _play_audio(self, audio: bytes):
        """Play audio bytes (implement with sounddevice/pyaudio)"""
        import sounddevice as sd
        import numpy as np

        # Assuming 16-bit PCM at config sample rate
        audio_array = np.frombuffer(audio, dtype=np.int16)
        await asyncio.get_event_loop().run_in_executor(
            None, sd.play, audio_array, self.config.sample_rate
        )
        # Wait for playback
        duration = len(audio_array) / self.config.sample_rate
        await asyncio.sleep(duration + 0.1)

    async def start_listening(self):
        """Start the assistant (call after audio input is set up)"""
        await self._set_state(AssistantState.IDLE)
        logger.info("Voice assistant started")

    async def stop(self):
        """Stop the assistant"""
        await self._set_state(AssistantState.IDLE)
        self._audio_buffer.clear()


# Factory for creating engines (implement based on your choices)
class EngineFactory:
    @staticmethod
    def create_stt(engine: str = "faster-whisper", **kwargs):
        """Create a local speech-to-text engine."""
        if engine in {"whisper", "faster-whisper"}:
            from faster_whisper import WhisperModel

            model = WhisperModel(
                kwargs.get("model_size", "base.en"),
                device=kwargs.get("device", "cpu"),
                compute_type=kwargs.get("compute_type", "int8"),
            )

            class FasterWhisperSTT:
                async def transcribe(self, audio_bytes: bytes) -> str:
                    import asyncio
                    import os
                    import tempfile
                    import wave

                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        temp_path = f.name

                    try:
                        with wave.open(temp_path, "wb") as wav_file:
                            wav_file.setnchannels(kwargs.get("channels", 1))
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(kwargs.get("sample_rate", 16000))
                            wav_file.writeframes(audio_bytes)

                        segments, _ = await asyncio.to_thread(model.transcribe, temp_path)
                        return " ".join(s.text for s in segments)
                    finally:
                        os.unlink(temp_path)

            return FasterWhisperSTT()

        raise ValueError(f"Unknown STT engine: {engine}")

    @staticmethod
    def create_tts(engine: str = "piper", **kwargs):
        """Create TTS engine: piper, coqui, edge-tts, etc."""
        if engine == "piper":
            # Piper TTS - fast, good quality, offline
            import subprocess
            import tempfile

            class PiperTTS:
                def __init__(self, voice: str = "en_US-lessac-medium"):
                    self.voice = voice

                async def synthesize(self, text: str) -> bytes:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        output = f.name

                    try:
                        proc = await asyncio.create_subprocess_exec(
                            "piper",
                            "--model",
                            self.voice,
                            "--output_file",
                            output,
                            stdin=asyncio.subprocess.PIPE,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        await proc.communicate(text.encode())

                        with open(output, "rb") as f:
                            return f.read()
                    finally:
                        import os

                        if os.path.exists(output):
                            os.unlink(output)

            return PiperTTS(kwargs.get("voice", "en_US-lessac-medium"))

        elif engine == "edge-tts":
            import edge_tts
            import tempfile

            class EdgeTTS:
                def __init__(self, voice: str = "en-US-AriaNeural"):
                    self.voice = voice

                async def synthesize(self, text: str) -> bytes:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                        output = f.name

                    try:
                        communicate = edge_tts.Communicate(text, self.voice)
                        await communicate.save(output)

                        with open(output, "rb") as f:
                            return f.read()
                    finally:
                        import os

                        if os.path.exists(output):
                            os.unlink(output)

            return EdgeTTS(kwargs.get("voice", "en-US-AriaNeural"))

        raise ValueError(f"Unknown TTS engine: {engine}")
