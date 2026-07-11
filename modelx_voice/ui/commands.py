import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class CommandType(Enum):
    STOP = "stop"
    PAUSE = "pause"
    CLEAR = "clear"
    SAVE = "save"
    HELP = "help"
    SWITCH_VOICE = "switch_voice"
    STATUS = "status"
    REPEAT = "repeat"
    NONE = "none"


@dataclass
class VoiceCommand:
    type: CommandType
    args: dict[str, Any] = None
    raw_text: str = ""

    def __post_init__(self):
        if self.args is None:
            self.args = {}


COMMAND_PATTERNS = {
    CommandType.STOP: [
        r"^(stop|quit|exit|goodbye|bye)$",
        r"^stop listening$",
    ],
    CommandType.PAUSE: [
        r"^(pause|wait|hold on)$",
    ],
    CommandType.CLEAR: [
        r"^(clear|clear history|reset|forget)$",
        r"^clear conversation$",
    ],
    CommandType.SAVE: [
        r"^(save|save conversation|export)$",
    ],
    CommandType.HELP: [
        r"^(help|commands|what can you do)$",
    ],
    CommandType.SWITCH_VOICE: [
        r"^(switch voice|change voice|use voice)\s+(\w+)$",
        r"^voice\s+(\w+)$",
    ],
    CommandType.STATUS: [
        r"^(status|stats|info)$",
    ],
    CommandType.REPEAT: [
        r"^(repeat|say that again|say again)$",
    ],
}

VOICE_ALIASES = {
    "professional": "professional",
    "pro": "professional",
    "male": "professional",
    "casual": "casual",
    "friendly": "casual",
    "female": "casual",
    "clear": "clear",
    "clarity": "clear",
    "neutral": "clear",
}


class CommandProcessor:
    def __init__(self):
        self._commands = COMMAND_PATTERNS
        self._last_response: str = ""

    def process(self, text: str) -> VoiceCommand:
        text_clean = text.lower().strip()
        text_clean = re.sub(r"[.!?]+$", "", text_clean)

        for cmd_type, patterns in self._commands.items():
            for pattern in patterns:
                match = re.match(pattern, text_clean, re.IGNORECASE)
                if match:
                    args = {}
                    if cmd_type == CommandType.SWITCH_VOICE and match.groups():
                        voice_name = match.group(match.lastindex or 1).lower()
                        args["voice"] = VOICE_ALIASES.get(voice_name, voice_name)
                    return VoiceCommand(type=cmd_type, args=args, raw_text=text)

        return VoiceCommand(type=CommandType.NONE, raw_text=text)

    def is_command(self, text: str) -> bool:
        return self.process(text).type != CommandType.NONE

    def get_help_text(self) -> str:
        return """
Available voice commands:
  • "Stop" / "Quit" / "Exit" - Stop listening and exit
  • "Pause" / "Wait" - Pause the response
  • "Clear" / "Reset" - Clear conversation history
  • "Save" - Save conversation to file
  • "Help" - Show this help
  • "Switch voice [professional|casual|clear]" - Change voice
  • "Status" - Show system status
  • "Repeat" - Repeat last response
        """.strip()

    def set_last_response(self, response: str):
        self._last_response = response

    def get_last_response(self) -> str:
        return self._last_response
