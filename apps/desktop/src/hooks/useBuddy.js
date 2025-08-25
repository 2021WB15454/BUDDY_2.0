import { useState, useEffect, useCallback } from 'react';

export const useBuddy = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const [skills, setSkills] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [status, setStatus] = useState(null);
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: "Hello! I'm BUDDY, your personal AI assistant. How can I help you today?",
      timestamp: new Date().toISOString()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastActivity, setLastActivity] = useState(null);

  // Check connection status
  const checkConnection = useCallback(async () => {
    try {
      if (window.buddy) {
        console.log('Checking BUDDY connection...');
        const response = await window.buddy.getStatus();
        console.log('Health check response:', response);
        
        if (response && response.success) {
          setIsConnected(true);
          setConnectionError(null);
          setConnectionStatus('connected');
          setStatus(response.data);
          console.log('BUDDY connected successfully');
        } else {
          throw new Error(response?.error || 'Unknown connection error');
        }
      } else {
        throw new Error('BUDDY API not available');
      }
    } catch (error) {
      console.error('Connection check failed:', error);
      setIsConnected(false);
      setConnectionError(error.message);
      setConnectionStatus('disconnected');
    }
  }, []);

  // Load skills
  const loadSkills = useCallback(async () => {
    try {
      if (window.buddy) {
        const response = await window.buddy.getSkills();
        if (response.success) {
          setSkills(response.data.skills || []);
        }
      }
    } catch (error) {
      console.error('Failed to load skills:', error);
    }
  }, []);

  // Load metrics
  const loadMetrics = useCallback(async () => {
    try {
      if (window.buddy) {
        const response = await window.buddy.getMetrics();
        if (response.success) {
          setMetrics(response.data);
        }
      }
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  }, []);

  // Send message to BUDDY
  const sendMessage = useCallback(async (message, context = {}) => {
    if (!isConnected) {
      throw new Error('Not connected to BUDDY');
    }

    setIsLoading(true);
    try {
      // Add user message to conversation
      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, userMessage]);
      
      const response = await window.buddy.sendMessage(message, context);
      
      if (response && response.success) {
        // Add assistant response to conversation
        const assistantMessage = {
          id: Date.now() + 1,
          role: 'assistant',
          content: response.data.response || 'I received your message but had trouble responding.',
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, assistantMessage]);
        setLastActivity(new Date().toISOString());
      } else {
        throw new Error(response?.error || 'Failed to get response');
      }
      
      return response;
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Add error message to conversation
      const errorMessage = {
        id: Date.now() + 2,
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
      
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [isConnected]);

  // Initialize connection and data loading
  useEffect(() => {
    console.log('Initializing BUDDY connection...');
    checkConnection();
    
    const interval = setInterval(() => {
      checkConnection();
      if (isConnected) {
        loadMetrics();
      }
    }, 10000); // Check every 10 seconds

    return () => clearInterval(interval);
  }, [checkConnection, loadMetrics, isConnected]);

  // Load skills when connected
  useEffect(() => {
    if (isConnected) {
      loadSkills();
    }
  }, [isConnected, loadSkills]);

  return {
    isConnected,
    connectionError,
    connectionStatus,
    skills,
    metrics,
    status,
    messages,
    isLoading,
    lastActivity,
    sendMessage,
    checkConnection,
    loadSkills,
    loadMetrics
  };
};
