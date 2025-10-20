"""
Audio processing utilities for speech recognition.
"""

import logging
from typing import Optional, Tuple
import struct


class AudioProcessor:
    """
    Utility class for audio data processing and validation.
    """
    
    @staticmethod
    def validate_pcm_format(audio_data: bytes, 
                          expected_sample_rate: int = 16000,
                          expected_channels: int = 1,
                          expected_bit_depth: int = 16) -> bool:
        """
        Validate PCM audio format.
        
        Args:
            audio_data: Raw audio bytes
            expected_sample_rate: Expected sample rate in Hz
            expected_channels: Expected number of channels
            expected_bit_depth: Expected bit depth
            
        Returns:
            True if format appears valid
        """
        if len(audio_data) < 100:  # Minimum reasonable chunk size
            return False
        
        # For PCM 16-bit mono, each sample is 2 bytes
        bytes_per_sample = expected_bit_depth // 8 * expected_channels
        
        # Check if length is appropriate for the format
        if len(audio_data) % bytes_per_sample != 0:
            logging.warning(f"Audio data length {len(audio_data)} not aligned with expected format")
            return False
        
        return True
    
    @staticmethod
    def convert_to_pcm_16bit_mono(audio_data: bytes, 
                                 source_sample_rate: int = 44100,
                                 target_sample_rate: int = 16000) -> bytes:
        """
        Convert audio data to PCM 16-bit mono format.
        Note: This is a simplified conversion. For production use,
        consider using a proper audio library like librosa or pydub.
        
        Args:
            audio_data: Source audio bytes
            source_sample_rate: Source sample rate
            target_sample_rate: Target sample rate
            
        Returns:
            Converted audio data
        """
        # This is a placeholder for audio conversion
        # In production, you would use proper audio processing libraries
        logging.warning("Audio conversion not fully implemented - returning original data")
        return audio_data
    
    @staticmethod
    def calculate_audio_level(audio_data: bytes) -> float:
        """
        Calculate the audio level (RMS) for the given PCM data.
        Useful for voice activity detection.
        
        Args:
            audio_data: PCM 16-bit audio data
            
        Returns:
            RMS audio level (0.0 to 1.0)
        """
        if len(audio_data) < 2:
            return 0.0
        
        try:
            # Convert bytes to 16-bit signed integers
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            
            # Calculate RMS
            sum_squares = sum(sample * sample for sample in samples)
            rms = (sum_squares / len(samples)) ** 0.5
            
            # Normalize to 0-1 range (32767 is max value for 16-bit signed)
            return min(rms / 32767.0, 1.0)
            
        except Exception as e:
            logging.warning(f"Error calculating audio level: {e}")
            return 0.0
    
    @staticmethod
    def detect_silence(audio_data: bytes, threshold: float = 0.01) -> bool:
        """
        Detect if audio data represents silence.
        
        Args:
            audio_data: PCM audio data
            threshold: Silence threshold (0.0 to 1.0)
            
        Returns:
            True if audio is considered silence
        """
        level = AudioProcessor.calculate_audio_level(audio_data)
        return level < threshold
    
    @staticmethod
    def chunk_audio_data(audio_data: bytes, chunk_size_ms: int = 100, 
                        sample_rate: int = 16000) -> list:
        """
        Split audio data into time-based chunks.
        
        Args:
            audio_data: PCM 16-bit mono audio data
            chunk_size_ms: Chunk size in milliseconds
            sample_rate: Sample rate in Hz
            
        Returns:
            List of audio chunks
        """
        bytes_per_sample = 2  # 16-bit = 2 bytes
        samples_per_chunk = (sample_rate * chunk_size_ms) // 1000
        bytes_per_chunk = samples_per_chunk * bytes_per_sample
        
        chunks = []
        for i in range(0, len(audio_data), bytes_per_chunk):
            chunk = audio_data[i:i + bytes_per_chunk]
            if len(chunk) >= bytes_per_chunk // 2:  # Include partial chunks if substantial
                chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def apply_noise_gate(audio_data: bytes, threshold: float = 0.02) -> bytes:
        """
        Apply a simple noise gate to reduce background noise.
        
        Args:
            audio_data: PCM 16-bit audio data
            threshold: Gate threshold (0.0 to 1.0)
            
        Returns:
            Processed audio data
        """
        try:
            # Convert to samples
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            
            # Apply noise gate
            processed_samples = []
            for sample in samples:
                normalized_sample = abs(sample) / 32767.0
                if normalized_sample > threshold:
                    processed_samples.append(sample)
                else:
                    processed_samples.append(0)  # Silence
            
            # Convert back to bytes
            return struct.pack(f'<{len(processed_samples)}h', *processed_samples)
            
        except Exception as e:
            logging.warning(f"Error applying noise gate: {e}")
            return audio_data  # Return original on error


class AudioBuffer:
    """
    Circular buffer for streaming audio data.
    """
    
    def __init__(self, max_size_seconds: float = 30.0, sample_rate: int = 16000):
        """
        Initialize audio buffer.
        
        Args:
            max_size_seconds: Maximum buffer size in seconds
            sample_rate: Audio sample rate
        """
        self.sample_rate = sample_rate
        self.bytes_per_sample = 2  # 16-bit PCM
        self.max_size_bytes = int(max_size_seconds * sample_rate * self.bytes_per_sample)
        self.buffer = bytearray()
        
    def add_data(self, audio_data: bytes):
        """Add audio data to the buffer."""
        self.buffer.extend(audio_data)
        
        # Trim buffer if it exceeds max size
        if len(self.buffer) > self.max_size_bytes:
            excess = len(self.buffer) - self.max_size_bytes
            self.buffer = self.buffer[excess:]
    
    def get_recent_data(self, duration_seconds: float) -> bytes:
        """
        Get recent audio data from the buffer.
        
        Args:
            duration_seconds: Duration of audio to retrieve
            
        Returns:
            Recent audio data
        """
        bytes_requested = int(duration_seconds * self.sample_rate * self.bytes_per_sample)
        
        if len(self.buffer) <= bytes_requested:
            return bytes(self.buffer)
        
        return bytes(self.buffer[-bytes_requested:])
    
    def clear(self):
        """Clear the buffer."""
        self.buffer.clear()
    
    def get_duration_seconds(self) -> float:
        """Get the current buffer duration in seconds."""
        return len(self.buffer) / (self.sample_rate * self.bytes_per_sample)