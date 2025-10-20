# Implementation Plan: Azure Speech Services with WebSocket Streaming

## **Architecture Overview**

```
[React Frontend] ←→ [WebSocket] ←→ [Python Backend] ←→ [Azure Speech Services]
     ↓                                     ↓
[Audio Capture]                    [Real-time Transcription]
     ↓                                     ↓
[Live Text Display] ←← [WebSocket] ←← [Text Streaming Back]
```

## **Phase 1: Backend Infrastructure** 

### **1.1 Add Azure Speech Dependencies**
- Add `azure-cognitiveservices-speech` to `requirements.txt`
- Add WebSocket support to Quart app (already has WebSocket capability)
- Configure Azure Speech Service environment variables

### **1.2 Create Speech Service Configuration**
- Add Speech Service settings to `backend/settings.py`
- Support both API key and managed identity authentication
- Configure regional endpoints and language settings

### **1.3 Implement WebSocket Speech Endpoint**
- Create `/speech/stream` WebSocket endpoint in `app.py`
- Handle binary audio data streaming from frontend
- Initialize Azure Speech SDK with streaming recognition
- Forward real-time transcription results back to client

### **1.4 Audio Processing Pipeline**
- Implement audio chunk buffering and streaming
- Handle Speech SDK connection lifecycle
- Add error handling for network interruptions
- Support multiple concurrent speech sessions

## **Phase 2: Frontend Speech Integration**

### **2.1 Add Speech UI Components**
- Create `SpeechInput` component in `frontend/src/components/`
- Add microphone button to existing `QuestionInput` component
- Implement real-time transcription display
- Add visual feedback (recording indicator, audio levels)

### **2.2 WebSocket Client Implementation**
- Create WebSocket service in `frontend/src/services/`
- Handle binary audio streaming to backend
- Process real-time transcription updates
- Manage connection state and error recovery

### **2.3 Audio Capture & Processing**
- Implement browser MediaRecorder API integration
- Add audio format conversion (to PCM/WAV as needed)
- Handle microphone permissions and device selection
- Implement audio chunking for streaming

### **2.4 UI/UX Enhancements**
- Add toggle between text and speech input modes
- Show live transcription with confidence indicators
- Implement "push-to-talk" and "continuous listening" modes
- Add speech input history and editing capabilities

## **Phase 3: Integration & Enhancement**

### **3.1 Chat Flow Integration**
- Connect transcribed text to existing chat submission
- Maintain conversation context and history
- Support mixed input modes (text + speech)
- Preserve existing chat features (image upload, etc.)

### **3.2 Performance Optimization**
- Implement audio compression and optimization
- Add client-side audio preprocessing
- Optimize WebSocket message size and frequency
- Cache and reuse Speech Service connections

### **3.3 Error Handling & Resilience**
- Add comprehensive error handling for all failure modes
- Implement automatic reconnection logic
- Handle microphone access errors gracefully
- Add fallback to text input when speech fails

## **Phase 4: Configuration & Deployment**

### **4.1 Environment Configuration**
- Add Speech Service environment variables
- Update deployment configuration (Azure/Docker)
- Configure CORS policies for WebSocket connections
- Add feature flags for speech functionality

### **4.2 Security & Privacy**
- Implement authentication for speech endpoints
- Add audio data privacy controls
- Configure secure WebSocket connections (WSS)
- Add rate limiting for speech requests

## **Detailed File Changes Required:**

### **Backend Files:**
1. **`requirements.txt`** - Add Azure Speech SDK
2. **`backend/settings.py`** - Add speech service configuration
3. **`app.py`** - Add WebSocket speech endpoint
4. **`backend/speech/`** (new) - Speech service integration modules

### **Frontend Files:**
1. **`frontend/src/components/SpeechInput/`** (new) - Speech components
2. **`frontend/src/services/speechService.ts`** (new) - WebSocket client
3. **`frontend/src/components/QuestionInput/QuestionInput.tsx`** - Integration
4. **`frontend/package.json`** - Add audio processing dependencies

### **Configuration Files:**
1. **`.env`** - Add Speech Service environment variables
2. **`infra/main.bicep`** - Add Speech Service provisioning
3. **`azure.yaml`** - Update deployment configuration

## **Implementation Timeline:**

- **Week 1:** Backend infrastructure and Speech Service integration
- **Week 2:** Frontend audio capture and WebSocket client
- **Week 3:** UI components and chat flow integration  
- **Week 4:** Testing, optimization, and deployment

## **Testing Strategy:**

1. **Unit Tests:** Speech service modules, audio processing
2. **Integration Tests:** WebSocket communication, end-to-end flow
3. **Browser Tests:** Cross-browser audio capture compatibility
4. **Performance Tests:** Latency measurements, concurrent users
5. **Accessibility Tests:** Keyboard navigation, screen reader support

## **Success Criteria:**

- **Latency:** < 500ms from speech to text display
- **Accuracy:** > 95% for clear English speech
- **Reliability:** < 1% connection failure rate
- **User Experience:** Seamless integration with existing chat flow
- **Performance:** Support 50+ concurrent speech sessions

## **Progress Tracking:**

**✅ PHASE 1 COMPLETED - Backend Infrastructure**
- [x] Phase 1.1: Add Azure Speech Dependencies ✅ 
- [x] Phase 1.2: Create Speech Service Configuration ✅
- [x] Phase 1.3: Implement WebSocket Speech Endpoint ✅
- [x] Phase 1.4: Audio Processing Pipeline ✅

**🔄 NEXT: PHASE 2 - Frontend Speech Integration**
- [ ] Phase 2.1: Add Speech UI Components
- [ ] Phase 2.2: WebSocket Client Implementation
- [ ] Phase 2.3: Audio Capture & Processing
- [ ] Phase 2.4: UI/UX Enhancements

**📋 REMAINING PHASES**
- [ ] Phase 3.1: Chat Flow Integration
- [ ] Phase 3.2: Performance Optimization
- [ ] Phase 3.3: Error Handling & Resilience
- [ ] Phase 4.1: Environment Configuration
- [ ] Phase 4.2: Security & Privacy

## **Phase 1 Summary (COMPLETED ✅)**

**What was implemented:**
1. **Azure Speech SDK Integration** - Added `azure-cognitiveservices-speech==1.38.0` to requirements.txt
2. **Speech Service Configuration** - Added `_AzureSpeechSettings` class with support for API key and managed identity authentication
3. **WebSocket Endpoints** - Created `/speech/stream` WebSocket endpoint and `/speech/config` REST endpoint
4. **Speech Service Module** - Complete backend speech service with:
   - `AzureSpeechService` - Core speech recognition functionality
   - `SpeechWebSocketHandler` - WebSocket connection management
   - `AudioProcessor` & `AudioBuffer` - Audio processing utilities
5. **Integration** - Integrated speech services into main Quart app with proper initialization

**Files Created/Modified:**
- ✅ `requirements.txt` - Added Azure Speech SDK
- ✅ `backend/settings.py` - Added speech configuration
- ✅ `backend/speech/__init__.py` - Module exports
- ✅ `backend/speech/speech_service.py` - Core speech service
- ✅ `backend/speech/websocket_handler.py` - WebSocket management  
- ✅ `backend/speech/audio_utils.py` - Audio processing utilities
- ✅ `app.py` - WebSocket endpoints and initialization
- ✅ `test_speech_backend.py` - Backend validation script

**Testing Results:**
- ✅ All module imports successful
- ✅ Speech service creation works  
- ✅ Audio processing utilities functional
- ✅ Ready for Azure Speech Service integration

---

**Created:** October 20, 2025  
**Status:** Phase 1 Complete ✅ - Ready for Phase 2 (Frontend Integration)