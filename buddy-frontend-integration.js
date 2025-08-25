// 🔗 BUDDY 2.0 React Frontend Integration
// Add this to your React app to automatically connect to Render backend

import React, { useState, useEffect, useCallback } from 'react';
import { database, ref, onValue } from 'firebase/database';

// Configuration
const BACKEND_CONFIG = {
  // Update this with your actual Render URL when deployed
  RENDER_URL: process.env.REACT_APP_API_URL || "https://buddy-backend.onrender.com",
  LOCAL_URL: "http://localhost:10000",
  
  // Auto-detect environment
  getApiUrl() {
    // Check if we're on Firebase hosting
    if (window.location.hostname.includes('firebaseapp.com') || 
        window.location.hostname.includes('web.app')) {
      return this.RENDER_URL;
    }
    // Local development
    return this.LOCAL_URL;
  }
};

// Custom hook for BUDDY connection
export const useBuddyConnection = () => {
  const [isOnline, setIsOnline] = useState(false);
  const [backendUrl, setBackendUrl] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  
  const apiUrl = BACKEND_CONFIG.getApiUrl();
  
  // Check backend health directly
  const checkBackendHealth = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const health = await response.json();
        return health.status === 'healthy';
      }
      return false;
    } catch (err) {
      console.warn('Backend health check failed:', err);
      return false;
    }
  }, [apiUrl]);
  
  // Get backend configuration
  const getBackendConfig = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/config`);
      if (response.ok) {
        const configData = await response.json();
        setConfig(configData);
        return configData;
      }
    } catch (err) {
      console.warn('Failed to get backend config:', err);
    }
    return null;
  }, [apiUrl]);
  
  // Firebase status listener
  useEffect(() => {
    let unsubscribe = null;
    
    try {
      // Listen to Firebase Realtime Database for status
      const statusRef = ref(database, 'status/buddy');
      
      unsubscribe = onValue(statusRef, (snapshot) => {
        const status = snapshot.val();
        
        if (status) {
          setIsOnline(status.status === 'online');
          setBackendUrl(status.backend_url);
          setLastUpdated(status.last_updated);
          setError(null);
          
          console.log('🔥 Firebase Status Update:', status);
        } else {
          setIsOnline(false);
          setBackendUrl(null);
        }
      });
      
    } catch (err) {
      console.warn('Firebase listener setup failed:', err);
      setError('Firebase connection failed');
    }
    
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, []);
  
  // Fallback: Direct backend polling if Firebase fails
  useEffect(() => {
    if (isOnline) return; // Firebase is working
    
    let interval = null;
    
    const pollBackend = async () => {
      const healthy = await checkBackendHealth();
      if (healthy) {
        setIsOnline(true);
        setBackendUrl(apiUrl);
        setLastUpdated(new Date().toISOString());
        setError(null);
        
        // Get config on first connection
        if (!config) {
          await getBackendConfig();
        }
      } else {
        setIsOnline(false);
        setError('Backend unreachable');
      }
    };
    
    // Initial check
    pollBackend();
    
    // Poll every 15 seconds as fallback
    interval = setInterval(pollBackend, 15000);
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isOnline, checkBackendHealth, getBackendConfig, config, apiUrl]);
  
  return {
    isOnline,
    backendUrl: backendUrl || apiUrl,
    lastUpdated,
    config,
    error,
    apiUrl
  };
};

// BUDDY Status Indicator Component
export const BuddyStatusIndicator = () => {
  const { isOnline, lastUpdated, error, apiUrl } = useBuddyConnection();
  
  return (
    <div className={`buddy-status ${isOnline ? 'online' : 'offline'}`}>
      <div className="status-indicator">
        <div className="status-dot"></div>
        <span className="status-text">
          BUDDY is {isOnline ? 'Online' : 'Offline'}
        </span>
      </div>
      
      {lastUpdated && (
        <div className="status-details">
          <small>Last updated: {new Date(lastUpdated).toLocaleTimeString()}</small>
        </div>
      )}
      
      {error && (
        <div className="status-error">
          <small>⚠️ {error}</small>
        </div>
      )}
      
      <div className="backend-info">
        <small>Backend: {apiUrl}</small>
      </div>
    </div>
  );
};

// Chat Hook with automatic backend connection
export const useBuddyChat = () => {
  const { isOnline, apiUrl } = useBuddyConnection();
  const [loading, setLoading] = useState(false);
  
  const sendMessage = useCallback(async (message, userId = 'web_user', sessionId = 'web_session') => {
    if (!isOnline || !message.trim()) {
      throw new Error('BUDDY is offline or message is empty');
    }
    
    setLoading(true);
    
    try {
      const response = await fetch(`${apiUrl}/chat`, {
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
            timestamp: new Date().toISOString(),
            source: 'firebase_frontend'
          }
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      return result;
      
    } catch (error) {
      console.error('Chat error:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [isOnline, apiUrl]);
  
  return {
    sendMessage,
    loading,
    isOnline
  };
};

// Complete Chat Component
export const BuddyChat = () => {
  const { sendMessage, loading, isOnline } = useBuddyChat();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || loading) return;
    
    // Add user message
    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    const currentMessage = inputMessage;
    setInputMessage('');
    
    try {
      // Send to BUDDY
      const response = await sendMessage(currentMessage);
      
      // Add BUDDY response
      const buddyMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp
      };
      
      setMessages(prev => [...prev, buddyMessage]);
      
    } catch (error) {
      // Add error message
      const errorMessage = {
        role: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    }
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  return (
    <div className="buddy-chat-container">
      {/* Status Indicator */}
      <BuddyStatusIndicator />
      
      {/* Chat Messages */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h3>👋 Welcome to BUDDY 2.0!</h3>
            <p>Your AI assistant is {isOnline ? 'ready to help' : 'currently offline'}.</p>
          </div>
        )}
        
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="message-content">{msg.content}</div>
            <div className="message-time">
              {new Date(msg.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}
      </div>
      
      {/* Input Area */}
      <div className="chat-input">
        <textarea
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={isOnline ? "Type your message..." : "BUDDY is offline"}
          disabled={!isOnline || loading}
          rows={3}
        />
        <button
          onClick={handleSendMessage}
          disabled={!isOnline || loading || !inputMessage.trim()}
          className="send-button"
        >
          {loading ? '⏳' : '🚀'} {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};

// CSS Styles (add to your CSS file)
export const BuddyChatStyles = `
.buddy-status {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  border: 1px solid #ddd;
}

.buddy-status.online {
  background: linear-gradient(135deg, #e8f5e8, #f1f8e9);
  border-color: #4caf50;
}

.buddy-status.offline {
  background: linear-gradient(135deg, #ffebee, #fce4ec);
  border-color: #f44336;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.buddy-status.online .status-dot {
  background: #4caf50;
}

.buddy-status.offline .status-dot {
  background: #f44336;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.status-text {
  font-weight: 600;
  font-size: 16px;
}

.buddy-status.online .status-text {
  color: #2e7d32;
}

.buddy-status.offline .status-text {
  color: #c62828;
}

.status-details, .status-error, .backend-info {
  font-size: 12px;
  margin-top: 2px;
  opacity: 0.8;
}

.buddy-chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 12px;
  background: white;
}

.chat-messages {
  height: 400px;
  overflow-y: auto;
  padding: 16px;
  border: 1px solid #eee;
  border-radius: 8px;
  margin-bottom: 16px;
  background: #fafafa;
}

.welcome-message {
  text-align: center;
  color: #666;
  padding: 40px 20px;
}

.message {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 8px;
  max-width: 80%;
}

.message.user {
  background: #e3f2fd;
  margin-left: auto;
  text-align: right;
}

.message.assistant {
  background: #f1f8e9;
  margin-right: auto;
}

.message.error {
  background: #ffebee;
  color: #c62828;
  margin-right: auto;
}

.message-content {
  margin-bottom: 4px;
  line-height: 1.4;
}

.message-time {
  font-size: 11px;
  opacity: 0.6;
}

.chat-input {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  resize: vertical;
  font-family: inherit;
}

.send-button {
  padding: 12px 20px;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.send-button:hover:not(:disabled) {
  background: #1976d2;
}

.send-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
`;

// Environment Setup Instructions
export const setupInstructions = `
// 🚀 Setup Instructions for Firebase Frontend

1. **Install Firebase SDK:**
   npm install firebase

2. **Initialize Firebase in your app:**
   import { initializeApp } from 'firebase/app';
   import { getDatabase } from 'firebase/database';
   
   const firebaseConfig = {
     apiKey: "your-api-key",
     authDomain: "buddyai-42493.firebaseapp.com", 
     databaseURL: "https://buddyai-42493-default-rtdb.firebaseio.com",
     projectId: "buddyai-42493"
   };
   
   const app = initializeApp(firebaseConfig);
   export const database = getDatabase(app);

3. **Set environment variable:**
   REACT_APP_API_URL=https://your-render-url.onrender.com

4. **Use the components:**
   import { BuddyChat, BuddyChatStyles } from './buddy-frontend-integration';
   
   function App() {
     return (
       <div>
         <style>{BuddyChatStyles}</style>
         <BuddyChat />
       </div>
     );
   }

5. **Deploy to Firebase:**
   npm run build
   firebase deploy
`;

export default {
  BuddyStatusIndicator,
  BuddyChat,
  useBuddyConnection,
  useBuddyChat,
  BuddyChatStyles,
  setupInstructions,
  BACKEND_CONFIG
};
