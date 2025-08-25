"""
BUDDY 2.0 Voice Web Server - Web-based Voice Interaction
=======================================================

This module provides a web interface for voice interactions using WebRTC,
Web Speech API, and real-time communication with the BUDDY AI backend.

Features:
- Browser-based voice recording and playback
- Real-time voice streaming
- WebRTC voice communication
- Voice chat web interface
- Multi-user voice sessions
- Voice command processing through web
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import logging
import base64
import wave
import io
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel

from .voice_interface import VoiceAssistant, VoicePersonality, quick_voice_test
from .voice_engine import VoiceConfig

logger = logging.getLogger(__name__)

# Pydantic models for API
class VoiceRequest(BaseModel):
    audio_data: str  # Base64 encoded audio
    format: str = "wav"
    sample_rate: int = 16000

class VoiceResponse(BaseModel):
    text: str
    audio_data: Optional[str] = None  # Base64 encoded response audio
    confidence: float
    processing_time: float
    session_id: str

class VoiceSessionConfig(BaseModel):
    personality_name: str = "BUDDY"
    voice_style: str = "friendly"
    language: str = "en-US"
    wake_words: List[str] = ["buddy", "hey buddy"]

# FastAPI app
app = FastAPI(title="BUDDY Voice Web Server", version="2.0")

# Global state
active_sessions: Dict[str, VoiceAssistant] = {}
websocket_connections: Dict[str, WebSocket] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize voice server on startup"""
    logger.info("Starting BUDDY Voice Web Server...")
    
    # Test voice capabilities
    test_results = await quick_voice_test()
    logger.info(f"Voice system status: {test_results.get('overall_status', 'unknown')}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down BUDDY Voice Web Server...")
    
    # Close all active sessions
    for session_id, assistant in active_sessions.items():
        try:
            await assistant.conversation_manager.end_conversation()
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {e}")

# REST API endpoints

@app.get("/")
async def get_voice_interface():
    """Serve the main voice interface HTML page"""
    return HTMLResponse(content=get_voice_interface_html(), media_type="text/html")

@app.post("/api/voice/process")
async def process_voice_command(request: VoiceRequest) -> VoiceResponse:
    """Process a voice command via REST API"""
    try:
        # Decode audio data
        audio_bytes = base64.b64decode(request.audio_data)
        
        # Create or get voice assistant
        session_id = f"rest_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if session_id not in active_sessions:
            assistant = VoiceAssistant()
            await assistant.initialize()
            active_sessions[session_id] = assistant
        else:
            assistant = active_sessions[session_id]
        
        # Process voice command
        start_time = datetime.now()
        result = await assistant.conversation_manager.process_single_command(audio_bytes)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Extract results
        text = result.get('stt_result', {}).get('text', '')
        confidence = result.get('stt_result', {}).get('confidence', 0.0)
        response_text = result.get('response', 'No response generated')
        
        # Generate response audio (optional)
        response_audio = None
        if response_text:
            # Convert response to audio
            tts_result = await assistant.conversation_manager.voice_engine.tts.speak_text(response_text)
            if tts_result.get('success') and 'audio_data' in tts_result:
                response_audio = base64.b64encode(tts_result['audio_data']).decode('utf-8')
        
        return VoiceResponse(
            text=response_text,
            audio_data=response_audio,
            confidence=confidence,
            processing_time=processing_time,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {e}")

@app.post("/api/voice/session/start")
async def start_voice_session(config: VoiceSessionConfig) -> Dict[str, str]:
    """Start a new voice session"""
    try:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create personality
        personality = VoicePersonality(
            name=config.personality_name,
            voice_style=config.voice_style
        )
        
        # Create voice assistant
        assistant = VoiceAssistant(personality)
        await assistant.initialize()
        
        # Enable wake words if configured
        if config.wake_words:
            await assistant.enable_wake_word(config.wake_words)
        
        # Start conversation
        await assistant.conversation_manager.start_conversation()
        
        # Store session
        active_sessions[session_id] = assistant
        
        logger.info(f"Voice session {session_id} started")
        
        return {
            "session_id": session_id,
            "status": "active",
            "personality": config.personality_name
        }
        
    except Exception as e:
        logger.error(f"Failed to start voice session: {e}")
        raise HTTPException(status_code=500, detail=f"Session start failed: {e}")

@app.delete("/api/voice/session/{session_id}")
async def end_voice_session(session_id: str) -> Dict[str, str]:
    """End a voice session"""
    try:
        if session_id in active_sessions:
            assistant = active_sessions[session_id]
            await assistant.conversation_manager.end_conversation()
            del active_sessions[session_id]
            
            logger.info(f"Voice session {session_id} ended")
            
            return {
                "session_id": session_id,
                "status": "ended"
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except Exception as e:
        logger.error(f"Failed to end voice session: {e}")
        raise HTTPException(status_code=500, detail=f"Session end failed: {e}")

@app.get("/api/voice/test")
async def test_voice_capabilities() -> Dict[str, Any]:
    """Test voice system capabilities"""
    try:
        test_results = await quick_voice_test()
        return test_results
    except Exception as e:
        logger.error(f"Voice test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice test failed: {e}")

# WebSocket endpoints for real-time voice interaction

@app.websocket("/ws/voice/{session_id}")
async def voice_websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time voice interaction"""
    await websocket.accept()
    websocket_connections[session_id] = websocket
    
    try:
        logger.info(f"WebSocket connection established for session {session_id}")
        
        # Get or create voice assistant
        if session_id not in active_sessions:
            assistant = VoiceAssistant()
            await assistant.initialize()
            await assistant.conversation_manager.start_conversation()
            active_sessions[session_id] = assistant
        else:
            assistant = active_sessions[session_id]
        
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "message": "Voice WebSocket connected",
            "session_id": session_id
        })
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_websocket_message(websocket, session_id, data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error for session {session_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Cleanup
        if session_id in websocket_connections:
            del websocket_connections[session_id]
        
        if session_id in active_sessions:
            try:
                await active_sessions[session_id].conversation_manager.end_conversation()
                del active_sessions[session_id]
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {e}")

async def handle_websocket_message(websocket: WebSocket, session_id: str, data: Dict):
    """Handle incoming WebSocket messages"""
    try:
        message_type = data.get("type")
        
        if message_type == "voice_data":
            # Process voice audio data
            audio_data = data.get("audio_data")
            if audio_data:
                # Decode base64 audio
                audio_bytes = base64.b64decode(audio_data)
                
                # Process with voice assistant
                assistant = active_sessions[session_id]
                result = await assistant.conversation_manager.process_single_command(audio_bytes)
                
                # Send response
                await websocket.send_json({
                    "type": "voice_response",
                    "transcribed_text": result.get('stt_result', {}).get('text', ''),
                    "response_text": result.get('response', ''),
                    "confidence": result.get('stt_result', {}).get('confidence', 0.0),
                    "processing_time": result.get('processing_time', 0.0)
                })
        
        elif message_type == "text_input":
            # Process text input (for testing/fallback)
            text = data.get("text", "")
            if text:
                assistant = active_sessions[session_id]
                
                # Process with advanced AI
                response = await assistant.conversation_manager.voice_engine._process_with_advanced_ai(text)
                
                # Speak response
                await assistant.say(response)
                
                # Send response
                await websocket.send_json({
                    "type": "text_response",
                    "input_text": text,
                    "response_text": response
                })
        
        elif message_type == "start_listening":
            # Start continuous listening mode
            await websocket.send_json({
                "type": "listening_started",
                "message": "Voice recognition active"
            })
        
        elif message_type == "stop_listening":
            # Stop listening mode
            await websocket.send_json({
                "type": "listening_stopped",
                "message": "Voice recognition stopped"
            })
        
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

def get_voice_interface_html() -> str:
    """Generate the voice interface HTML page"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BUDDY 2.0 Voice Assistant</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            color: white;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
            margin: 10px 0;
        }
        
        .voice-controls {
            text-align: center;
            margin: 30px 0;
        }
        
        .voice-button {
            background: linear-gradient(45deg, #ff6b6b, #ee5a52);
            border: none;
            border-radius: 50%;
            width: 120px;
            height: 120px;
            font-size: 24px;
            color: white;
            cursor: pointer;
            margin: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        .voice-button:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        
        .voice-button.recording {
            background: linear-gradient(45deg, #4ecdc4, #44a08d);
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .status {
            text-align: center;
            font-size: 1.1em;
            margin: 20px 0;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            min-height: 50px;
        }
        
        .conversation {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .message {
            margin: 10px 0;
            padding: 10px 15px;
            border-radius: 10px;
            word-wrap: break-word;
        }
        
        .user-message {
            background: rgba(102, 126, 234, 0.3);
            margin-left: 20px;
        }
        
        .assistant-message {
            background: rgba(118, 75, 162, 0.3);
            margin-right: 20px;
        }
        
        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        .control-button {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
            padding: 10px 20px;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .control-button:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .test-section {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .test-button {
            background: rgba(76, 175, 80, 0.3);
            border: 1px solid rgba(76, 175, 80, 0.5);
            border-radius: 8px;
            padding: 10px 20px;
            color: white;
            cursor: pointer;
            margin: 5px;
            transition: all 0.3s ease;
        }
        
        .test-button:hover {
            background: rgba(76, 175, 80, 0.5);
        }
        
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 BUDDY 2.0</h1>
            <p>Advanced Voice Assistant with JARVIS-Level AI</p>
            <p>Phase 8: Voice Capabilities Integration</p>
        </div>
        
        <div class="voice-controls">
            <button id="voiceButton" class="voice-button" onclick="toggleVoiceRecording()">
                🎤
            </button>
            <div>Click and hold to speak with BUDDY</div>
        </div>
        
        <div id="status" class="status">
            Ready to listen... Click the microphone button to start!
        </div>
        
        <div class="conversation" id="conversation">
            <div class="message assistant-message">
                <strong>BUDDY:</strong> Hello! I'm your AI voice assistant with advanced intelligence capabilities. How can I help you today?
            </div>
        </div>
        
        <div class="controls">
            <button class="control-button" onclick="clearConversation()">Clear Chat</button>
            <button class="control-button" onclick="testVoiceSystem()">Test Voice System</button>
            <button class="control-button" onclick="startContinuousMode()">Continuous Mode</button>
            <button class="control-button" onclick="toggleWakeWord()">Wake Word</button>
        </div>
        
        <div class="test-section">
            <h3>🧪 Voice System Tests</h3>
            <button class="test-button" onclick="testTTS()">Test Text-to-Speech</button>
            <button class="test-button" onclick="testSTT()">Test Speech-to-Text</button>
            <button class="test-button" onclick="testFullFlow()">Test Complete Flow</button>
            <button class="test-button" onclick="runVoiceDemo()">Run Voice Demo</button>
        </div>
    </div>

    <script>
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        let websocket = null;
        let sessionId = null;
        let wakeWordActive = false;
        
        // Initialize when page loads
        window.onload = function() {
            initializeVoiceSystem();
        };
        
        async function initializeVoiceSystem() {
            try {
                updateStatus("Initializing voice system...");
                
                // Create session
                const response = await fetch('/api/voice/session/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        personality_name: "BUDDY",
                        voice_style: "friendly",
                        language: "en-US",
                        wake_words: ["buddy", "hey buddy"]
                    })
                });
                
                const result = await response.json();
                sessionId = result.session_id;
                
                // Initialize WebSocket
                initializeWebSocket();
                
                updateStatus("Voice system ready! Click the microphone to start talking.");
                
            } catch (error) {
                console.error('Initialization error:', error);
                updateStatus("⚠️ Voice system initialization failed. Some features may not work.");
            }
        }
        
        function initializeWebSocket() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/voice/${sessionId}`;
            
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = function(event) {
                console.log('WebSocket connected');
            };
            
            websocket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            websocket.onclose = function(event) {
                console.log('WebSocket disconnected');
                updateStatus("Connection lost. Refresh to reconnect.");
            };
            
            websocket.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateStatus("Connection error occurred.");
            };
        }
        
        function handleWebSocketMessage(data) {
            switch(data.type) {
                case 'welcome':
                    console.log('WebSocket welcome:', data.message);
                    break;
                case 'voice_response':
                    addMessage('You', data.transcribed_text, 'user');
                    addMessage('BUDDY', data.response_text, 'assistant');
                    updateStatus(`Processing complete (${data.processing_time.toFixed(2)}s, confidence: ${(data.confidence * 100).toFixed(1)}%)`);
                    break;
                case 'text_response':
                    addMessage('You', data.input_text, 'user');
                    addMessage('BUDDY', data.response_text, 'assistant');
                    break;
                case 'error':
                    updateStatus(`Error: ${data.message}`);
                    break;
            }
        }
        
        async function toggleVoiceRecording() {
            if (!isRecording) {
                await startRecording();
            } else {
                await stopRecording();
            }
        }
        
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = function(event) {
                    audioChunks.push(event.data);
                };
                
                mediaRecorder.onstop = function() {
                    processRecordedAudio();
                };
                
                mediaRecorder.start();
                isRecording = true;
                
                const button = document.getElementById('voiceButton');
                button.classList.add('recording');
                button.innerHTML = '🔴';
                
                updateStatus("🎤 Listening... Speak now!");
                
            } catch (error) {
                console.error('Recording start error:', error);
                updateStatus("❌ Microphone access denied or not available");
            }
        }
        
        async function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                
                isRecording = false;
                
                const button = document.getElementById('voiceButton');
                button.classList.remove('recording');
                button.innerHTML = '🎤';
                
                updateStatus("🔄 Processing your voice...");
            }
        }
        
        async function processRecordedAudio() {
            try {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const audioBuffer = await audioBlob.arrayBuffer();
                const base64Audio = btoa(String.fromCharCode(...new Uint8Array(audioBuffer)));
                
                // Send to WebSocket
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(JSON.stringify({
                        type: 'voice_data',
                        audio_data: base64Audio
                    }));
                } else {
                    updateStatus("❌ Connection not available");
                }
                
            } catch (error) {
                console.error('Audio processing error:', error);
                updateStatus("❌ Audio processing failed");
            }
        }
        
        function addMessage(sender, message, type) {
            const conversation = document.getElementById('conversation');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            messageDiv.innerHTML = `<strong>${sender}:</strong> ${message}`;
            conversation.appendChild(messageDiv);
            conversation.scrollTop = conversation.scrollHeight;
        }
        
        function updateStatus(message) {
            document.getElementById('status').textContent = message;
        }
        
        function clearConversation() {
            const conversation = document.getElementById('conversation');
            conversation.innerHTML = '<div class="message assistant-message"><strong>BUDDY:</strong> Conversation cleared. How can I help you?</div>';
            updateStatus("Conversation cleared");
        }
        
        async function testVoiceSystem() {
            updateStatus("🧪 Testing voice system...");
            
            try {
                const response = await fetch('/api/voice/test');
                const result = await response.json();
                
                const status = result.overall_status;
                const working = status === 'fully_operational';
                
                updateStatus(working ? "✅ Voice system test passed!" : "⚠️ Voice system has issues");
                addMessage('System', `Voice test result: ${status}`, 'assistant');
                
            } catch (error) {
                console.error('Voice test error:', error);
                updateStatus("❌ Voice test failed");
            }
        }
        
        async function testTTS() {
            updateStatus("🔊 Testing text-to-speech...");
            
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({
                    type: 'text_input',
                    text: 'This is a test of the text-to-speech system. Hello from BUDDY!'
                }));
            }
        }
        
        async function testSTT() {
            updateStatus("🎤 Click the microphone button to test speech-to-text");
            addMessage('System', 'Please use the microphone button to test speech recognition', 'assistant');
        }
        
        async function testFullFlow() {
            updateStatus("🔄 Testing complete voice flow...");
            
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({
                    type: 'text_input',
                    text: 'Hello BUDDY, please tell me what you can do'
                }));
            }
        }
        
        async function runVoiceDemo() {
            updateStatus("🎬 Running voice interaction demo...");
            
            const demoMessages = [
                "Hello BUDDY, how are you today?",
                "What can you help me with?",
                "Schedule a meeting with the team tomorrow",
                "What's the weather forecast?",
                "Thank you for the demonstration!"
            ];
            
            for (let i = 0; i < demoMessages.length; i++) {
                setTimeout(() => {
                    if (websocket && websocket.readyState === WebSocket.OPEN) {
                        websocket.send(JSON.stringify({
                            type: 'text_input',
                            text: demoMessages[i]
                        }));
                    }
                }, i * 3000); // 3 second delay between messages
            }
        }
        
        function startContinuousMode() {
            wakeWordActive = !wakeWordActive;
            const button = event.target;
            
            if (wakeWordActive) {
                button.textContent = "Stop Continuous";
                button.style.background = "rgba(244, 67, 54, 0.3)";
                updateStatus("🔄 Continuous mode active - say 'Hey BUDDY' to activate");
                addMessage('System', 'Continuous listening mode activated. Say "Hey BUDDY" to start speaking.', 'assistant');
            } else {
                button.textContent = "Continuous Mode";
                button.style.background = "rgba(255, 255, 255, 0.2)";
                updateStatus("Continuous mode disabled");
                addMessage('System', 'Continuous listening mode disabled.', 'assistant');
            }
        }
        
        function toggleWakeWord() {
            const active = !wakeWordActive;
            updateStatus(active ? "👂 Wake word detection: ON" : "👂 Wake word detection: OFF");
            addMessage('System', `Wake word detection ${active ? 'enabled' : 'disabled'}. Say "Hey BUDDY" to activate.`, 'assistant');
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(event) {
            if (event.code === 'Space' && !isRecording) {
                event.preventDefault();
                startRecording();
            }
        });
        
        document.addEventListener('keyup', function(event) {
            if (event.code === 'Space' && isRecording) {
                event.preventDefault();
                stopRecording();
            }
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', function() {
            if (websocket) {
                websocket.close();
            }
        });
    </script>
</body>
</html>
"""

# Additional utility endpoints

@app.get("/api/voice/sessions")
async def list_active_sessions() -> Dict[str, List[str]]:
    """List all active voice sessions"""
    return {
        "active_sessions": list(active_sessions.keys()),
        "websocket_connections": list(websocket_connections.keys())
    }

@app.get("/api/voice/status")
async def get_voice_server_status() -> Dict[str, Any]:
    """Get voice server status"""
    return {
        "server_status": "running",
        "active_sessions": len(active_sessions),
        "websocket_connections": len(websocket_connections),
        "uptime": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting BUDDY Voice Web Server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
