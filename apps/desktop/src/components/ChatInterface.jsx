import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, AlertCircle, User, Bot } from 'lucide-react';

const ChatInterface = ({ 
  onSendMessage, 
  isConnected, 
  connectionError,
  transcript 
}) => {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello! I\'m BUDDY, your personal AI assistant. How can I help you today?',
      timestamp: new Date()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Handle voice transcript
  useEffect(() => {
    if (transcript && transcript.trim()) {
      setMessage(transcript);
    }
  }, [transcript]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!message.trim() || isLoading || !isConnected) {
      return;
    }

    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: message.trim(),
      timestamp: new Date()
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setMessage('');
    setIsLoading(true);

    try {
      const response = await onSendMessage(userMessage.content);
      
      if (response.success) {
        const assistantMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: response.data.response || 'I understand your request.',
          timestamp: new Date(),
          metadata: {
            intent: response.data.intent,
            confidence: response.data.confidence,
            duration: response.data.duration_ms
          }
        };
        
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        throw new Error(response.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('Chat error:', error);
      
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        type: 'error',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const clearMessages = () => {
    setMessages([
      {
        id: '1',
        type: 'assistant',
        content: 'Chat cleared. How can I help you?',
        timestamp: new Date()
      }
    ]);
  };

  return (
    <div className="chat-interface">
      {/* Header */}
      <div className="chat-header">
        <h2 className="chat-title">Chat with BUDDY</h2>
        <div className="chat-actions">
          <button 
            className="btn btn-secondary btn-sm"
            onClick={clearMessages}
            disabled={isLoading}
          >
            Clear Chat
          </button>
        </div>
      </div>

      {/* Connection Error */}
      {connectionError && (
        <div className="connection-error">
          <AlertCircle size={16} />
          <span>Connection Error: {connectionError}</span>
        </div>
      )}

      {/* Messages */}
      <div className="messages-container">
        <div className="messages">
          {messages.map(msg => (
            <div 
              key={msg.id} 
              className={`message ${msg.type}`}
            >
              <div className="message-avatar">
                {msg.type === 'user' ? (
                  <User size={16} />
                ) : msg.type === 'assistant' ? (
                  <Bot size={16} />
                ) : (
                  <AlertCircle size={16} />
                )}
              </div>
              
              <div className="message-content">
                <div className="message-text">
                  {msg.content}
                </div>
                
                <div className="message-meta">
                  <span className="message-time">
                    {msg.timestamp.toLocaleTimeString()}
                  </span>
                  
                  {msg.metadata && (
                    <>
                      {msg.metadata.intent && (
                        <span className="message-intent">
                          Intent: {msg.metadata.intent}
                        </span>
                      )}
                      {msg.metadata.duration && (
                        <span className="message-duration">
                          {msg.metadata.duration}ms
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message assistant loading">
              <div className="message-avatar">
                <Loader size={16} className="animate-spin" />
              </div>
              <div className="message-content">
                <div className="message-text">
                  BUDDY is thinking...
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="chat-input-container">
          <textarea
            ref={inputRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              isConnected 
                ? "Type your message... (Shift+Enter for new line)"
                : "Connecting to BUDDY..."
            }
            className="chat-input"
            disabled={!isConnected || isLoading}
            rows={1}
          />
          
          <button
            type="submit"
            className="btn btn-primary chat-send-btn"
            disabled={!message.trim() || isLoading || !isConnected}
          >
            {isLoading ? (
              <Loader size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;
