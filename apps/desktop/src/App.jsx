import React, { useState, useEffect, useRef } from 'react';
import './styles/App.css';
import './styles/enhanced.css';

// Simple fallback components to avoid import errors
const Sidebar = ({ currentView, onViewChange, connectionStatus }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  
  const navItems = [
    { id: 'chat', name: 'Chat', icon: '💬', badge: null },
    { id: 'skills', name: 'Skills', icon: '⚡', badge: 'NEW' },
    { id: 'voice', name: 'Voice', icon: '🎤', badge: null },
    { id: 'settings', name: 'Settings', icon: '⚙️', badge: null },
    { id: 'analytics', name: 'Analytics', icon: '📊', badge: null }
  ];

  return (
    <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo-section">
          <div className="logo">🤖</div>
          {!isCollapsed && (
            <div className="brand">
              <h2>BUDDY</h2>
              <span className="tagline">AI Assistant</span>
            </div>
          )}
        </div>
        <button 
          className="collapse-btn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? 'Expand' : 'Collapse'}
        >
          {isCollapsed ? '→' : '←'}
        </button>
      </div>
      
      <div className={`status-indicator ${connectionStatus}`}>
        <div className="status-dot"></div>
        {!isCollapsed && (
          <span className="status-text">
            {connectionStatus === 'connected' ? 'Online' : 
             connectionStatus === 'connecting' ? 'Connecting...' : 'Offline'}
          </span>
        )}
      </div>
      
      <nav className="sidebar-nav">
        {navItems.map(item => (
          <button
            key={item.id}
            className={`nav-item ${currentView === item.id ? 'active' : ''}`}
            onClick={() => onViewChange(item.id)}
            title={isCollapsed ? item.name : ''}
          >
            <span className="nav-icon">{item.icon}</span>
            {!isCollapsed && (
              <>
                <span className="nav-label">{item.name}</span>
                {item.badge && <span className="nav-badge">{item.badge}</span>}
              </>
            )}
          </button>
        ))}
      </nav>
      
      {!isCollapsed && (
        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">👤</div>
            <div className="user-details">
              <span className="user-name">User</span>
              <span className="user-role">Administrator</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const ChatInterface = ({ onSendMessage }) => {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'Hello! I\'m BUDDY, your AI assistant. How can I help you today?',
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (message.trim()) {
      // Add user message immediately
      const userMessage = {
        id: Date.now(),
        type: 'user',
        content: message,
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages(prev => [...prev, userMessage]);
      
      const currentMessage = message;
      setMessage('');
      setIsTyping(true);
      
      try {
        // Call the backend and wait for response
        const backendResponse = await onSendMessage(currentMessage);
        
        // Add bot response with actual backend data
        const botMessage = {
          id: Date.now() + 1,
          type: 'bot',
          content: backendResponse?.response || backendResponse || 'I apologize, but I encountered an issue processing your request.',
          timestamp: new Date().toLocaleTimeString()
        };
        setMessages(prev => [...prev, botMessage]);
        setIsTyping(false);
      } catch (error) {
        setIsTyping(false);
        console.error('Chat error:', error);
        const errorMessage = {
          id: Date.now() + 1,
          type: 'bot',
          content: 'I apologize, but I encountered a technical issue. Please check that the backend server is running and try again.',
          timestamp: new Date().toLocaleTimeString()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    }
  };

  const quickActions = [
    { text: "What's the time?", icon: "🕐" },
    { text: "System status", icon: "📊" },
    { text: "Calculate 25 * 4", icon: "🧮" },
    { text: "Set a reminder", icon: "⏰" }
  ];

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h3>💬 Chat with BUDDY</h3>
        <div className="chat-status">
          {isTyping ? (
            <span className="typing-indicator">
              <span className="typing-dot"></span>
              <span className="typing-dot"></span>
              <span className="typing-dot"></span>
              BUDDY is thinking...
            </span>
          ) : (
            <span className="status-ready">Ready</span>
          )}
        </div>
      </div>
      
      <div className="chat-messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.type}`}>
            <div className="message-content">
              <div className="message-bubble">
                {msg.type === 'bot' && <span className="bot-icon">🤖</span>}
                {msg.type === 'user' && <span className="user-icon">👤</span>}
                {msg.type === 'error' && <span className="error-icon">⚠️</span>}
                <span className="message-text">{msg.content}</span>
              </div>
              <div className="message-time">{msg.timestamp}</div>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="message bot typing">
            <div className="message-content">
              <div className="message-bubble">
                <span className="bot-icon">🤖</span>
                <div className="typing-animation">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="quick-actions">
        <div className="quick-actions-label">Quick Actions:</div>
        <div className="quick-actions-buttons">
          {quickActions.map((action, index) => (
            <button
              key={index}
              className="quick-action-btn"
              onClick={() => setMessage(action.text)}
            >
              <span className="action-icon">{action.icon}</span>
              {action.text}
            </button>
          ))}
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="chat-input">
        <div className="input-container">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message to BUDDY..."
            disabled={isTyping}
          />
          <button type="button" className="voice-btn" title="Voice Input">
            🎤
          </button>
          <button type="submit" disabled={!message.trim() || isTyping}>
            {isTyping ? '⏳' : '📤'}
          </button>
        </div>
      </form>
    </div>
  );
};

const SkillsPanel = ({ skills = [] }) => {
  const [selectedCategory, setSelectedCategory] = useState('all');
  
  const categories = ['all', 'conversation', 'utility', 'information', 'system', 'productivity', 'interaction'];
  
  const filteredSkills = selectedCategory === 'all' 
    ? skills 
    : skills.filter(skill => skill.category === selectedCategory);
  
  const enabledCount = skills.filter(s => s.enabled).length;
  const totalCount = skills.length;

  return (
    <div className="skills-panel">
      <div className="skills-header">
        <h3>🔥 AI Skills Center</h3>
        <div className="skills-stats">
          <span className="stat">
            <strong>{enabledCount}</strong>/{totalCount} Active
          </span>
          <span className="stat">
            <strong>{categories.length - 1}</strong> Categories
          </span>
        </div>
      </div>
      
      <div className="category-filter">
        {categories.map(category => (
          <button
            key={category}
            className={`category-btn ${selectedCategory === category ? 'active' : ''}`}
            onClick={() => setSelectedCategory(category)}
          >
            {category.charAt(0).toUpperCase() + category.slice(1)}
          </button>
        ))}
      </div>
      
      <div className="skills-grid">
        {filteredSkills.length > 0 ? filteredSkills.map(skill => (
          <div key={skill.id} className={`skill-card ${skill.enabled ? 'enabled' : 'disabled'}`}>
            <div className="skill-icon">{skill.icon || '⚡'}</div>
            <div className="skill-content">
              <h4>{skill.name}</h4>
              <p>{skill.description}</p>
              <div className="skill-meta">
                <span className={`skill-status ${skill.enabled ? 'active' : 'inactive'}`}>
                  {skill.enabled ? '🟢 Active' : '🔴 Inactive'}
                </span>
                <span className="skill-category">{skill.category}</span>
              </div>
            </div>
            <div className="skill-actions">
              <button className="skill-toggle">
                {skill.enabled ? 'Disable' : 'Enable'}
              </button>
            </div>
          </div>
        )) : (
          <div className="no-skills">
            <span className="no-skills-icon">🔍</span>
            <p>No skills found in this category</p>
          </div>
        )}
      </div>
    </div>
  );
};

const VoicePanel = ({ onSendMessage }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);
  const [hasPermission, setHasPermission] = useState(null);
  const [isCheckingPermission, setIsCheckingPermission] = useState(false);
  const recognitionRef = useRef(null);
  
  const [voiceCommands, setVoiceCommands] = useState([
    { command: "What time is it?", response: "Current time will be provided", used: 12 },
    { command: "Show system status", response: "System information displayed", used: 8 },
    { command: "Set reminder for...", response: "Reminder will be created", used: 5 },
    { command: "Calculate...", response: "Math calculation performed", used: 15 }
  ]);

  // Check microphone permission
  const checkMicrophonePermission = async () => {
    setIsCheckingPermission(true);
    setError(null);
    
    try {
      // First check if we have getUserMedia support
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('getUserMedia not supported in this browser');
      }

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Clean up the stream immediately
      stream.getTracks().forEach(track => track.stop());
      
      setHasPermission(true);
      setError(null);
    } catch (err) {
      console.error('Microphone permission check failed:', err);
      setHasPermission(false);
      
      if (err.name === 'NotAllowedError') {
        setError('Microphone access denied. Please allow microphone access in your browser settings.');
      } else if (err.name === 'NotFoundError') {
        setError('No microphone found. Please connect a microphone and try again.');
      } else if (err.name === 'NotReadableError') {
        setError('Microphone is being used by another application.');
      } else {
        setError(`Microphone access failed: ${err.message}`);
      }
    } finally {
      setIsCheckingPermission(false);
    }
  };

  // Initialize speech recognition
  const initializeSpeechRecognition = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Speech recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
      return false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognitionRef.current = new SpeechRecognition();
    
    recognitionRef.current.continuous = true;
    recognitionRef.current.interimResults = true;
    recognitionRef.current.lang = 'en-US';

    recognitionRef.current.onstart = () => {
      console.log('Speech recognition started');
      setIsListening(true);
      setError(null);
      setTranscript('Listening...');
    };

    recognitionRef.current.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      setTranscript(finalTranscript || interimTranscript);

      // If we have a final result, process it
      if (finalTranscript) {
        console.log('Final voice input:', finalTranscript);
        
        // Send the voice input to the chat
        if (onSendMessage) {
          onSendMessage(finalTranscript.trim());
        }
        
        // Stop listening after getting a command
        stopListening();
      }
    };

    recognitionRef.current.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      
      switch (event.error) {
        case 'no-speech':
          setError('No speech detected. Please try again.');
          break;
        case 'audio-capture':
          setError('Microphone not accessible. Please check your microphone.');
          break;
        case 'not-allowed':
          setError('Microphone access denied. Please allow microphone access.');
          setHasPermission(false);
          break;
        case 'network':
          setError('Network error. Please check your internet connection.');
          break;
        default:
          setError(`Speech recognition error: ${event.error}`);
      }
      
      setIsListening(false);
    };

    recognitionRef.current.onend = () => {
      console.log('Speech recognition ended');
      setIsListening(false);
    };

    return true;
  };

  const startListening = async () => {
    setError(null);
    
    // Check permission first
    if (hasPermission !== true) {
      await checkMicrophonePermission();
      return;
    }

    // Initialize speech recognition if not already done
    if (!recognitionRef.current) {
      if (!initializeSpeechRecognition()) {
        return;
      }
    }

    try {
      recognitionRef.current.start();
    } catch (err) {
      console.error('Failed to start speech recognition:', err);
      setError('Failed to start voice recognition. Please try again.');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  // Check permissions on component mount
  useEffect(() => {
    checkMicrophonePermission();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  return (
    <div className="voice-panel">
      <div className="voice-header">
        <h3>🎤 Voice Control Center</h3>
        <div className="voice-status">
          <span className={`status-indicator ${isListening ? 'active' : hasPermission ? 'ready' : 'error'}`}>
            {isListening ? '🔴 Listening' : hasPermission ? '⚪ Ready' : '❌ No Access'}
          </span>
        </div>
      </div>
      
      {/* Permission Request */}
      {hasPermission === false && (
        <div className="permission-request">
          <div className="permission-icon">🎤</div>
          <h4>Microphone Access Required</h4>
          <p>BUDDY needs microphone access to use voice commands.</p>
          <button 
            className="permission-btn"
            onClick={checkMicrophonePermission}
            disabled={isCheckingPermission}
          >
            {isCheckingPermission ? 'Checking...' : 'Grant Microphone Access'}
          </button>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="voice-error">
          <div className="error-icon">⚠️</div>
          <p>{error}</p>
          {hasPermission === false && (
            <button className="retry-btn" onClick={checkMicrophonePermission}>
              Try Again
            </button>
          )}
        </div>
      )}
      
      <div className="voice-controls">
        <button 
          className={`voice-toggle ${isListening ? 'listening' : ''}`}
          onClick={toggleListening}
          disabled={!hasPermission || isCheckingPermission}
        >
          <span className="voice-icon">🎤</span>
          {isListening ? 'Stop Listening' : 'Start Listening'}
        </button>
        
        <div className="voice-feedback">
          <div className="transcript-box">
            <label>Live Transcript:</label>
            <div className="transcript">
              {transcript || 'Click "Start Listening" to begin voice recognition...'}
            </div>
          </div>
        </div>
      </div>
      
      <div className="voice-commands">
        <h4>Popular Voice Commands</h4>
        <div className="commands-list">
          {voiceCommands.map((cmd, index) => (
            <div key={index} className="command-item">
              <div className="command-text">
                <span className="command">"{cmd.command}"</span>
                <span className="response">→ {cmd.response}</span>
              </div>
              <div className="command-usage">
                <span className="usage-count">{cmd.used} times</span>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="voice-settings">
        <h4>Voice Settings</h4>
        <div className="setting-item">
          <label>
            <input type="checkbox" defaultChecked />
            Enable wake word detection
          </label>
        </div>
        <div className="setting-item">
          <label>
            <input type="checkbox" defaultChecked />
            Continuous listening mode
          </label>
        </div>
        <div className="setting-item">
          <label>Voice sensitivity:</label>
          <input type="range" min="1" max="10" defaultValue="7" />
        </div>
      </div>
    </div>
  );
};

const AnalyticsPanel = ({ skills = [] }) => {
  const totalSkills = skills.length;
  const activeSkills = skills.filter(s => s.enabled).length;
  const skillsByCategory = skills.reduce((acc, skill) => {
    acc[skill.category] = (acc[skill.category] || 0) + 1;
    return acc;
  }, {});

  const usageData = [
    { name: 'Chat Interactions', value: 45, trend: '+12%' },
    { name: 'Voice Commands', value: 23, trend: '+8%' },
    { name: 'Skills Activated', value: 34, trend: '+15%' },
    { name: 'System Queries', value: 67, trend: '+22%' }
  ];

  return (
    <div className="analytics-panel">
      <div className="analytics-header">
        <h3>📊 Analytics Dashboard</h3>
        <div className="analytics-period">
          <select defaultValue="today">
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
          </select>
        </div>
      </div>
      
      <div className="analytics-grid">
        <div className="stat-card">
          <div className="stat-icon">⚡</div>
          <div className="stat-content">
            <div className="stat-value">{activeSkills}/{totalSkills}</div>
            <div className="stat-label">Active Skills</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">💬</div>
          <div className="stat-content">
            <div className="stat-value">127</div>
            <div className="stat-label">Conversations</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">🕐</div>
          <div className="stat-content">
            <div className="stat-value">3.2h</div>
            <div className="stat-label">Active Time</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-content">
            <div className="stat-value">94%</div>
            <div className="stat-label">Success Rate</div>
          </div>
        </div>
      </div>
      
      <div className="usage-chart">
        <h4>Usage Statistics</h4>
        <div className="usage-list">
          {usageData.map((item, index) => (
            <div key={index} className="usage-item">
              <div className="usage-info">
                <span className="usage-name">{item.name}</span>
                <span className="usage-trend">{item.trend}</span>
              </div>
              <div className="usage-bar">
                <div 
                  className="usage-fill" 
                  style={{ width: `${item.value}%` }}
                ></div>
              </div>
              <span className="usage-value">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="category-breakdown">
        <h4>Skills by Category</h4>
        <div className="category-list">
          {Object.entries(skillsByCategory).map(([category, count]) => (
            <div key={category} className="category-item">
              <span className="category-name">{category}</span>
              <span className="category-count">{count} skills</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const SettingsPanel = () => {
  const [settings, setSettings] = useState({
    voiceEnabled: true,
    autoStart: true,
    notifications: true,
    darkMode: false,
    aiPersonality: 'friendly',
    language: 'english',
    responseSpeed: 'normal'
  });

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="settings-panel">
      <div className="settings-header">
        <h3>⚙️ Settings & Preferences</h3>
        <button className="save-settings">💾 Save All</button>
      </div>
      
      <div className="settings-sections">
        <div className="settings-section">
          <h4>🎤 Voice & Audio</h4>
          <div className="setting-item">
            <label className="setting-label">
              <input 
                type="checkbox" 
                checked={settings.voiceEnabled}
                onChange={(e) => handleSettingChange('voiceEnabled', e.target.checked)}
              />
              <span className="checkmark"></span>
              Enable voice recognition
            </label>
          </div>
          <div className="setting-item">
            <label className="setting-label">Voice response speed:</label>
            <select 
              value={settings.responseSpeed}
              onChange={(e) => handleSettingChange('responseSpeed', e.target.value)}
            >
              <option value="slow">Slow</option>
              <option value="normal">Normal</option>
              <option value="fast">Fast</option>
            </select>
          </div>
        </div>

        <div className="settings-section">
          <h4>🤖 AI Behavior</h4>
          <div className="setting-item">
            <label className="setting-label">AI Personality:</label>
            <select 
              value={settings.aiPersonality}
              onChange={(e) => handleSettingChange('aiPersonality', e.target.value)}
            >
              <option value="professional">Professional</option>
              <option value="friendly">Friendly</option>
              <option value="casual">Casual</option>
              <option value="technical">Technical</option>
            </select>
          </div>
          <div className="setting-item">
            <label className="setting-label">Language:</label>
            <select 
              value={settings.language}
              onChange={(e) => handleSettingChange('language', e.target.value)}
            >
              <option value="english">English</option>
              <option value="spanish">Spanish</option>
              <option value="french">French</option>
              <option value="german">German</option>
            </select>
          </div>
        </div>

        <div className="settings-section">
          <h4>🖥️ System</h4>
          <div className="setting-item">
            <label className="setting-label">
              <input 
                type="checkbox" 
                checked={settings.autoStart}
                onChange={(e) => handleSettingChange('autoStart', e.target.checked)}
              />
              <span className="checkmark"></span>
              Auto-start with system
            </label>
          </div>
          <div className="setting-item">
            <label className="setting-label">
              <input 
                type="checkbox" 
                checked={settings.notifications}
                onChange={(e) => handleSettingChange('notifications', e.target.checked)}
              />
              <span className="checkmark"></span>
              Enable notifications
            </label>
          </div>
          <div className="setting-item">
            <label className="setting-label">
              <input 
                type="checkbox" 
                checked={settings.darkMode}
                onChange={(e) => handleSettingChange('darkMode', e.target.checked)}
              />
              <span className="checkmark"></span>
              Dark mode
            </label>
          </div>
        </div>

        <div className="settings-section">
          <h4>🔒 Privacy & Security</h4>
          <div className="setting-item">
            <label className="setting-label">
              <input type="checkbox" defaultChecked />
              <span className="checkmark"></span>
              Keep conversation history
            </label>
          </div>
          <div className="setting-item">
            <label className="setting-label">
              <input type="checkbox" defaultChecked />
              <span className="checkmark"></span>
              Anonymous usage analytics
            </label>
          </div>
          <div className="setting-item">
            <button className="danger-btn">🗑️ Clear All Data</button>
          </div>
        </div>

        <div className="settings-section">
          <h4>ℹ️ About</h4>
          <div className="about-info">
            <div className="info-item">
              <span className="info-label">Version:</span>
              <span className="info-value">BUDDY v2.0.0</span>
            </div>
            <div className="info-item">
              <span className="info-label">Build:</span>
              <span className="info-value">2025.08.21</span>
            </div>
            <div className="info-item">
              <span className="info-label">Status:</span>
              <span className="info-value status-healthy">🟢 Healthy</span>
            </div>
          </div>
          <div className="about-actions">
            <button className="info-btn">📖 Documentation</button>
            <button className="info-btn">🐛 Report Bug</button>
            <button className="info-btn">💝 Support</button>
          </div>
        </div>
      </div>
    </div>
  );
};

const StatusBar = ({ connectionStatus, activeSkills = 0, skills = [] }) => {
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const getSystemStatus = () => {
    if (connectionStatus === 'connected') return { icon: '🟢', text: 'Online', class: 'healthy' };
    if (connectionStatus === 'connecting') return { icon: '🟡', text: 'Connecting', class: 'warning' };
    return { icon: '🔴', text: 'Offline', class: 'error' };
  };

  const status = getSystemStatus();

  return (
    <div className="status-bar">
      <div className="status-section">
        <span className={`status-item ${status.class}`}>
          <span className="status-icon">{status.icon}</span>
          <span className="status-text">{status.text}</span>
        </span>
      </div>
      
      <div className="status-section">
        <span className="status-item">
          <span className="status-icon">⚡</span>
          <span className="status-text">{activeSkills}/{skills.length} Skills Active</span>
        </span>
      </div>
      
      <div className="status-section">
        <span className="status-item">
          <span className="status-icon">💬</span>
          <span className="status-text">Ready for Chat</span>
        </span>
      </div>
      
      <div className="status-section">
        <span className="status-item">
          <span className="status-icon">🕐</span>
          <span className="status-text">{currentTime}</span>
        </span>
      </div>
      
      <div className="status-section">
        <button className="mini-btn" title="Minimize">━</button>
        <button className="close-btn" title="Close">✕</button>
      </div>
    </div>
  );
};

function App() {
  const [currentView, setCurrentView] = useState('chat');
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [skills, setSkills] = useState([]);

  // Test backend connection
  useEffect(() => {
    const testConnection = async () => {
      try {
        if (window.electronAPI) {
          // Test backend connection
          const response = await window.electronAPI.invoke('backend:request', {
            method: 'GET',
            endpoint: '/health'
          });
          console.log('Backend health check:', response);
          
          if (response.success) {
            setConnectionStatus('connected');
            
            // Load skills
            const skillsResponse = await window.electronAPI.invoke('backend:request', {
              method: 'GET',
              endpoint: '/skills'
            });
            console.log('Skills response:', skillsResponse);
            
            // Extract skills array safely
            let skillsData = [];
            if (skillsResponse.success && skillsResponse.data) {
              if (skillsResponse.data.skills && Array.isArray(skillsResponse.data.skills)) {
                skillsData = skillsResponse.data.skills;
              } else if (Array.isArray(skillsResponse.data)) {
                skillsData = skillsResponse.data;
              }
            }
            
            setSkills(skillsData);
          } else {
            setConnectionStatus('disconnected');
          }
        }
      } catch (error) {
        console.error('Connection test failed:', error);
        setConnectionStatus('disconnected');
      }
    };

    testConnection();
    const interval = setInterval(testConnection, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (message) => {
    try {
      if (window.electronAPI) {
        console.log('Sending message to backend:', message);
        const response = await window.electronAPI.invoke('backend:request', {
          method: 'POST',
          endpoint: '/chat',
          data: { message: message }
        });
        console.log('Backend response received:', response);
        // IPC returns { success, data } from main.js
        if (response && response.success) {
          const data = response.data;
          if (data && typeof data === 'object' && typeof data.response === 'string') {
            return { response: data.response };
          }
          if (typeof data === 'string') {
            return { response: data };
          }
          console.error('Unexpected backend data shape:', data);
          return { response: 'Sorry, I could not understand the server response.' };
        }
        const errorText = response?.error || 'Backend request failed.';
        console.error('Backend error:', errorText, response?.details || '');
        return { response: 'I had trouble reaching the backend. Please try again.' };
      } else {
        throw new Error('Electron API not available');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // Surface a friendly message instead of throwing to avoid duplicate bubbles
      return { response: 'A technical error occurred. Ensure the backend is running on port 8082 and try again.' };
    }
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'chat':
        return <ChatInterface onSendMessage={handleSendMessage} />;
      case 'skills':
        return <SkillsPanel skills={skills} />;
      case 'voice':
        return <VoicePanel onSendMessage={handleSendMessage} />;
      case 'analytics':
        return <AnalyticsPanel skills={skills} />;
      case 'settings':
        return <SettingsPanel />;
      default:
        return <ChatInterface onSendMessage={handleSendMessage} />;
    }
  };

  return (
    <div className="app">
      <Sidebar
        currentView={currentView}
        onViewChange={setCurrentView}
        connectionStatus={connectionStatus}
      />

      <main className="app-main">
        <div className="app-content">
          {renderCurrentView()}
        </div>
        {/* Keep status bar anchored at the bottom of the right pane */}
        <StatusBar
          connectionStatus={connectionStatus}
          activeSkills={skills.filter(s => s.enabled).length}
          skills={skills}
        />
      </main>
    </div>
  );
}

export default App;
