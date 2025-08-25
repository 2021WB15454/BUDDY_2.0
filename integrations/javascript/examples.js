/**
 * BUDDY JavaScript SDK - Usage Examples
 * 
 * This file demonstrates how to integrate BUDDY into various JavaScript applications
 */

// ===== Basic Usage Example =====

const BuddyClient = require('./buddy-sdk');

// Initialize BUDDY client
const buddy = new BuddyClient({
    baseUrl: 'http://localhost:8081',
    userId: 'user_123',
    sessionId: 'session_abc',
    onMessage: (response) => {
        console.log('BUDDY says:', response.response);
    },
    onError: (error) => {
        console.error('BUDDY error:', error.message);
    }
});

// ===== Simple Chat Example =====

async function basicChat() {
    try {
        // Send a message to BUDDY
        const response = await buddy.chat('Hello BUDDY! How are you today?');
        console.log('BUDDY Response:', response.response);
        
        // Send a follow-up message
        const followUp = await buddy.chat('What can you help me with?');
        console.log('BUDDY Capabilities:', followUp.response);
        
    } catch (error) {
        console.error('Chat error:', error);
    }
}

// ===== Skill Execution Example =====

async function useSkills() {
    try {
        // Get available skills
        const skills = await buddy.getSkills();
        console.log('Available skills:', skills.map(s => s.name));
        
        // Execute specific skills
        const timeResult = await buddy.executeSkill('time', {
            timezone: 'UTC',
            format: '12-hour'
        });
        console.log('Current time:', timeResult);
        
        const weatherResult = await buddy.executeSkill('weather', {
            location: 'New York',
            units: 'metric'
        });
        console.log('Weather:', weatherResult);
        
        const calcResult = await buddy.executeSkill('calculate', {
            expression: '15 * 24 + 100'
        });
        console.log('Calculation:', calcResult);
        
    } catch (error) {
        console.error('Skill execution error:', error);
    }
}

// ===== Streaming Chat Example =====

async function streamingChat() {
    try {
        console.log('Starting streaming conversation...');
        
        await buddy.streamChat('Tell me a story about AI', (chunk) => {
            if (chunk.type === 'message') {
                process.stdout.write(chunk.content);
            } else if (chunk.type === 'complete') {
                console.log('\n\nStory complete!');
            }
        });
        
    } catch (error) {
        console.error('Streaming error:', error);
    }
}

// ===== React Component Example =====

const reactExample = `
import React, { useState, useEffect } from 'react';
import BuddyClient from './buddy-sdk';

const ChatComponent = () => {
    const [buddy] = useState(() => new BuddyClient({
        baseUrl: 'http://localhost:8081'
    }));
    
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!input.trim()) return;
        
        const userMessage = { sender: 'user', text: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);
        
        try {
            const response = await buddy.chat(input);
            const buddyMessage = { sender: 'buddy', text: response.response };
            setMessages(prev => [...prev, buddyMessage]);
        } catch (error) {
            console.error('Chat error:', error);
            const errorMessage = { sender: 'system', text: 'Error: Could not reach BUDDY' };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-container">
            <div className="messages">
                {messages.map((msg, index) => (
                    <div key={index} className={\`message \${msg.sender}\`}>
                        <strong>{msg.sender}:</strong> {msg.text}
                    </div>
                ))}
                {loading && <div className="message system">BUDDY is thinking...</div>}
            </div>
            
            <div className="input-area">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Type your message..."
                />
                <button onClick={sendMessage} disabled={loading}>
                    Send
                </button>
            </div>
        </div>
    );
};

export default ChatComponent;
`;

// ===== Vue.js Component Example =====

const vueExample = `
<template>
  <div class="buddy-chat">
    <div class="messages">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.sender]"
      >
        <strong>{{ message.sender }}:</strong> {{ message.text }}
      </div>
      <div v-if="loading" class="message system">BUDDY is thinking...</div>
    </div>
    
    <div class="input-area">
      <input
        v-model="input"
        @keyup.enter="sendMessage"
        placeholder="Type your message..."
        :disabled="loading"
      />
      <button @click="sendMessage" :disabled="loading || !input.trim()">
        Send
      </button>
    </div>
  </div>
</template>

<script>
import BuddyClient from './buddy-sdk';

export default {
  name: 'BuddyChat',
  data() {
    return {
      buddy: new BuddyClient({ baseUrl: 'http://localhost:8081' }),
      messages: [],
      input: '',
      loading: false
    };
  },
  methods: {
    async sendMessage() {
      if (!this.input.trim()) return;
      
      this.messages.push({ sender: 'user', text: this.input });
      const userInput = this.input;
      this.input = '';
      this.loading = true;
      
      try {
        const response = await this.buddy.chat(userInput);
        this.messages.push({ sender: 'buddy', text: response.response });
      } catch (error) {
        console.error('Chat error:', error);
        this.messages.push({ 
          sender: 'system', 
          text: 'Error: Could not reach BUDDY' 
        });
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
`;

// ===== Express.js Server Integration =====

const expressExample = `
const express = require('express');
const BuddyClient = require('./buddy-sdk');

const app = express();
app.use(express.json());

const buddy = new BuddyClient({
    baseUrl: 'http://localhost:8081'
});

// Chatbot endpoint for your web app
app.post('/api/chat', async (req, res) => {
    try {
        const { message, userId, sessionId } = req.body;
        
        const response = await buddy.chat(message, {
            userId: userId || 'web_user',
            sessionId: sessionId || 'web_session'
        });
        
        res.json({
            success: true,
            data: response
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Skills endpoint
app.get('/api/skills', async (req, res) => {
    try {
        const skills = await buddy.getSkills();
        res.json({ success: true, data: skills });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.listen(3000, () => {
    console.log('Server running on http://localhost:3000');
});
`;

// ===== Browser Widget Example =====

const widgetExample = `
<!-- Embed this in any HTML page for instant BUDDY chat -->
<div id="buddy-widget">
    <div id="buddy-toggle">💬 Chat with BUDDY</div>
    <div id="buddy-chat" style="display: none;">
        <div id="buddy-header">
            <span>BUDDY AI Assistant</span>
            <button id="buddy-close">×</button>
        </div>
        <div id="buddy-messages"></div>
        <div id="buddy-input">
            <input type="text" id="buddy-text" placeholder="Type your message...">
            <button id="buddy-send">Send</button>
        </div>
    </div>
</div>

<script src="./buddy-sdk.js"></script>
<script>
    const buddy = new BuddyClient({ baseUrl: 'http://localhost:8081' });
    const widget = {
        toggle: document.getElementById('buddy-toggle'),
        chat: document.getElementById('buddy-chat'),
        messages: document.getElementById('buddy-messages'),
        input: document.getElementById('buddy-text'),
        send: document.getElementById('buddy-send'),
        close: document.getElementById('buddy-close')
    };

    widget.toggle.onclick = () => {
        widget.chat.style.display = 'block';
        widget.toggle.style.display = 'none';
    };

    widget.close.onclick = () => {
        widget.chat.style.display = 'none';
        widget.toggle.style.display = 'block';
    };

    widget.send.onclick = async () => {
        const message = widget.input.value.trim();
        if (!message) return;

        widget.messages.innerHTML += \`<div><strong>You:</strong> \${message}</div>\`;
        widget.input.value = '';

        try {
            const response = await buddy.chat(message);
            widget.messages.innerHTML += \`<div><strong>BUDDY:</strong> \${response.response}</div>\`;
            widget.messages.scrollTop = widget.messages.scrollHeight;
        } catch (error) {
            widget.messages.innerHTML += \`<div><strong>Error:</strong> Could not reach BUDDY</div>\`;
        }
    };

    widget.input.onkeypress = (e) => {
        if (e.key === 'Enter') widget.send.click();
    };
</script>
`;

// Run examples
if (require.main === module) {
    console.log('🤖 BUDDY JavaScript SDK Examples');
    console.log('================================\n');
    
    console.log('1. Running basic chat example...');
    basicChat();
    
    setTimeout(() => {
        console.log('\n2. Running skills example...');
        useSkills();
    }, 2000);
    
    setTimeout(() => {
        console.log('\n3. Running streaming example...');
        streamingChat();
    }, 4000);
}

module.exports = {
    basicChat,
    useSkills,
    streamingChat,
    reactExample,
    vueExample,
    expressExample,
    widgetExample
};
