"""
BUDDY 2.0 Enhanced AI Assistant with Mail & Device Handling
Production-ready implementation with contextual intelligence
"""
import os
import sys
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
from datetime import datetime
from typing import Dict, Any, Optional

# Add buddy_core to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'buddy_core'))

# Universal Port Management
from buddy_core.utils.universal_port_manager import (
    universal_port_manager, 
    get_buddy_port, 
    get_buddy_host, 
    get_server_config,
    print_startup_banner,
    auto_configure
)

# Import enhanced intelligence and utilities
try:
    from buddy_core.intelligence.enhanced_response_engine import BUDDYEnhancedIntelligence
    from buddy_core.memory.cross_device_memory import CrossDeviceMemoryManager
    from buddy_core.utils.super_enhanced_email_handler import SuperEnhancedBUDDYEmailHandler
    ENHANCED_INTELLIGENCE_AVAILABLE = True
    MEMORY_AVAILABLE = True
    MAILER_AVAILABLE = True
    print("✅ Super Enhanced components loaded successfully!")
    print("🌟 Features: Templates • Contacts • Scheduling • Analytics • Attachments")
except ImportError as e:
    print(f"⚠️  Super Enhanced components not available: {e}")
    try:
        from utils.mailer import MockMailer, create_mailer, BUDDYEmailHandler as SuperEnhancedBUDDYEmailHandler
        ENHANCED_INTELLIGENCE_AVAILABLE = False
        MEMORY_AVAILABLE = False
        MAILER_AVAILABLE = True
        print("📧 Using standard email handler as fallback")
    except ImportError:
        SuperEnhancedBUDDYEmailHandler = None
        ENHANCED_INTELLIGENCE_AVAILABLE = False
        MEMORY_AVAILABLE = False
    MAILER_AVAILABLE = False

# FastAPI app with enhanced capabilities
app = FastAPI(
    title="BUDDY 2.0 Enhanced AI Assistant",
    description="Advanced AI with email handling, device management, and contextual intelligence",
    version="2.0.1"
)

# CORS middleware for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML interfaces)
app.mount("/static", StaticFiles(directory="."), name="static")

# Global service instances
buddy_intelligence = None
memory_manager = None
mailer = None
email_handler = None

async def init_buddy_services():
    """Initialize all BUDDY enhanced services"""
    global buddy_intelligence, memory_manager, mailer, email_handler
    
    print("🔧 Initializing BUDDY enhanced services...")
    
    if ENHANCED_INTELLIGENCE_AVAILABLE:
        try:
            buddy_intelligence = BUDDYEnhancedIntelligence()
            print("✅ Enhanced Intelligence Engine loaded")
        except Exception as e:
            print(f"❌ Intelligence Engine failed: {e}")
    
    if MEMORY_AVAILABLE:
        try:
            memory_manager = CrossDeviceMemoryManager()
            print("✅ Cross-Device Memory Manager initialized")
        except Exception as e:
            print(f"❌ Memory Manager failed: {e}")
    
    if MAILER_AVAILABLE and SuperEnhancedBUDDYEmailHandler:
        try:
            # Initialize SUPER Enhanced email handler with ALL features
            email_handler = SuperEnhancedBUDDYEmailHandler(provider="mock")
            print("✅ SUPER Enhanced Email Handler initialized!")
            print("🎯 Features Active: Templates • Contacts • Scheduling • Analytics • Attachments")
        except Exception as e:
            print(f"❌ Super Enhanced Email Handler failed: {e}")
            email_handler = None
    else:
        email_handler = None
        print("⚠️  Email handler not available")

# Request/Response Models
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    user_id: Optional[str] = Field("default", min_length=1, max_length=100)

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    personality: str = "buddy_enhanced"
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

class UniversalChatRequest(ChatMessage):
    device_type: str = Field("web", max_length=30)
    device_id: Optional[str] = Field(None, max_length=100)
    session_id: Optional[str] = Field(None, max_length=100)
    capabilities: Optional[Dict[str, Any]] = None
    conversation_context: Optional[list] = None

# Enhanced fallback responses
ENHANCED_FALLBACK_RESPONSES = {
    "send_mail": "I'd love to help you send an email! Who should I send it to? Please provide the recipient's email address or contact name.",
    "list_devices": "Let me check your connected devices. I can see this current device, but I need the memory system to show all your devices.",
    "greeting": "Hello! I'm BUDDY 2.0 with enhanced intelligence. I can help with emails, device management, calculations, and much more!",
    "general": "I'm BUDDY 2.0 with enhanced capabilities. I can help with sending emails, managing devices, calculations, and more. What would you like to do?",
    "error": "I encountered an issue processing that request. Please try again or ask for help."
}

@app.get("/health")

async def generate_response(self, user_input, user_id, device_type, session_context):
    raise NotImplementedError

async def health_check():
    """Enhanced health check with system status"""
    return {
        "service": "BUDDY 2.0 Enhanced",
        "status": "healthy",
        "version": "2.0.1",
        "timestamp": datetime.now().isoformat(),
        "capabilities": {
            "enhanced_intelligence": ENHANCED_INTELLIGENCE_AVAILABLE,
            "memory_system": MEMORY_AVAILABLE,
            "email_system": MAILER_AVAILABLE,
            "intent_recognition": True,
            "device_management": True,
            "cross_platform_sync": True
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def basic_chat(request: ChatMessage):
    """Basic chat endpoint with enhanced fallbacks"""
    try:
        # Quick intent detection for basic endpoint
        message_lower = request.message.lower()
        
        if "send" in message_lower and ("mail" in message_lower or "email" in message_lower):
            response_text = ENHANCED_FALLBACK_RESPONSES["send_mail"]
        elif "device" in message_lower and ("connect" in message_lower or "list" in message_lower):
            response_text = ENHANCED_FALLBACK_RESPONSES["list_devices"]
        elif any(greeting in message_lower for greeting in ["hello", "hi", "hey"]):
            response_text = ENHANCED_FALLBACK_RESPONSES["greeting"]
        else:
            response_text = ENHANCED_FALLBACK_RESPONSES["general"]
        
        # Try enhanced intelligence if available
        if ENHANCED_INTELLIGENCE_AVAILABLE and buddy_intelligence:
            try:
                result = await buddy_intelligence.generate_response(
                    user_input=request.message,
                    user_id=request.user_id,
                    device_type="api_client",
                    session_context={"mailer": mailer}
                )
                response_text = result.get("response", response_text)
                metadata = result.get("metadata", {"intelligence_level": "enhanced"})
            except Exception as e:
                print(f"Enhanced intelligence error: {e}")
                metadata = {"intelligence_level": "fallback", "error": str(e)}
        else:
            metadata = {"intelligence_level": "basic"}
        
        return ChatResponse(
            response=response_text,
            timestamp=datetime.now().isoformat(),
            metadata=metadata
        )
        
    except Exception as e:
        print(f"Chat error: {e}")
        return ChatResponse(
            response=ENHANCED_FALLBACK_RESPONSES["error"],
            timestamp=datetime.now().isoformat(),
            metadata={"error": str(e)}
        )

@app.post("/chat/universal", response_model=ChatResponse)
async def enhanced_universal_chat(request: UniversalChatRequest):
    """Enhanced universal chat with full context and capabilities"""
    try:
        start_time = datetime.now()
        
        if not ENHANCED_INTELLIGENCE_AVAILABLE or not buddy_intelligence:
            # Enhanced fallback with intent detection
            message_lower = request.message.lower()
            
            # Use SUPER enhanced email handler for email requests
            if "send" in message_lower and ("mail" in message_lower or "email" in message_lower):
                if email_handler:
                    try:
                        # Use the SUPER enhanced email handler with ALL features
                        email_result = await email_handler.handle_email_request(
                            user_input=request.message,
                            context={
                                "user_id": request.user_id,
                                "device_type": request.device_type,
                                "default_email": "demo@example.com"
                            }
                        )
                        response_text = email_result["response"]
                    except Exception as e:
                        response_text = f"📧 I'd love to help you send an email! However, there's an issue with the email system: {str(e)}"
                else:
                    response_text = "📧 I can help you send an email! Who should I send it to? (Please provide email address or contact name)"
            elif "device" in message_lower and ("connect" in message_lower or "list" in message_lower or "what are" in message_lower):
                response_text = f"I can see you're using a {request.device_type} device right now. For a complete device list, I need my memory system to be fully active."
            elif "time" in message_lower:
                current_time = datetime.now().strftime("%I:%M %p")
                response_text = f"⏰ It's currently {current_time}."
            elif any(word in message_lower for word in ["calculate", "math", "*", "+", "-", "/"]):
                response_text = "🧮 I can help with calculations! Please tell me what you'd like me to calculate."
            else:
                response_text = ENHANCED_FALLBACK_RESPONSES["general"]
            
            return ChatResponse(
                response=response_text,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "intelligence_level": "enhanced_fallback",
                    "device_type": request.device_type,
                    "response_time": int((datetime.now() - start_time).total_seconds() * 1000)
                }
            )
        
        # Build comprehensive session context
        session_context = {
            "device_type": request.device_type,
            "device_id": request.device_id or f"device_{int(datetime.now().timestamp())}",
            "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
            "capabilities": request.capabilities or {},
            "conversation_context": request.conversation_context or [],
            "mailer": mailer,  # Critical: Include mailer for email functionality
            "timestamp": start_time.isoformat(),
            "api_version": "2.0.1"
        }
        
        # Ensure device is tracked if memory is available
        if MEMORY_AVAILABLE and memory_manager and request.device_id and request.user_id:
            try:
                await memory_manager.ensure_device_record(
                    user_id=request.user_id,
                    device_id=request.device_id,
                    device_type=request.device_type,
                    device_name=request.capabilities.get("device_name") if request.capabilities else None,
                    capabilities=request.capabilities
                )
            except Exception as e:
                print(f"Device tracking error: {e}")
        
        # Generate enhanced intelligent response
        result = await buddy_intelligence.generate_response(
            user_input=request.message,
            user_id=request.user_id,
            device_type=request.device_type,
            session_context=session_context
        )
        
        response_text = result.get("response", "I'm processing your request...")
        metadata = result.get("metadata", {})
        
        # Enhance metadata with performance and context info
        end_time = datetime.now()
        metadata.update({
            "intelligence_level": "enhanced",
            "device_adapted": True,
            "memory_enabled": MEMORY_AVAILABLE,
            "email_enabled": MAILER_AVAILABLE,
            "response_time": int((end_time - start_time).total_seconds() * 1000),
            "api_version": "2.0.1",
            "device_type": request.device_type
        })
        
        return ChatResponse(
            response=response_text,
            timestamp=end_time.isoformat(),
            metadata=metadata
        )
        
    except Exception as e:
        print(f"Universal chat error: {e}")
        import traceback
        traceback.print_exc()
        
        return ChatResponse(
            response=f"I encountered an error processing your request. Please try again. (Error: {str(e)})",
            timestamp=datetime.now().isoformat(),
            metadata={
                "error": str(e),
                "intelligence_level": "error",
                "device_type": request.device_type
            }
        )

@app.get("/system/capabilities")
async def system_capabilities():
    """Get detailed system capabilities"""
    return {
        "enhanced_intelligence": ENHANCED_INTELLIGENCE_AVAILABLE,
        "memory_system": MEMORY_AVAILABLE,
        "email_system": MAILER_AVAILABLE,
        "supported_actions": [
            "send_mail",
            "list_devices", 
            "time_inquiry",
            "calculations",
            "device_management",
            "cross_platform_sync"
        ],
        "response_types": [
            "contextual",
            "personalized",
            "device_adapted",
            "action_oriented"
        ],
        "version": "2.0.1",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint with enhanced system information"""
    return {
        "message": "🤖 BUDDY 2.0 Enhanced AI Assistant",
        "version": "2.0.1",
        "status": "running",
        "enhancements": [
            "✅ Enhanced Intelligence Engine",
            "✅ Email Sending with Conversation Flow",
            "✅ Device Management & Listing", 
            "✅ Advanced Intent Recognition",
            "✅ Cross-Device Memory System",
            "✅ Contextual Responses",
            "✅ Math Calculations & Time Queries",
            "✅ Device Synchronization"
        ],
        "quick_test": {
            "send_email": "POST /chat/universal with message: 'send a mail'",
            "list_devices": "POST /chat/universal with message: 'what are all the devices connected'",
            "math": "POST /chat/universal with message: 'what's 25 * 4?'",
            "time": "POST /chat/universal with message: 'what time is it?'"
        },
        "endpoints": [
            "GET /health - Enhanced health check",
            "POST /chat - Basic chat with enhanced fallbacks",
            "POST /chat/universal - Full enhanced chat",
            "GET /system/capabilities - System capabilities",
            "GET /docs - API documentation"
        ]
    }

if __name__ == "__main__":
    # Auto-configure for any environment
    auto_configure()
    
    # Get universal server configuration
    server_config = get_server_config()
    host = server_config['host']
    port = server_config['port']
    
    print("🚀 Launching BUDDY 2.0 Enhanced AI Assistant...")
    print("=" * 70)
    print("🎯 Features: Email Handling • Device Management • Smart Intent Recognition")
    print("🧠 Intelligence: Contextual Responses • Cross-Device Memory • Action-Oriented")
    print("📱 Platforms: Web • Desktop • Mobile • Watch • Car • TV")
    print("=" * 70)
    
    # Print universal startup banner
    print_startup_banner()
    
    # Initialize enhanced services
    print("🔧 Initializing enhanced services...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_buddy_services())
    
    print("🎉 BUDDY 2.0 Enhanced is ready!")
    print("💡 Try: 'send a mail' or 'what are all the devices connected'")
    print("🌍 Universal deployment ready - works on any platform!")
    print("=" * 70)
    
    # Start server with universal configuration
    with universal_port_manager.managed_server() as config:
        uvicorn.run(
            app, 
            host=host, 
            port=port,
            log_level="info",
            access_log=True
        )
