"""
WebSocket handler for real-time speech-to-text streaming.
"""

import asyncio
import json
import logging
from typing import Dict, Optional
from quart import websocket
import azure.cognitiveservices.speech as speechsdk
from .speech_service import AzureSpeechService


class SpeechWebSocketHandler:
    """
    Handles WebSocket connections for real-time speech recognition.
    Manages multiple concurrent speech recognition sessions.
    """
    
    def __init__(self, speech_service: AzureSpeechService):
        """
        Initialize the WebSocket handler.
        
        Args:
            speech_service: Configured AzureSpeechService instance
        """
        from backend.settings import app_settings
        self.speech_service = speech_service
        self.active_sessions: Dict[str, dict] = {}
        # Get max sessions from settings, with fallback
        self.max_concurrent_sessions = (
            app_settings.azure_speech.max_concurrent_sessions 
            if app_settings.azure_speech else 100
        )
    
    def can_accept_new_session(self) -> bool:
        """Check if we can accept a new speech session."""
        active_count = self.get_active_session_count()
        return active_count < self.max_concurrent_sessions
    
    async def handle_websocket_connection(self, session_id: str):
        """
        Handle a WebSocket connection for speech recognition.
        
        Args:
            session_id: Unique identifier for this speech session
        """
        recognizer = None
        audio_stream = None
        
        try:
            # Check if we can accept new sessions
            if not self.can_accept_new_session():
                await self._send_error(session_id, 
                    f"Speech service at capacity. Maximum {self.max_concurrent_sessions} concurrent sessions allowed.")
                return
            
            logging.info(f"Starting speech recognition session: {session_id} ({self.get_active_session_count() + 1}/{self.max_concurrent_sessions})")
            
            # Create speech recognizer and audio stream
            recognizer, audio_stream = self.speech_service.create_recognizer_from_stream()
            
            # Store session info
            self.active_sessions[session_id] = {
                'recognizer': recognizer,
                'audio_stream': audio_stream,
                'is_active': True
            }
            
            # Set up callbacks for this specific recognizer (not the shared service)
            def on_recognizing(evt):
                if evt.result.text:
                    asyncio.create_task(self._send_partial_result(session_id, evt.result.text))
            
            def on_recognized(evt):
                if evt.result.text:
                    result_data = {
                        'text': evt.result.text,
                        'confidence': getattr(evt.result, 'confidence', 1.0),
                        'offset': evt.result.offset,
                        'duration': evt.result.duration,
                        'reason': str(evt.result.reason)
                    }
                    asyncio.create_task(self._send_final_result(session_id, evt.result.text, result_data))
            
            def on_session_started(evt):
                logging.debug(f"Speech recognition session started: {session_id}")
            
            def on_session_stopped(evt):
                logging.debug(f"Speech recognition session stopped: {session_id}")
            
            def on_canceled(evt):
                if evt.reason == speechsdk.CancellationReason.Error:
                    error_msg = f"Speech recognition error: {evt.error_details}"
                    logging.error(error_msg)
                    asyncio.create_task(self._send_error(session_id, error_msg))
                else:
                    logging.info(f"Speech recognition canceled: {evt.reason}")
            
            # Connect callbacks to this specific recognizer
            recognizer.recognizing.connect(on_recognizing)
            recognizer.recognized.connect(on_recognized)
            recognizer.session_started.connect(on_session_started)
            recognizer.session_stopped.connect(on_session_stopped)
            recognizer.canceled.connect(on_canceled)
            
            # Start continuous recognition
            recognizer.start_continuous_recognition_async()
            
            # Send session started message
            await self._send_message(session_id, {
                'type': 'session_started',
                'session_id': session_id,
                'status': 'ready'
            })
            
            # Handle incoming WebSocket messages
            async for message in websocket.websocket.iter_message():
                if isinstance(message, bytes):
                    # Audio data received
                    await self._handle_audio_data(session_id, message)
                elif isinstance(message, str):
                    # Control message received
                    await self._handle_control_message(session_id, message)
                    
        except Exception as e:
            logging.error(f"Error in speech WebSocket session {session_id}: {e}")
            await self._send_error(session_id, str(e))
            
        finally:
            await self._cleanup_session(session_id, recognizer, audio_stream)
    
    async def _handle_audio_data(self, session_id: str, audio_data: bytes):
        """
        Handle incoming audio data from the WebSocket.
        
        Args:
            session_id: Session identifier
            audio_data: Raw audio bytes
        """
        try:
            session = self.active_sessions.get(session_id)
            if not session or not session['is_active']:
                return
            
            # Validate audio format
            if not self.speech_service.validate_audio_format(audio_data):
                await self._send_error(session_id, "Invalid audio format")
                return
            
            # Stream audio data to Speech SDK
            audio_stream = session['audio_stream']
            audio_stream.write(audio_data)
            
        except Exception as e:
            logging.error(f"Error handling audio data for session {session_id}: {e}")
            await self._send_error(session_id, str(e))
    
    async def _handle_control_message(self, session_id: str, message: str):
        """
        Handle control messages from the WebSocket client.
        
        Args:
            session_id: Session identifier
            message: JSON control message
        """
        try:
            data = json.loads(message)
            command = data.get('command')
            
            if command == 'stop_recognition':
                await self._stop_recognition(session_id)
            elif command == 'add_phrase_hints':
                phrases = data.get('phrases', [])
                await self._add_phrase_hints(session_id, phrases)
            elif command == 'configure':
                config = data.get('config', {})
                await self._configure_session(session_id, config)
            else:
                await self._send_error(session_id, f"Unknown command: {command}")
                
        except json.JSONDecodeError:
            await self._send_error(session_id, "Invalid JSON in control message")
        except Exception as e:
            logging.error(f"Error handling control message for session {session_id}: {e}")
            await self._send_error(session_id, str(e))
    
    async def _stop_recognition(self, session_id: str):
        """Stop speech recognition for a session."""
        try:
            session = self.active_sessions.get(session_id)
            if session and session['is_active']:
                recognizer = session['recognizer']
                audio_stream = session['audio_stream']
                
                # Stop recognition and close stream
                recognizer.stop_continuous_recognition_async()
                audio_stream.close()
                
                session['is_active'] = False
                
                await self._send_message(session_id, {
                    'type': 'session_stopped',
                    'session_id': session_id
                })
                
        except Exception as e:
            logging.error(f"Error stopping recognition for session {session_id}: {e}")
    
    async def _add_phrase_hints(self, session_id: str, phrases: list):
        """Add phrase hints to improve recognition accuracy."""
        try:
            session = self.active_sessions.get(session_id)
            if session and session['is_active']:
                recognizer = session['recognizer']
                self.speech_service.add_phrase_hints(recognizer, phrases)
                
                await self._send_message(session_id, {
                    'type': 'phrase_hints_added',
                    'count': len(phrases)
                })
                
        except Exception as e:
            logging.error(f"Error adding phrase hints for session {session_id}: {e}")
    
    async def _configure_session(self, session_id: str, config: dict):
        """Configure session settings dynamically."""
        try:
            # Handle configuration changes
            language = config.get('language')
            if language:
                # Note: Changing language requires recreating the recognizer
                logging.info(f"Language change requested for session {session_id}: {language}")
                # This would require stopping current session and starting a new one
            
            await self._send_message(session_id, {
                'type': 'configuration_updated',
                'config': config
            })
            
        except Exception as e:
            logging.error(f"Error configuring session {session_id}: {e}")
    
    async def _send_partial_result(self, session_id: str, text: str):
        """Send partial recognition result to the client."""
        await self._send_message(session_id, {
            'type': 'recognizing',
            'text': text,
            'is_final': False
        })
    
    async def _send_final_result(self, session_id: str, text: str, result_data: dict):
        """Send final recognition result to the client."""
        await self._send_message(session_id, {
            'type': 'recognized',
            'text': text,
            'is_final': True,
            'confidence': result_data.get('confidence', 1.0),
            'offset': result_data.get('offset', 0),
            'duration': result_data.get('duration', 0)
        })
    
    async def _send_error(self, session_id: str, error_message: str):
        """Send error message to the client."""
        await self._send_message(session_id, {
            'type': 'error',
            'error': error_message
        })
    
    async def _send_message(self, session_id: str, message: dict):
        """Send a message to the WebSocket client."""
        try:
            message['session_id'] = session_id
            message['timestamp'] = asyncio.get_event_loop().time()
            await websocket.send(json.dumps(message))
        except Exception as e:
            logging.error(f"Error sending message to session {session_id}: {e}")
    
    async def _cleanup_session(self, session_id: str, recognizer=None, audio_stream=None):
        """Clean up resources for a speech recognition session."""
        try:
            logging.info(f"Cleaning up speech recognition session: {session_id}")
            
            # Stop recognizer if still running
            if recognizer:
                try:
                    recognizer.stop_continuous_recognition_async()
                except Exception as e:
                    logging.warning(f"Error stopping recognizer: {e}")
            
            # Close audio stream
            if audio_stream:
                try:
                    audio_stream.close()
                except Exception as e:
                    logging.warning(f"Error closing audio stream: {e}")
            
            # Remove session from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                
        except Exception as e:
            logging.error(f"Error cleaning up session {session_id}: {e}")
    
    def get_active_session_count(self) -> int:
        """Get the number of active speech recognition sessions."""
        return len([s for s in self.active_sessions.values() if s.get('is_active', False)])
    
    async def cleanup_all_sessions(self):
        """Clean up all active sessions (for shutdown)."""
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            session = self.active_sessions.get(session_id)
            if session:
                await self._cleanup_session(
                    session_id, 
                    session.get('recognizer'), 
                    session.get('audio_stream')
                )