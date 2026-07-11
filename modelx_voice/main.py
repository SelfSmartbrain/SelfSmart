import asyncio
import sys
import signal
import subprocess
import importlib.util
from pathlib import Path
from typing import Optional, List, Tuple


from .config import ConfigManager, run_setup_wizard
from .brain import ModelXBrain, ConversationMemory, get_provider, get_default_model, Message
from .pipeline import AudioPipeline, PipelineConfig
from .ui import SimpleVoiceUI


async def run_voice(
    setup: bool = False,
    configure: bool = False,
    test_audio: bool = False,
    test_api: bool = False,
    download_voices: bool = False,
    voice: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
):
    config_manager = ConfigManager()
    
    if setup or configure:
        success = await run_setup_wizard(config_manager)
        if not success:
            sys.exit(1)
        return
    
    if download_voices:
        from .tts import VoiceManager
        vm = VoiceManager()
        voices = vm.list_available_voices()
        print("Available voices:")
        for profile, filename in voices.items():
            print(f"  {profile}: {filename}")
        return
    
    config = config_manager.load()
    
    if provider:
        config.api.provider = provider
    if api_key:
        config.api.api_key = api_key
    if voice:
        config.voice.selected_voice = voice
    
    config_manager.save()
    
    if test_audio:
        await test_audio_devices()
        return
    
    if test_api:
        await test_api_connection(config)
        return
    
    if not config_manager.is_configured():
        print("Not configured. Run 'modelx --setup' to configure.")
        sys.exit(1)
    
    if not config.api.model:
        config.api.model = get_default_model(config.api.provider)
        config_manager.save()
    
    memory_file = config_manager.config_dir / "conversation.json"
    memory = ConversationMemory(persistence_file=memory_file)
    
    brain = ModelXBrain(
        provider=config.api.provider,
        api_key=config.api.api_key,
        base_url=config.api.base_url or None,
        model=config.api.model,
        memory=memory,
    )
    
    pipeline_config = PipelineConfig(
        sample_rate=config.audio.sample_rate,
        vad_aggressiveness=config.behavior.vad_aggressiveness,
        whisper_model="base",
        voice_profile=config.voice.selected_voice,
        auto_listen=config.behavior.auto_listen and not config.behavior.wake_word,
    )
    
    ui = SimpleVoiceUI()
    pipeline = AudioPipeline(pipeline_config, config_manager, brain, ui)
    
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        print("\nShutting down...")
        pipeline._running = False
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass
    
    await pipeline.initialize()
    await pipeline.run()
    
    await brain.close()
    print("\nGoodbye!")


async def test_audio_devices():
    import sounddevice as sd
    print("Audio Devices:")
    print("-" * 60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        io = []
        if device['max_input_channels'] > 0:
            io.append(f"in:{device['max_input_channels']}")
        if device['max_output_channels'] > 0:
            io.append(f"out:{device['max_output_channels']}")
        default_in = " (default in)" if i == sd.default.device[0] else ""
        default_out = " (default out)" if i == sd.default.device[1] else ""
        print(f"  [{i}] {device['name']} - {'/'.join(io)}{default_in}{default_out}")


async def test_api_connection(config):
    print(f"Testing {config.api.provider} API connection...")
    
    try:
        provider = get_provider(config.api.provider, config.api.api_key, config.api.base_url)
        response = await provider.chat_completion(
            messages=[Message(role="user", content="Hello")],
            model=config.api.model or "claude-sonnet-4-20250514",
            max_tokens=10,
        )
        print(f"✓ Success! Response: {response.content[:50]}...")
        await provider.close()
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)


# ===== HEALTH CHECK FRAMEWORK =====

class HealthCheck:
    """Individual health check result."""
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.status = "unknown"
        self.message = ""
        self.details = {}
    
    def pass_(self, message: str = "", **details):
        self.status = "pass"
        self.message = message
        self.details = details
        return self
    
    def warn(self, message: str = "", **details):
        self.status = "warn"
        self.message = message
        self.details = details
        return self
    
    def fail(self, message: str = "", **details):
        self.status = "fail"
        self.message = message
        self.details = details
        return self
    
    def skip(self, message: str = ""):
        self.status = "skip"
        self.message = message
        return self


class HealthCheckRunner:
    """Runs all health checks and aggregates results."""
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.categories = {}
    
    def add(self, check: HealthCheck):
        self.checks.append(check)
        if check.category not in self.categories:
            self.categories[check.category] = []
        self.categories[check.category].append(check)
    
    def run_all(self):
        for check in self.checks:
            check()
    
    def get_summary(self) -> Tuple[int, int, int, int]:
        pass_count = sum(1 for c in self.checks if c.status == "pass")
        warn_count = sum(1 for c in self.checks if c.status == "warn")
        fail_count = sum(1 for c in self.checks if c.status == "fail")
        skip_count = sum(1 for c in self.checks if c.status == "skip")
        return pass_count, warn_count, fail_count, skip_count
    
    def print_report(self):
        print("ModelX Doctor - System Diagnostics")
        print("=" * 50)
        
        for category, checks in self.categories.items():
            print(f"\n{category}:")
            for check in checks:
                icon = {"pass": "✓", "warn": "⚠", "fail": "✗", "skip": "○"}[check.status]
                print(f"  {icon} {check.name}: {check.message}")
                for k, v in check.details.items():
                    print(f"      {k}: {v}")
        
        pass_count, warn_count, fail_count, skip_count = self.get_summary()
        total = len(self.checks)
        
        print("\n" + "=" * 50)
        print(f"Summary: {pass_count}/{total} passed, {warn_count} warnings, {fail_count} failures, {skip_count} skipped")
        
        if fail_count == 0:
            health = 100 - (warn_count * 100 // max(total, 1))
            print(f"Overall Health: {health}%")
        else:
            print("Overall Health: FAILING")
        
        return fail_count == 0


def check_python_version() -> HealthCheck:
    import sys
    check = HealthCheck("Python Version", "Runtime")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        check.pass_(f"Python {version}", version=version)
    else:
        check.fail(f"Python {version} (requires 3.10+)", version=version)
    return check


def check_package_version() -> HealthCheck:
    check = HealthCheck("Package Version", "Runtime")
    try:
        import modelx_voice
        check.pass_(f"ModelX {modelx_voice.__version__}", version=modelx_voice.__version__)
    except Exception as e:
        check.fail(f"Version unknown: {e}")
    return check


def check_virtual_env() -> HealthCheck:
    check = HealthCheck("Virtual Environment", "Runtime")
    import sys
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        check.pass_("Active", path=sys.prefix)
    else:
        check.warn("Not detected (system Python)", path=sys.prefix)
    return check


def check_config() -> HealthCheck:
    check = HealthCheck("Configuration", "Configuration")
    config_manager = ConfigManager()
    if config_manager.is_configured():
        config = config_manager.load()
        check.pass_("Configured", config_file=str(config_manager.config_file))
        return check
    check.fail("Not configured (run 'modelx --setup')", config_file=str(config_manager.config_file))
    return check


def check_api_keys() -> HealthCheck:
    check = HealthCheck("API Keys", "Configuration")
    config_manager = ConfigManager()
    config = config_manager.load()
    
    provider = config.api.provider
    api_key = config_manager.get_api_key(provider)
    
    if api_key:
        check.pass_(f"{provider} key configured", provider=provider)
    else:
        check.fail(f"{provider} key missing", provider=provider)
    return check


def check_write_permissions() -> HealthCheck:
    check = HealthCheck("Write Permissions", "System")
    config_manager = ConfigManager()
    try:
        test_file = config_manager.config_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        check.pass_(f"Writable ({config_manager.config_dir})", path=str(config_manager.config_dir))
    except Exception as e:
        check.fail(f"Cannot write: {e}", path=str(config_manager.config_dir))
    return check


def check_network() -> HealthCheck:
    check = HealthCheck("Network Access", "System")
    try:
        import urllib.request
        urllib.request.urlopen('https://api.anthropic.com', timeout=5)
        check.pass_("Internet accessible")
    except Exception:
        check.warn("Limited or no internet access")
    return check


def check_audio_devices() -> HealthCheck:
    check = HealthCheck("Audio Devices", "Hardware")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        has_input = any(d['max_input_channels'] > 0 for d in devices)
        has_output = any(d['max_output_channels'] > 0 for d in devices)
        
        if has_input and has_output:
            check.pass_(f"Input: {has_input}, Output: {has_output}", 
                       input=has_input, output=has_output)
        elif has_input or has_output:
            check.warn(f"Partial: Input={has_input}, Output={has_output}",
                      input=has_input, output=has_output)
        else:
            check.fail("No audio devices found")
    except Exception as e:
        check.fail(f"Audio check failed: {e}")
    return check


def check_voice_models() -> HealthCheck:
    check = HealthCheck("Voice Models", "Models")
    try:
        from .tts import VoiceManager
        vm = VoiceManager()
        voices = vm.list_available_voices()
        if voices:
            check.pass_(f"{len(voices)} voices available", voices=list(voices.keys()))
        else:
            check.warn("No voices downloaded (will download on first run)")
    except Exception as e:
        check.warn(f"Could not check voices: {e}")
    return check


def check_stt_model() -> HealthCheck:
    check = HealthCheck("STT Model (Whisper)", "Models")
    try:
        from .stt import WhisperTranscriber
        WhisperTranscriber()
        check.pass_("Whisper model loadable")
    except Exception as e:
        check.fail(f"Whisper unavailable: {e}")
    return check


def check_tts_engine() -> HealthCheck:
    check = HealthCheck("TTS Engine (Piper)", "Models")
    try:
        from .tts import PiperSynthesizer
        PiperSynthesizer()
        check.pass_("Piper engine loadable")
    except Exception as e:
        check.fail(f"Piper unavailable: {e}")
    return check


def check_llm_providers() -> HealthCheck:
    check = HealthCheck("LLM Providers", "Providers")
    providers = ["anthropic", "openai", "openrouter", "ollama"]
    available = []
    missing = []
    
    for p in providers:
        try:
            get_provider(p, "test-key")
            available.append(p)
        except Exception:
            missing.append(p)
    
    if available:
        check.pass_(f"Available: {', '.join(available)}", available=available, missing=missing)
    else:
        check.fail("No providers available")
    return check


async def check_llm_connectivity() -> HealthCheck:
    check = HealthCheck("LLM Connectivity", "Providers")
    config_manager = ConfigManager()
    config = config_manager.load()
    
    if not config.api.api_key:
        check.skip("No API key configured")
        return check
    
    try:
        provider = get_provider(config.api.provider, config.api.api_key, config.api.base_url)
        response = await provider.chat_completion(
            messages=[Message(role="user", content="ping")],
            model=config.api.model or get_default_model(config.api.provider),
            max_tokens=5,
        )
        await provider.close()
        check.pass_(f"{config.api.provider} API responding", 
                   provider=config.api.provider, model=config.api.model)
    except Exception as e:
        check.fail(f"{config.api.provider} API failed: {e}",
                  provider=config.api.provider)
    return check


async def check_ollama() -> HealthCheck:
    check = HealthCheck("Ollama (Local)", "Providers")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                check.pass_(f"Ollama running ({len(models)} models)", models=len(models))
            else:
                check.warn("Ollama not responding")
    except Exception:
        check.skip("Ollama not running (optional)")
    return check


def run_doctor():
    runner = HealthCheckRunner()
    
    # Runtime
    runner.add(check_python_version())
    runner.add(check_package_version())
    runner.add(check_virtual_env())
    
    # Configuration
    runner.add(check_config())
    runner.add(check_api_keys())
    runner.add(check_write_permissions())
    
    # System
    runner.add(check_network())
    runner.add(check_audio_devices())
    
    # Models
    runner.add(check_voice_models())
    runner.add(check_stt_model())
    runner.add(check_tts_engine())
    
    # Providers
    runner.add(check_llm_providers())
    
    # Run async checks
    loop = asyncio.new_event_loop()
    async_checks = [check_llm_connectivity(), check_ollama()]
    for coro in async_checks:
        check = loop.run_until_complete(coro)
        runner.add(check)
    loop.close()
    
    success = runner.print_report()
    if not success:
        sys.exit(1)


# ===== SELF-TEST FRAMEWORK =====

class SelfTest:
    """Quick runtime validation tests."""
    
    def __init__(self):
        self.results = []
    
    def add_result(self, name: str, success: bool, details: str = ""):
        self.results.append((name, success, details))
    
    def print_summary(self):
        passed = sum(1 for _, s, _ in self.results if s)
        total = len(self.results)
        
        print("\nModelX Self-Test")
        print("=" * 50)
        
        for name, success, details in self.results:
            icon = "PASS" if success else "FAIL"
            print(f"  {icon} {name}")
            if details:
                print(f"       {details}")
        
        print("-" * 50)
        print(f"Total: {total}/{total}  Passed: {passed}  Failed: {total - passed}")
        
        if passed == total:
            print("✓ All tests passed")
        else:
            print("✗ Some tests failed")
            sys.exit(1)


def run_self_test():
    test = SelfTest()
    
    # Config Manager
    try:
        from .config import ConfigManager
        cm = ConfigManager()
        _ = cm.load()
        test.add_result("Config Manager", True)
    except Exception as e:
        test.add_result("Config Manager", False, str(e))
    
    # Audio Capture
    try:
        from .audio import AudioCapture
        _ = AudioCapture()
        test.add_result("Audio Capture", True)
    except Exception as e:
        test.add_result("Audio Capture", False, str(e))
    
    # VAD
    try:
        from .audio import StreamingVAD
        _ = StreamingVAD()
        test.add_result("VAD", True)
    except Exception as e:
        test.add_result("VAD", False, str(e))
    
    # STT
    try:
        from .stt import WhisperTranscriber
        _ = WhisperTranscriber()
        test.add_result("STT (Whisper)", True)
    except Exception as e:
        test.add_result("STT (Whisper)", False, str(e))
    
    # TTS
    try:
        from .tts import PiperSynthesizer
        _ = PiperSynthesizer()
        test.add_result("TTS (Piper)", True)
    except Exception as e:
        test.add_result("TTS (Piper)", False, str(e))
    
    # LLM Client
    try:
        from .brain import get_provider
        _ = get_provider("anthropic", "test-key")
        test.add_result("LLM Client", True)
    except Exception as e:
        test.add_result("LLM Client", False, str(e))
    
    # Memory
    try:
        from .brain import ConversationMemory
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(suffix=".json") as f:
            _ = ConversationMemory(persistence_file=Path(f.name))
        test.add_result("Memory", True)
    except Exception as e:
        test.add_result("Memory", False, str(e))
    
    # Pipeline
    try:
        from .pipeline import AudioPipeline, PipelineConfig
        _ = AudioPipeline(PipelineConfig())
        test.add_result("Pipeline", True)
    except Exception as e:
        test.add_result("Pipeline", False, str(e))
    
    # UI
    try:
        from .ui import SimpleVoiceUI
        _ = SimpleVoiceUI()
        test.add_result("UI", True)
    except Exception as e:
        test.add_result("UI", False, str(e))
    
    # Voice Manager
    try:
        from .tts import VoiceManager
        vm = VoiceManager()
        voices = vm.list_available_voices()
        test.add_result("Voice Manager", True, f"{len(voices)} profiles")
    except Exception as e:
        test.add_result("Voice Manager", False, str(e))
    
    test.print_summary()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        prog="modelx",
        description="ModelX - AI Assistant Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  modelx              Start voice assistant (default)
  modelx voice        Start voice assistant (explicit)
  modelx doctor       Run system diagnostics
  modelx self-test    Run internal self-tests
  modelx --version    Show version

Examples:
  modelx                      # Start voice assistant
  modelx voice --setup        # Run voice setup wizard
  modelx doctor               # Check system health
  modelx self-test            # Run self-tests
  modelx --version            # Show version
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    
    # voice subcommand
    voice_parser = subparsers.add_parser("voice", help="Voice assistant")
    voice_parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    voice_parser.add_argument("--configure", action="store_true", help="Reconfigure settings")
    voice_parser.add_argument("--test-audio", action="store_true", help="Test audio devices")
    voice_parser.add_argument("--test-api", action="store_true", help="Test API connection")
    voice_parser.add_argument("--download-voices", action="store_true", help="List available voices")
    voice_parser.add_argument("--voice", choices=["professional", "casual", "clear"], help="Voice profile")
    voice_parser.add_argument("--provider", choices=["anthropic", "openai", "openrouter", "ollama"], help="LLM provider")
    voice_parser.add_argument("--api-key", help="API key (for quick setup)")
    
    # doctor subcommand
    subparsers.add_parser("doctor", help="Run system diagnostics")
    
    # self-test subcommand
    subparsers.add_parser("self-test", help="Run internal self-tests")
    
    # Global options (backward compat)
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard (alias for 'voice --setup')")
    parser.add_argument("--configure", action="store_true", help="Reconfigure settings")
    parser.add_argument("--test-audio", action="store_true", help="Test audio devices")
    parser.add_argument("--test-api", action="store_true", help="Test API connection")
    parser.add_argument("--download-voices", action="store_true", help="List available voices")
    parser.add_argument("--voice", choices=["professional", "casual", "clear"], help="Voice profile")
    parser.add_argument("--provider", choices=["anthropic", "openai", "openrouter", "ollama"], help="LLM provider")
    parser.add_argument("--api-key", help="API key (for quick setup)")
    
    args = parser.parse_args()
    
    # Handle version
    if args.version:
        import modelx_voice
        print(f"ModelX {modelx_voice.__version__}")
        return
    
    # Handle subcommands
    if args.command == "doctor":
        run_doctor()
        return
    elif args.command == "self-test":
        run_self_test()
        return
    elif args.command == "voice":
        asyncio.run(run_voice(
            setup=args.setup,
            configure=args.configure,
            test_audio=args.test_audio,
            test_api=args.test_api,
            download_voices=args.download_voices,
            voice=args.voice,
            provider=args.provider,
            api_key=args.api_key,
        ))
        return
    
    # Default: run voice assistant (backward compat with global flags)
    asyncio.run(run_voice(
        setup=args.setup,
        configure=args.configure,
        test_audio=args.test_audio,
        test_api=args.test_api,
        download_voices=args.download_voices,
        voice=args.voice,
        provider=args.provider,
        api_key=args.api_key,
    ))


if __name__ == "__main__":
    main()