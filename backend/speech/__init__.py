"""
Azure Speech Services integration module.
Provides WebSocket-based real-time speech-to-text functionality.
"""

from .speech_service import AzureSpeechService
from .websocket_handler import SpeechWebSocketHandler
from .audio_utils import AudioProcessor, AudioBuffer

__all__ = ['AzureSpeechService', 'SpeechWebSocketHandler', 'AudioProcessor', 'AudioBuffer']