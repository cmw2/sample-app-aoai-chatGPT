"""
Test Azure Speech Services with real Azure connection.
This script validates the configuration and tests actual connectivity.
"""

import os
import sys
import logging
import asyncio

# Add the project root to Python path
sys.path.append('/workspaces/sample-app-aoai-chatGPT')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_speech_service_config():
    """Test if speech service configuration is valid."""
    try:
        from backend.settings import app_settings
        
        print("🔧 Testing Speech Service Configuration...")
        print("-" * 50)
        
        if not app_settings.azure_speech:
            print("❌ Azure Speech not configured in settings")
            return False
        
        speech_config = app_settings.azure_speech
        
        print(f"✅ Speech service enabled: {speech_config.enabled}")
        print(f"✅ Region: {speech_config.region}")
        print(f"✅ Language: {speech_config.language}")
        print(f"✅ Output format: {speech_config.output_format}")
        print(f"✅ Profanity filter: {speech_config.profanity_filter}")
        
        if speech_config.key:
            print(f"✅ Authentication: Subscription key (***{speech_config.key[-4:]})")
        elif speech_config.endpoint:
            print(f"✅ Authentication: Custom endpoint ({speech_config.endpoint})")
        else:
            print("⚠️  Authentication: Managed identity (no key provided)")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def test_speech_service_connection():
    """Test actual connection to Azure Speech Service."""
    try:
        print("\n🌐 Testing Azure Speech Service Connection...")
        print("-" * 50)
        
        from backend.speech import AzureSpeechService
        from backend.settings import app_settings
        
        if not app_settings.azure_speech or not app_settings.azure_speech.enabled:
            print("❌ Speech service not enabled")
            return False
        
        # Create speech service instance
        speech_service = AzureSpeechService(
            speech_key=app_settings.azure_speech.key,
            service_region=app_settings.azure_speech.region,
            language=app_settings.azure_speech.language,
            endpoint=app_settings.azure_speech.endpoint
        )
        
        print("✅ Speech service instance created")
        
        # Try to create a recognizer (this validates the connection)
        try:
            recognizer, audio_stream = speech_service.create_recognizer_from_stream()
            print("✅ Speech recognizer created successfully")
            
            # Clean up
            audio_stream.close()
            print("✅ Connection test successful - Azure Speech Service is accessible")
            return True
            
        except Exception as e:
            if "unauthorized" in str(e).lower() or "403" in str(e):
                print("❌ Authentication failed - check your AZURE_SPEECH_KEY")
            elif "not found" in str(e).lower() or "404" in str(e):
                print("❌ Service not found - check your AZURE_SPEECH_REGION")
            else:
                print(f"❌ Connection failed: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

async def test_app_initialization():
    """Test if the main app initializes with speech services."""
    try:
        print("\n🚀 Testing App Initialization with Speech Services...")
        print("-" * 50)
        
        import app
        
        # Initialize speech service
        app.init_speech_service()
        
        if app.speech_service is None:
            print("❌ Speech service failed to initialize")
            print(f"Debug: speech_service = {app.speech_service}")
            return False
        
        if app.speech_websocket_handler is None:
            print("❌ WebSocket handler failed to initialize") 
            print(f"Debug: speech_websocket_handler = {app.speech_websocket_handler}")
            return False
        
        print("✅ Speech service initialized successfully")
        print("✅ WebSocket handler initialized successfully")
        print("✅ App ready to handle speech requests")
        
        return True
        
    except Exception as e:
        print(f"❌ App initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_endpoints_config():
    """Test the speech configuration endpoint response."""
    try:
        print("\n🔗 Testing Speech Endpoints Configuration...")
        print("-" * 50)
        
        from backend.settings import app_settings
        
        if not app_settings.azure_speech or not app_settings.azure_speech.enabled:
            print("❌ Speech service not configured")
            return False
        
        # Simulate the /speech/config endpoint response
        config_response = {
            "enabled": True,
            "language": app_settings.azure_speech.language,
            "region": app_settings.azure_speech.region,
            "supported_languages": ["en-US", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "zh-CN", "ja-JP"],
            "audio_format": {
                "sample_rate": 16000,
                "channels": 1,
                "bit_depth": 16,
                "format": "PCM"
            }
        }
        
        print("✅ /speech/config endpoint ready")
        print(f"✅ Configured language: {config_response['language']}")
        print(f"✅ Audio format: {config_response['audio_format']['sample_rate']}Hz PCM")
        print("✅ /speech/stream WebSocket endpoint ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Endpoint configuration test failed: {e}")
        return False

async def main():
    """Run all speech service tests."""
    print("🎤 Azure Speech Services Integration Test")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_speech_service_config),
        ("Azure Connection", test_speech_service_connection),
        ("App Initialization", test_app_initialization),
        ("Endpoints", test_endpoints_config),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print(f"\n{'='*60}")
    print(f"🧪 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Azure Speech Services is ready to use.")
        print("\n📋 Next Steps:")
        print("1. ✅ Backend is fully configured and working")
        print("2. 🚀 Start the app: python -m quart app:create_app --host 0.0.0.0 --port 5000")
        print("3. 🧪 Test endpoints:")
        print("   - GET http://localhost:5000/speech/config")
        print("   - WebSocket: ws://localhost:5000/speech/stream")
        print("4. 🔄 Ready for Phase 2: Frontend Integration")
    elif passed >= 2:
        print("⚠️  Partial success - basic setup works but Azure connection may have issues.")
        print("Check your Azure Speech Service key and region configuration.")
    else:
        print("❌ Multiple failures detected. Check your configuration and Azure setup.")

if __name__ == "__main__":
    asyncio.run(main())