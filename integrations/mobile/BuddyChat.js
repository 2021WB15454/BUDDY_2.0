/**
 * BUDDY AI Assistant - React Native Integration
 * 
 * This file provides components and utilities for integrating BUDDY
 * into React Native mobile applications
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Animated,
  Dimensions
} from 'react-native';

// BUDDY API Service
class BuddyMobileClient {
  constructor(baseUrl = 'http://localhost:8081') {
    this.baseUrl = baseUrl;
    this.userId = this.generateUserId();
    this.sessionId = this.generateSessionId();
  }

  generateUserId() {
    return `mobile_user_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateSessionId() {
    return `mobile_session_${Math.random().toString(36).substr(2, 9)}`;
  }

  async chat(message, options = {}) {
    try {
      const response = await fetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          user_id: options.userId || this.userId,
          session_id: options.sessionId || this.sessionId,
          context: options.context || {},
          metadata: {
            platform: Platform.OS,
            timestamp: new Date().toISOString(),
            ...options.metadata
          }
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('BUDDY chat error:', error);
      throw error;
    }
  }

  async getSkills() {
    try {
      const response = await fetch(`${this.baseUrl}/skills`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('BUDDY skills error:', error);
      throw error;
    }
  }

  async getHealth() {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('BUDDY health error:', error);
      throw error;
    }
  }
}

// Message Component
const Message = ({ message, isUser, timestamp, confidence }) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, []);

  return (
    <Animated.View style={[
      styles.messageContainer,
      isUser ? styles.userMessage : styles.buddyMessage,
      { opacity: fadeAnim }
    ]}>
      <View style={[
        styles.messageBubble,
        isUser ? styles.userBubble : styles.buddyBubble
      ]}>
        <Text style={[
          styles.messageText,
          isUser ? styles.userText : styles.buddyText
        ]}>
          {message}
        </Text>
        
        {!isUser && confidence && confidence < 0.7 && (
          <Text style={styles.confidenceText}>
            Confidence: {Math.round(confidence * 100)}%
          </Text>
        )}
        
        <Text style={styles.timestamp}>
          {new Date(timestamp).toLocaleTimeString()}
        </Text>
      </View>
    </Animated.View>
  );
};

// Typing Indicator Component
const TypingIndicator = () => {
  const dots = useRef([
    new Animated.Value(0),
    new Animated.Value(0),
    new Animated.Value(0)
  ]).current;

  useEffect(() => {
    const animateDots = () => {
      const animations = dots.map((dot, index) =>
        Animated.sequence([
          Animated.delay(index * 200),
          Animated.timing(dot, {
            toValue: 1,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(dot, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          })
        ])
      );

      Animated.loop(
        Animated.parallel(animations),
        { iterations: -1 }
      ).start();
    };

    animateDots();
  }, []);

  return (
    <View style={styles.typingContainer}>
      <View style={styles.typingBubble}>
        <View style={styles.typingDots}>
          {dots.map((dot, index) => (
            <Animated.View
              key={index}
              style={[
                styles.typingDot,
                { opacity: dot }
              ]}
            />
          ))}
        </View>
      </View>
    </View>
  );
};

// Skill Pills Component
const SkillPills = ({ skills, onSkillPress }) => {
  return (
    <View style={styles.skillsContainer}>
      <Text style={styles.skillsTitle}>Try asking about:</Text>
      <View style={styles.skillsGrid}>
        {skills.slice(0, 6).map((skill, index) => (
          <TouchableOpacity
            key={index}
            style={styles.skillPill}
            onPress={() => onSkillPress(skill)}
          >
            <Text style={styles.skillText}>{skill.name}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
};

// Main Chat Component
const BuddyChat = ({ 
  baseUrl = 'http://localhost:8081',
  onMessage,
  onError,
  style 
}) => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [skills, setSkills] = useState([]);
  const [buddy] = useState(() => new BuddyMobileClient(baseUrl));
  const scrollViewRef = useRef();

  useEffect(() => {
    initializeBuddy();
  }, []);

  const initializeBuddy = async () => {
    try {
      // Check BUDDY health
      await buddy.getHealth();
      
      // Load skills
      const skillsData = await buddy.getSkills();
      setSkills(skillsData);
      
      // Add welcome message
      addMessage(
        "Hello! I'm BUDDY, your AI assistant. How can I help you today?",
        false,
        Date.now(),
        1.0
      );
      
    } catch (error) {
      console.error('Failed to initialize BUDDY:', error);
      addMessage(
        "Sorry, I'm having trouble connecting. Please check your connection and try again.",
        false,
        Date.now(),
        0.0
      );
      
      if (onError) {
        onError(error);
      }
    }
  };

  const addMessage = (text, isUser, timestamp, confidence) => {
    const newMessage = {
      id: Date.now() + Math.random(),
      text,
      isUser,
      timestamp,
      confidence
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    if (onMessage) {
      onMessage(newMessage);
    }
    
    // Scroll to bottom
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = inputText.trim();
    setInputText('');
    
    // Add user message
    addMessage(userMessage, true, Date.now());
    
    setIsLoading(true);

    try {
      const response = await buddy.chat(userMessage);
      
      // Add BUDDY response
      addMessage(
        response.response,
        false,
        Date.now(),
        response.confidence
      );
      
    } catch (error) {
      console.error('Chat error:', error);
      addMessage(
        "Sorry, I encountered an error. Please try again.",
        false,
        Date.now(),
        0.0
      );
      
      if (onError) {
        onError(error);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkillPress = (skill) => {
    const messages = {
      'time': 'What time is it?',
      'weather': 'What\'s the weather like?',
      'calculate': 'Help me with math',
      'help': 'What can you help me with?',
      'greeting': 'Hello!'
    };
    
    const message = messages[skill.name] || `Tell me about ${skill.name}`;
    setInputText(message);
  };

  const clearChat = () => {
    Alert.alert(
      'Clear Chat',
      'Are you sure you want to clear the conversation?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Clear', 
          style: 'destructive',
          onPress: () => {
            setMessages([]);
            addMessage(
              "Chat cleared! How can I help you?",
              false,
              Date.now(),
              1.0
            );
          }
        }
      ]
    );
  };

  return (
    <KeyboardAvoidingView 
      style={[styles.container, style]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🤖 BUDDY AI Assistant</Text>
        <TouchableOpacity onPress={clearChat} style={styles.clearButton}>
          <Text style={styles.clearButtonText}>Clear</Text>
        </TouchableOpacity>
      </View>

      {/* Messages */}
      <ScrollView
        ref={scrollViewRef}
        style={styles.messagesContainer}
        showsVerticalScrollIndicator={false}
      >
        {messages.map((message) => (
          <Message
            key={message.id}
            message={message.text}
            isUser={message.isUser}
            timestamp={message.timestamp}
            confidence={message.confidence}
          />
        ))}
        
        {isLoading && <TypingIndicator />}
        
        {messages.length === 1 && skills.length > 0 && (
          <SkillPills 
            skills={skills}
            onSkillPress={handleSkillPress}
          />
        )}
      </ScrollView>

      {/* Input */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.textInput}
          value={inputText}
          onChangeText={setInputText}
          placeholder="Type your message..."
          multiline
          maxLength={500}
          editable={!isLoading}
        />
        <TouchableOpacity
          style={[
            styles.sendButton,
            (!inputText.trim() || isLoading) && styles.sendButtonDisabled
          ]}
          onPress={sendMessage}
          disabled={!inputText.trim() || isLoading}
        >
          <Text style={styles.sendButtonText}>Send</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
};

// Floating Chat Button Component
const BuddyFloatingButton = ({ onPress, style }) => {
  const [isVisible, setIsVisible] = useState(true);
  const fadeAnim = useRef(new Animated.Value(1)).current;

  const handlePress = () => {
    Animated.sequence([
      Animated.timing(fadeAnim, {
        toValue: 0.8,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 100,
        useNativeDriver: true,
      })
    ]).start();
    
    if (onPress) {
      onPress();
    }
  };

  if (!isVisible) return null;

  return (
    <Animated.View style={[
      styles.floatingButton,
      style,
      { opacity: fadeAnim }
    ]}>
      <TouchableOpacity
        style={styles.floatingButtonInner}
        onPress={handlePress}
        activeOpacity={0.8}
      >
        <Text style={styles.floatingButtonText}>💬</Text>
      </TouchableOpacity>
    </Animated.View>
  );
};

// Styles
const { width, height } = Dimensions.get('window');

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#667eea',
    paddingTop: Platform.OS === 'ios' ? 50 : 16,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: 'white',
  },
  clearButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  clearButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  messagesContainer: {
    flex: 1,
    padding: 16,
  },
  messageContainer: {
    marginBottom: 12,
  },
  userMessage: {
    alignItems: 'flex-end',
  },
  buddyMessage: {
    alignItems: 'flex-start',
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 16,
  },
  userBubble: {
    backgroundColor: '#667eea',
    borderBottomRightRadius: 4,
  },
  buddyBubble: {
    backgroundColor: 'white',
    borderBottomLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: 'white',
  },
  buddyText: {
    color: '#333',
  },
  confidenceText: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
    fontStyle: 'italic',
  },
  timestamp: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
    textAlign: 'right',
  },
  typingContainer: {
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  typingBubble: {
    backgroundColor: 'white',
    padding: 12,
    borderRadius: 16,
    borderBottomLeftRadius: 4,
  },
  typingDots: {
    flexDirection: 'row',
  },
  typingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#999',
    marginHorizontal: 2,
  },
  skillsContainer: {
    marginVertical: 16,
  },
  skillsTitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
    fontWeight: '600',
  },
  skillsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillPill: {
    backgroundColor: '#e0e0e0',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
    marginRight: 8,
    marginBottom: 8,
  },
  skillText: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: 'white',
    alignItems: 'flex-end',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 4,
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginRight: 12,
    fontSize: 16,
    maxHeight: 100,
  },
  sendButton: {
    backgroundColor: '#667eea',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 20,
  },
  sendButtonDisabled: {
    backgroundColor: '#ccc',
  },
  sendButtonText: {
    color: 'white',
    fontWeight: '600',
    fontSize: 16,
  },
  floatingButton: {
    position: 'absolute',
    bottom: 30,
    right: 30,
    zIndex: 1000,
  },
  floatingButtonInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#667eea',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  floatingButtonText: {
    fontSize: 24,
  },
});

// Export components
export {
  BuddyChat,
  BuddyFloatingButton,
  BuddyMobileClient,
  Message,
  TypingIndicator,
  SkillPills
};

export default BuddyChat;
