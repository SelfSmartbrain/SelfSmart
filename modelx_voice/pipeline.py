import asyncio
import numpy as np
from typing import Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging

from .audio import AudioCapture, AudioPlayback, StreamingVAD
from .stt import WhisperTranscriber
from .tts import PiperSynthesizer
from .brain import ModelXBrain
from .config import ConfigManager
from .ui import SimpleVoiceUI
from .ui.commands import CommandProcessor, VoiceCommand, CommandType

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class PipelineConfig:
    sample_rate: int = 16000
    vad_aggressiveness: int = 2
    min_speech_ms: int = 250
    max_silence_ms: int = 1000
    whisper_model: str = "base"
    voice_profile: str = "clear"
    auto_listen: bool = True


class AudioPipeline:
    def __init__(
        self,
        config: PipelineConfig,
        config_manager: ConfigManager,
        brain: ModelXBrain,
        ui: SimpleVoiceUI,
    ):
        self.config = config
        self.config_manager = config_manager
        self.brain = brain
        self.ui = ui
        self.command_processor = CommandProcessor()
        
        self._state = PipelineState.IDLE
        self._running = False
        
        self._capture: Optional[AudioCapture] = None
        self._playback: Optional[AudioPlayback] = None
        self._vad: Optional[StreamingVAD] = None
        self._transcriber: Optional[WhisperTranscriber] = None
        self._synthesizer: Optional[PiperSynthesizer] = None
        
        self._audio_buffer: list = []
        self._speech_detected = False

    async def initialize(self):
        self._capture = AudioCapture(
            sample_rate=self.config.sample_rate,
            channels=1,
            chunk_size=512,
            device=self.config_manager.config.audio.input_device,
        )
        
        self._playback = AudioPlayback(
            sample_rate=22050,
            channels=1,
            device=self.config_manager.config.audio.output_device,
        )
        
        self._vad = StreamingVAD(
            sample_rate=self.config.sample_rate,
            aggressiveness=self.config.vad_aggressiveness,
            min_speech_ms=self.config.min_speech_ms,
            max_silence_ms=self.config.max_silence_ms,
        )
        
        self._transcriber = WhisperTranscriber(
            model_size=self.config.whisper_model,
            language="en",
        )
        
        self._synthesizer = PiperSynthesizer(
            voice=self.config.voice_profile,
        )
        
        await self._capture.start()
        await self._playback.start()
        
        logger.info("Audio pipeline initialized")

    async def cleanup(self):
        self._running = False
        
        if self._capture:
            await self._capture.stop()
        if self._playback:
            await self._playback.stop()
        if self._synthesizer:
            pass
        
        logger.info("Audio pipeline cleaned up")

    @property
    def state(self) -> PipelineState:
        return self._state

    async def run(self):
        self._running = True
        self.ui.print_info("ModelX Voice Assistant started. Press Ctrl+C to exit.")
        
        try:
            if self.config.auto_listen:
                await self._listen_loop()
            else:
                await self._push_to_talk_loop()
        except KeyboardInterrupt:
            pass
        finally:
            await self.cleanup()

    async def _listen_loop(self):
        self._state = PipelineState.LISTENING
        self.ui.print_listening()
        
        while self._running:
            try:
                audio_chunk = await self._capture.read_chunk()
                await self._process_audio_chunk(audio_chunk)
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(0.1)

    async def _push_to_talk_loop(self):
        self.ui.print_info("Push-to-talk mode. Press Enter to speak.")
        
        while self._running:
            try:
                await asyncio.get_event_loop().run_in_executor(None, input)
                await self._record_and_process()
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in push-to-talk: {e}")

    async def _record_and_process(self):
        self._state = PipelineState.LISTENING
        self.ui.print_listening()
        self._audio_buffer = []
        self._speech_detected = False
        
        silence_start = None
        max_silence_duration = 2.0
        
        while self._running:
            audio_chunk = await self._capture.read_chunk()
            self._audio_buffer.append(audio_chunk)
            
            speech_result = self._vad.process(audio_chunk)
            if speech_result is not None:
                self._speech_detected = True
                silence_start = None
            elif self._speech_detected:
                if silence_start is None:
                    silence_start = asyncio.get_event_loop().time()
                elif asyncio.get_event_loop().time() - silence_start > max_silence_duration:
                    break
        
        if self._speech_detected and self._audio_buffer:
            await self._process_recorded_audio()

    async def _process_audio_chunk(self, audio_chunk: np.ndarray):
        speech_audio = self._vad.process(audio_chunk)
        
        if speech_audio is not None:
            await self._transcribe_and_respond(speech_audio)

    async def _process_recorded_audio(self):
        if not self._audio_buffer:
            return
            
        full_audio = np.concatenate(self._audio_buffer)
        await self._transcribe_and_respond(full_audio)

    async def _transcribe_and_respond(self, audio_data: np.ndarray):
        self._state = PipelineState.PROCESSING
        self.ui.print_processing()
        
        text = await self._transcriber.transcribe_async(audio_data)
        
        if not text or not text.strip():
            self.ui.clear_line()
            if self.config.auto_listen:
                self.ui.print_listening()
            return
        
        self.ui.clear_line()
        self.ui.print_user(text)
        
        cmd = self.command_processor.process(text)
        if await self._handle_command(cmd):
            if self.config.auto_listen:
                self._state = PipelineState.LISTENING
                self.ui.print_listening()
            return
        
        await self._generate_and_speak(text)

    async def _generate_and_speak(self, user_text: str):
        self._state = PipelineState.PROCESSING
        self.ui.print_processing()
        
        try:
            response = await self.brain.process_input(user_text)
        except Exception as e:
            self.ui.print_error(f"Failed to generate response: {e}")
            if self.config.auto_listen:
                self._state = PipelineState.LISTENING
                self.ui.print_listening()
            return
        
        self.ui.clear_line()
        self.ui.print_assistant(response)
        self.command_processor.set_last_response(response)
        
        self._state = PipelineState.SPEAKING
        
        try:
            audio = await self._synthesizer.synthesize_async(response)
            await self._playback.play(audio)
        except Exception as e:
            logger.error(f"TTS/Playback error: {e}")
        
        if self.config.auto_listen:
            self._state = PipelineState.LISTENING
            self.ui.print_listening()

    async def _handle_command(self, cmd: VoiceCommand) -> bool:
        if cmd.type == CommandType.NONE:
            return False
        
        if cmd.type == CommandType.STOP:
            self.ui.print_info("Stopping...")
            self._running = False
            return True
        
        elif cmd.type == CommandType.PAUSE:
            self.ui.print_info("Paused. Press Enter to continue.")
            await asyncio.get_event_loop().run_in_executor(None, input)
            return True
        
        elif cmd.type == CommandType.CLEAR:
            self.brain.clear_memory()
            self.ui.print_info("Conversation history cleared.")
            return True
        
        elif cmd.type == CommandType.SAVE:
            from pathlib import Path
            filepath = Path.home() / f"modelx_conversation_{int(asyncio.get_event_loop().time())}.json"
            self.brain.memory.export_conversation(filepath)
            self.ui.print_info(f"Conversation saved to {filepath}")
            return True
        
        elif cmd.type == CommandType.HELP:
            self.ui.print_info(self.command_processor.get_help_text())
            return True
        
        elif cmd.type == CommandType.SWITCH_VOICE:
            voice = cmd.args.get("voice", "clear")
            try:
                self._synthesizer.set_voice(voice)
                self.config.voice_profile = voice
                self.config_manager.update_voice(selected_voice=voice)
                self.ui.print_info(f"Voice changed to {voice}")
            except Exception as e:
                self.ui.print_error(f"Failed to change voice: {e}")
            return True
        
        elif cmd.type == CommandType.STATUS:
            stats = self.brain.get_stats()
            self.ui.print_info(f"Provider: {stats['provider']}, Model: {stats['model']}, Turns: {stats['turns']}, Tokens: {stats['total_tokens']}")
            return True
        
        elif cmd.type == CommandType.REPEAT:
            last = self.command_processor.get_last_response()
            if last:
                self.ui.print_assistant(last)
                audio = await self._synthesizer.synthesize_async(last)
                await self._playback.play(audio)
            else:
                self.ui.print_info("No previous response to repeat.")
            return True
        
        return False