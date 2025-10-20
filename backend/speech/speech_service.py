"""
Azure Speech Services integration for real-time speech-to-text.
"""

import asyncio
import logging
import json
from typing import Optional, Callable, Any
import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential


class AzureSpeechService:
    """
    Azure Speech Services wrapper for real-time speech recognition.
    Handles connection lifecycle, audio streaming, and result callbacks.
    """
    
    def __init__(self, 
                 speech_key: Optional[str] = None,
                 service_region: str = "eastus",
                 language: str = "en-US",
                 endpoint: Optional[str] = None):
        """
        Initialize the Azure Speech Service.
        
        Args:
            speech_key: Azure Speech service subscription key (optional if using managed identity)
            service_region: Azure region for the speech service
            language: Language code for speech recognition (e.g., 'en-US')
            endpoint: Custom endpoint URL (optional)
        """
        self.speech_key = speech_key
        self.service_region = service_region
        self.language = language
        self.endpoint = endpoint
        self.speech_config = None
        self.audio_config = None
        self.speech_recognizer = None
        self.is_recognizing = False
        
        # Callback functions
        self.on_recognizing: Optional[Callable[[str], None]] = None
        self.on_recognized: Optional[Callable[[str, dict], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_session_started: Optional[Callable[[], None]] = None
        self.on_session_stopped: Optional[Callable[[], None]] = None
        
        self._setup_speech_config()
    
    def _setup_speech_config(self):
        """Set up the Azure Speech SDK configuration."""
        try:
            if self.speech_key:
                # Use subscription key authentication
                self.speech_config = speechsdk.SpeechConfig(
                    subscription=self.speech_key, 
                    region=self.service_region
                )
                logging.debug(f"Speech service initialized with key for region: {self.service_region}")
            else:
                # Use managed identity authentication
                if self.endpoint:
                    self.speech_config = speechsdk.SpeechConfig(
                        endpoint=self.endpoint
                    )
                else:
                    # Fallback to default endpoint with managed identity
                    endpoint = f"https://{self.service_region}.api.cognitive.microsoft.com/"
                    self.speech_config = speechsdk.SpeechConfig(endpoint=endpoint)
                logging.debug("Speech service initialized with managed identity")
            
            # Configure speech recognition settings
            self.speech_config.speech_recognition_language = self.language
            self.speech_config.output_format = speechsdk.OutputFormat.Detailed
            
            # Enable profanity filtering
            self.speech_config.set_profanity(speechsdk.ProfanityOption.Masked)
            
            # Configure for continuous recognition
            self.speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_EnableAudioLogging, 
                "false"
            )
            
        except Exception as e:
            logging.error(f"Failed to setup speech config: {e}")
            raise
    
    def create_recognizer_from_stream(self):
        """
        Create a speech recognizer that can accept streaming audio data.
        
        Returns:
            Tuple of (recognizer, audio_stream) for streaming audio input
        """
        try:
            # Create push audio stream
            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
            
            # Create speech recognizer
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Note: Event handlers are set up per-session in the WebSocket handler
            # to support multiple concurrent users properly
            
            return recognizer, audio_stream
            
        except Exception as e:
            logging.error(f"Failed to create speech recognizer: {e}")
            raise
    
    def _on_recognizing(self, evt):
        """Handle partial recognition results (real-time transcription)."""
        if self.on_recognizing and evt.result.text:
            try:
                self.on_recognizing(evt.result.text)
            except Exception as e:
                logging.error(f"Error in recognizing callback: {e}")
    
    def _on_recognized(self, evt):
        """Handle final recognition results."""
        if self.on_recognized and evt.result.text:
            try:
                # Create result data with confidence and timing info
                result_data = {
                    'text': evt.result.text,
                    'confidence': getattr(evt.result, 'confidence', 1.0),
                    'offset': evt.result.offset,
                    'duration': evt.result.duration,
                    'reason': str(evt.result.reason)
                }
                self.on_recognized(evt.result.text, result_data)
            except Exception as e:
                logging.error(f"Error in recognized callback: {e}")
    
    def _on_session_started(self, evt):
        """Handle session started event."""
        logging.debug("Speech recognition session started")
        self.is_recognizing = True
        if self.on_session_started:
            try:
                self.on_session_started()
            except Exception as e:
                logging.error(f"Error in session started callback: {e}")
    
    def _on_session_stopped(self, evt):
        """Handle session stopped event."""
        logging.debug("Speech recognition session stopped")
        self.is_recognizing = False
        if self.on_session_stopped:
            try:
                self.on_session_stopped()
            except Exception as e:
                logging.error(f"Error in session stopped callback: {e}")
    
    def _on_canceled(self, evt):
        """Handle recognition canceled event."""
        if evt.reason == speechsdk.CancellationReason.Error:
            error_msg = f"Speech recognition error: {evt.error_details}"
            logging.error(error_msg)
            if self.on_error:
                try:
                    self.on_error(error_msg)
                except Exception as e:
                    logging.error(f"Error in error callback: {e}")
        else:
            logging.info(f"Speech recognition canceled: {evt.reason}")
    
    def add_phrase_hints(self, recognizer, phrases: list):
        """
        Add phrase hints to improve recognition accuracy.
        
        Args:
            recognizer: The speech recognizer instance
            phrases: List of phrases that might be spoken
        """
        if not phrases:
            return
            
        try:
            phrase_list_grammar = speechsdk.PhraseListGrammar.from_recognizer(recognizer)
            for phrase in phrases:
                phrase_list_grammar.addPhrase(phrase)
            logging.debug(f"Added {len(phrases)} phrase hints to recognizer")
        except Exception as e:
            logging.warning(f"Failed to add phrase hints: {e}")
    
    def validate_audio_format(self, audio_data: bytes) -> bool:
        """
        Validate that audio data is in the expected format.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            True if audio format is valid
        """
        # Basic validation - check for minimum length
        if len(audio_data) < 1024:  # Minimum reasonable audio chunk
            return False
        
        # Could add more sophisticated format validation here
        # For now, we trust the client to send PCM 16-bit 16kHz mono
        return True
    
    def create_audio_format(self) -> speechsdk.audio.AudioStreamFormat:
        """
        Create audio format specification for the speech service.
        
        Returns:
            AudioStreamFormat configured for 16kHz 16-bit mono PCM
        """
        return speechsdk.audio.AudioStreamFormat(
            samples_per_second=16000,
            bits_per_sample=16,
            channels=1
        )