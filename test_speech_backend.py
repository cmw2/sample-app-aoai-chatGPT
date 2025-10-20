"""
Test script to validate the Azure Speech Services backend implementation.
Run this to check if all components are properly configured.
"""

import os
import sys
import logging

# Add the project root to Python path
sys.path.append('/workspaces/sample-app-aoai-chatGPT')

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_imports():
    """Test if all required modules can be imported."""
    try:
        from backend.settings import app_settings
        print("✓ Settings module imported successfully")
        
        # Check speech settings
        if app_settings.azure_speech:
            print(f"✓ Speech settings configured: region={app_settings.azure_speech.region}, language={app_settings.azure_speech.language}")
        else:
            print("! Speech settings not configured (this is OK for testing)")
        
        from backend.speech import AzureSpeechService, SpeechWebSocketHandler, AudioProcessor
        print("✓ Speech service modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def test_speech_service_creation():
    """Test speech service creation (without actual Azure connection)."""
    try:
        from backend.speech import AzureSpeechService
        
        # Test with dummy credentials
        service = AzureSpeechService(
            speech_key="dummy_key",
            service_region="eastus",
            language="en-US"
        )
        print("✓ Speech service instance created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Speech service creation failed: {e}")
        return False

def test_audio_utils():
    """Test audio processing utilities."""
    try:
        from backend.speech import AudioProcessor, AudioBuffer
        
        # Test audio level calculation with dummy data
        dummy_audio = b'\x00\x10' * 100  # Some dummy PCM data
        level = AudioProcessor.calculate_audio_level(dummy_audio)
        print(f"✓ Audio level calculation works: {level}")
        
        # Test audio buffer
        buffer = AudioBuffer(max_size_seconds=5.0)
        buffer.add_data(dummy_audio)
        duration = buffer.get_duration_seconds()
        print(f"✓ Audio buffer works: stored {duration:.3f}s of audio")
        
        return True
        
    except Exception as e:
        print(f"✗ Audio utils test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Azure Speech Services Backend Implementation")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Speech Service Creation", test_speech_service_creation),
        ("Audio Utilities", test_audio_utils),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        
    print(f"\n{'='*50}")
    print(f"Tests: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All backend tests passed! Ready to install dependencies and test with Azure.")
        print("\nNext steps:")
        print("1. Set Azure Speech Service environment variables:")
        print("   - AZURE_SPEECH_KEY=<your_speech_key>")
        print("   - AZURE_SPEECH_REGION=<your_region>")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the app and test /speech/config endpoint")
    else:
        print("❌ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()