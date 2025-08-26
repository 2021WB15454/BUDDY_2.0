// BUDDY 2.0 Frontend Configuration for Firebase Hosting
// Add this to your React app's .env file or environment configuration

// Render Backend Configuration
const BACKEND_CONFIG = {
  // Production Render URL (update when deployed)
  RENDER_API_URL: "https://buddy-2-0.onrender.com",
  
  // Get the appropriate API URL based on environment
  getApiUrl() {
    // Check if we're in production (Firebase hosting)
    if (window.location.hostname.includes('firebaseapp.com') || 
        window.location.hostname.includes('web.app')) {
      return this.RENDER_API_URL;
    }
    // Local development - use dynamic configuration
    const host = window.BUDDY_HOST || 'localhost';
    const port = window.BUDDY_PORT || '8082';
    return `http://${host}:${port}`;
  }
};

// Firebase Configuration
const FIREBASE_CONFIG = {
  apiKey: "your-firebase-api-key",
  authDomain: "buddyai-42493.firebaseapp.com",
  databaseURL: "https://buddyai-42493-default-rtdb.firebaseio.com",
  projectId: "buddyai-42493",
  storageBucket: "buddyai-42493.appspot.com",
  messagingSenderId: "your-messaging-sender-id",
  appId: "your-app-id"
};

// API Endpoints
const API_ENDPOINTS = {
  chat: "/chat",
  health: "/health",
  status: "/status",
  config: "/config",
  conversations: "/conversations"
};

// Example React component for connecting to BUDDY backend
class BuddyConnector {
  constructor() {
    this.apiUrl = BACKEND_CONFIG.getApiUrl();
    this.isOnline = false;
  }

  // Check if BUDDY backend is online
  async checkStatus() {
    try {
      const response = await fetch(`${this.apiUrl}${API_ENDPOINTS.status}`);
      if (response.ok) {
        const status = await response.json();
        this.isOnline = status.status === 'online';
        return status;
      }
    } catch (error) {
      console.error('Failed to check BUDDY status:', error);
      this.isOnline = false;
    }
    return null;
  }

  // Send message to BUDDY
  async sendMessage(message, userId = 'default_user', sessionId = 'web_session') {
    try {
      const response = await fetch(`${this.apiUrl}${API_ENDPOINTS.chat}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          user_id: userId,
          session_id: sessionId,
          context: {
            device_type: 'web',
            timestamp: new Date().toISOString()
          }
        })
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to send message to BUDDY:', error);
      throw error;
    }
  }

  // Get backend configuration
  async getConfig() {
    try {
      const response = await fetch(`${this.apiUrl}${API_ENDPOINTS.config}`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Failed to get backend config:', error);
    }
    return null;
  }
}

// React Hook for BUDDY connection
export const useBuddy = () => {
  const [isOnline, setIsOnline] = React.useState(false);
  const [status, setStatus] = React.useState(null);
  const [config, setConfig] = React.useState(null);
  const buddyConnector = React.useRef(new BuddyConnector());

  React.useEffect(() => {
    // Check status on mount
    const checkInitialStatus = async () => {
      const statusData = await buddyConnector.current.checkStatus();
      if (statusData) {
        setStatus(statusData);
        setIsOnline(statusData.status === 'online');
      }

      const configData = await buddyConnector.current.getConfig();
      if (configData) {
        setConfig(configData);
      }
    };

    checkInitialStatus();

    // Poll status every 30 seconds
    const interval = setInterval(async () => {
      const statusData = await buddyConnector.current.checkStatus();
      if (statusData) {
        setStatus(statusData);
        setIsOnline(statusData.status === 'online');
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const sendMessage = async (message, userId, sessionId) => {
    return await buddyConnector.current.sendMessage(message, userId, sessionId);
  };

  return {
    isOnline,
    status,
    config,
    sendMessage
  };
};

// Example React Component
export const BuddyChat = () => {
  const { isOnline, status, sendMessage } = useBuddy();
  const [message, setMessage] = React.useState('');
  const [conversation, setConversation] = React.useState([]);
  const [loading, setLoading] = React.useState(false);

  const handleSendMessage = async () => {
    if (!message.trim() || !isOnline || loading) return;

    setLoading(true);
    try {
      // Add user message to conversation
      const userMessage = { role: 'user', content: message, timestamp: new Date().toISOString() };
      setConversation(prev => [...prev, userMessage]);

      // Send to BUDDY
      const response = await sendMessage(message);
      
      // Add BUDDY response to conversation
      const buddyMessage = { role: 'assistant', content: response.response, timestamp: response.timestamp };
      setConversation(prev => [...prev, buddyMessage]);

      setMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
      // Show error message
      const errorMessage = { role: 'error', content: 'Failed to send message. Please try again.', timestamp: new Date().toISOString() };
      setConversation(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="buddy-chat">
      <div className="status-indicator">
        <span className={`status-dot ${isOnline ? 'online' : 'offline'}`}></span>
        BUDDY is {isOnline ? 'Online' : 'Offline'}
        {status && <span className="version">v{status.version}</span>}
      </div>

      <div className="conversation">
        {conversation.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="content">{msg.content}</div>
            <div className="timestamp">{new Date(msg.timestamp).toLocaleTimeString()}</div>
          </div>
        ))}
      </div>

      <div className="input-area">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder={isOnline ? "Type your message..." : "BUDDY is offline"}
          disabled={!isOnline || loading}
        />
        <button 
          onClick={handleSendMessage} 
          disabled={!isOnline || loading || !message.trim()}
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};

// CSS Styles (add to your CSS file)
const styles = `
.buddy-chat {
  max-width: 600px;
  margin: 0 auto;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.status-indicator {
  background: #f5f5f5;
  padding: 10px;
  border-bottom: 1px solid #ddd;
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
}

.status-dot.online {
  background: #4CAF50;
}

.status-dot.offline {
  background: #f44336;
}

.conversation {
  height: 400px;
  overflow-y: auto;
  padding: 16px;
}

.message {
  margin-bottom: 16px;
  padding: 8px 12px;
  border-radius: 8px;
  max-width: 80%;
}

.message.user {
  background: #e3f2fd;
  margin-left: auto;
  text-align: right;
}

.message.assistant {
  background: #f5f5f5;
  margin-right: auto;
}

.message.error {
  background: #ffebee;
  color: #c62828;
  margin-right: auto;
}

.timestamp {
  font-size: 0.8em;
  color: #666;
  margin-top: 4px;
}

.input-area {
  display: flex;
  padding: 16px;
  border-top: 1px solid #ddd;
  gap: 8px;
}

.input-area input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.input-area button {
  padding: 8px 16px;
  background: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.input-area button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
`;

export { BACKEND_CONFIG, FIREBASE_CONFIG, API_ENDPOINTS, BuddyConnector, styles };

// Instructions for Integration:
/*

1. **Deploy Backend to Render:**
   - Your backend is already configured for Render deployment
   - Set environment variables in Render dashboard
   - Get your Render URL (e.g., https://buddy-2-0.onrender.com)

2. **Update Frontend Configuration:**
   - Replace "https://buddy-2-0.onrender.com" with your actual Render URL
   - Add this configuration to your React app

3. **Build and Deploy Frontend to Firebase:**
   - npm run build
   - firebase deploy

4. **Test Connection:**
   - Open your Firebase-hosted app
   - Check the status indicator shows "BUDDY is Online"
   - Send a test message

5. **Monitor Logs:**
   - Render dashboard: Check backend logs
   - Firebase console: Check hosting and database activity
   - Browser DevTools: Check API calls

*/
