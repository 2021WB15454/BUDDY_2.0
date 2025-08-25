# 🔗 BUDDY AI Assistant - Integration Guide

Complete guide for integrating BUDDY into various applications and platforms.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [JavaScript/Node.js Integration](#javascript-nodejs-integration)
3. [Python Integration](#python-integration)
4. [Web Integration](#web-integration)
5. [Mobile Integration](#mobile-integration)
6. [API Reference](#api-reference)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Prerequisites

- BUDDY AI Assistant server running on `http://localhost:8081`
- Basic knowledge of your target platform (JavaScript, Python, etc.)

### Basic Integration Steps

1. **Choose your platform SDK**
2. **Initialize BUDDY client**
3. **Send messages and handle responses**
4. **Customize for your use case**

---

## 🟨 JavaScript/Node.js Integration

### Installation

```bash
# Copy the SDK file to your project
cp integrations/javascript/buddy-sdk.js your-project/
```

### Basic Usage

```javascript
const BuddyClient = require('./buddy-sdk');

// Initialize client
const buddy = new BuddyClient({
    baseUrl: 'http://localhost:8081',
    userId: 'your_user_id',
    onMessage: (response) => console.log('BUDDY:', response.response)
});

// Send a message
async function chat() {
    const response = await buddy.chat('Hello BUDDY!');
    console.log(response.response);
}
```

### React Integration

```jsx
import React, { useState } from 'react';
import BuddyClient from './buddy-sdk';

const ChatComponent = () => {
    const [buddy] = useState(() => new BuddyClient());
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');

    const sendMessage = async () => {
        const response = await buddy.chat(input);
        setMessages(prev => [...prev, 
            { sender: 'user', text: input },
            { sender: 'buddy', text: response.response }
        ]);
        setInput('');
    };

    return (
        <div>
            <div className="messages">
                {messages.map((msg, i) => (
                    <div key={i}>{msg.sender}: {msg.text}</div>
                ))}
            </div>
            <input 
                value={input} 
                onChange={e => setInput(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && sendMessage()}
            />
            <button onClick={sendMessage}>Send</button>
        </div>
    );
};
```

### Express.js Server

```javascript
const express = require('express');
const BuddyClient = require('./buddy-sdk');

const app = express();
app.use(express.json());

const buddy = new BuddyClient();

app.post('/api/chat', async (req, res) => {
    try {
        const response = await buddy.chat(req.body.message);
        res.json({ success: true, data: response });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.listen(3000);
```

---

## 🐍 Python Integration

### Installation

```bash
# Install dependencies
pip install aiohttp requests

# Copy SDK to your project
cp integrations/python/buddy_sdk.py your-project/
```

### Basic Usage

```python
from buddy_sdk import BuddyClient

# Initialize client
buddy = BuddyClient(
    base_url="http://localhost:8081",
    user_id="your_user_id"
)

# Synchronous chat
response = buddy.chat("Hello BUDDY!")
print(f"BUDDY: {response.response}")

# Asynchronous chat
async def async_chat():
    response = await buddy.async_chat("Tell me about AI")
    print(f"BUDDY: {response.response}")
```

### Flask Web App

```python
from flask import Flask, request, jsonify
from buddy_sdk import BuddyClient, BuddyConversation

app = Flask(__name__)
buddy = BuddyClient()
conversations = {}

@app.route('/api/chat', methods=['POST'])
def chat():
    user_id = request.json.get('user_id', 'web_user')
    message = request.json.get('message')
    
    if user_id not in conversations:
        conversations[user_id] = BuddyConversation(buddy)
    
    response = conversations[user_id].chat(message)
    return jsonify({
        'response': response.response,
        'confidence': response.confidence
    })

app.run(debug=True)
```

### Discord Bot

```python
import discord
from discord.ext import commands
from buddy_sdk import BuddyClient

bot = commands.Bot(command_prefix='!buddy ')
buddy = BuddyClient()

@bot.command(name='chat')
async def buddy_chat(ctx, *, message):
    response = await buddy.async_chat(message)
    await ctx.send(f"🤖 {response.response}")

bot.run('YOUR_DISCORD_TOKEN')
```

---

## 🌐 Web Integration

### Embed Chat Widget

Simply include the pre-built widget in any HTML page:

```html
<!DOCTYPE html>
<html>
<head>
    <title>My Website</title>
</head>
<body>
    <!-- Your existing content -->
    
    <!-- BUDDY Chat Widget -->
    <div id="buddy-widget">
        <!-- Widget content loaded from chat-widget.html -->
    </div>
    
    <script src="integrations/javascript/buddy-sdk.js"></script>
    <script>
        const buddy = new BuddyClient();
        // Widget initialization code
    </script>
</body>
</html>
```

### Custom Implementation

```html
<div id="chat-container">
    <div id="messages"></div>
    <input type="text" id="message-input" placeholder="Type your message...">
    <button onclick="sendMessage()">Send</button>
</div>

<script>
const buddy = new BuddyClient({ baseUrl: 'http://localhost:8081' });

async function sendMessage() {
    const input = document.getElementById('message-input');
    const messages = document.getElementById('messages');
    
    const userMessage = input.value;
    messages.innerHTML += `<div>You: ${userMessage}</div>`;
    
    const response = await buddy.chat(userMessage);
    messages.innerHTML += `<div>BUDDY: ${response.response}</div>`;
    
    input.value = '';
}
</script>
```

---

## 📱 Mobile Integration

### React Native

```jsx
import React from 'react';
import { BuddyChat } from './integrations/mobile/BuddyChat';

const App = () => {
    return (
        <BuddyChat 
            baseUrl="http://your-server:8081"
            onMessage={(message) => console.log('New message:', message)}
            onError={(error) => console.error('Error:', error)}
        />
    );
};

export default App;
```

### Floating Chat Button

```jsx
import { BuddyFloatingButton, BuddyChat } from './BuddyChat';

const App = () => {
    const [showChat, setShowChat] = useState(false);

    return (
        <View style={{ flex: 1 }}>
            {/* Your app content */}
            
            {showChat ? (
                <BuddyChat />
            ) : (
                <BuddyFloatingButton 
                    onPress={() => setShowChat(true)}
                />
            )}
        </View>
    );
};
```

---

## 📡 API Reference

### Core Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/chat` | POST | Send message to BUDDY | `message`, `user_id`, `session_id` |
| `/skills` | GET | Get available skills | None |
| `/health` | GET | Check server health | None |
| `/conversations` | GET | Get conversation history | `user_id`, `limit`, `offset` |

### Request Format

```json
{
    "message": "Hello BUDDY!",
    "user_id": "user_123",
    "session_id": "session_abc",
    "context": {},
    "metadata": {
        "timestamp": "2025-08-25T12:00:00Z",
        "platform": "web"
    }
}
```

### Response Format

```json
{
    "response": "Hello! How can I help you today?",
    "confidence": 0.95,
    "skill_used": "greeting",
    "execution_time": 0.123,
    "conversation_id": "conv_xyz",
    "metadata": {
        "timestamp": "2025-08-25T12:00:01Z"
    }
}
```

---

## ✅ Best Practices

### 🔐 Security

1. **API Key Authentication** (if enabled)
   ```javascript
   const buddy = new BuddyClient({
       apiKey: process.env.BUDDY_API_KEY
   });
   ```

2. **Rate Limiting**
   ```javascript
   // Implement client-side rate limiting
   const rateLimiter = new RateLimiter(10, 60000); // 10 requests per minute
   ```

3. **Input Validation**
   ```javascript
   function validateMessage(message) {
       if (!message || message.length > 500) {
           throw new Error('Invalid message length');
       }
       return message.trim();
   }
   ```

### 🚀 Performance

1. **Connection Pooling**
   ```javascript
   const buddy = new BuddyClient({
       maxConnections: 10,
       timeout: 30000
   });
   ```

2. **Caching Responses**
   ```javascript
   const cache = new Map();
   
   async function cachedChat(message) {
       if (cache.has(message)) {
           return cache.get(message);
       }
       
       const response = await buddy.chat(message);
       cache.set(message, response);
       return response;
   }
   ```

3. **Async/Await Usage**
   ```javascript
   // Parallel skill execution
   const [time, weather, calc] = await Promise.all([
       buddy.executeSkill('time'),
       buddy.executeSkill('weather'),
       buddy.executeSkill('calculate', { expression: '2+2' })
   ]);
   ```

### 🎯 User Experience

1. **Typing Indicators**
   ```javascript
   function showTyping() {
       // Show typing animation
   }
   
   function hideTyping() {
       // Hide typing animation
   }
   ```

2. **Error Handling**
   ```javascript
   try {
       const response = await buddy.chat(message);
   } catch (error) {
       if (error.message.includes('timeout')) {
           // Handle timeout
       } else if (error.message.includes('network')) {
           // Handle network error
       } else {
           // Handle general error
       }
   }
   ```

3. **Conversation Persistence**
   ```javascript
   // Save conversation to localStorage
   localStorage.setItem('buddy_conversation', JSON.stringify(messages));
   
   // Load conversation on page load
   const savedMessages = JSON.parse(localStorage.getItem('buddy_conversation') || '[]');
   ```

---

## 🔧 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Check if BUDDY server is running
   curl http://localhost:8081/health
   
   # Start BUDDY server
   ./launch-buddy.bat
   ```

2. **CORS Errors (Web)**
   ```javascript
   // Add CORS headers to BUDDY server or use proxy
   const buddy = new BuddyClient({
       baseUrl: '/api/buddy'  // Use proxy endpoint
   });
   ```

3. **Timeout Errors**
   ```javascript
   const buddy = new BuddyClient({
       timeout: 60000  // Increase timeout to 60 seconds
   });
   ```

4. **Memory Leaks**
   ```javascript
   // Clean up resources
   window.addEventListener('beforeunload', () => {
       buddy.disconnect();
   });
   ```

### Debug Mode

```javascript
const buddy = new BuddyClient({
    debug: true,  // Enable debug logging
    onError: (error) => {
        console.error('BUDDY Error:', error);
        // Send to error tracking service
    }
});
```

### Health Monitoring

```javascript
// Regular health checks
setInterval(async () => {
    try {
        await buddy.getHealth();
        console.log('BUDDY is healthy');
    } catch (error) {
        console.warn('BUDDY health check failed:', error);
    }
}, 60000); // Check every minute
```

---

## 📚 Example Applications

### Complete Examples Available

1. **🌐 Web Chat Widget** - `integrations/web/chat-widget.html`
2. **⚛️ React Chat App** - See JavaScript examples
3. **🐍 Python Chatbot** - `integrations/python/examples.py`
4. **📱 React Native App** - `integrations/mobile/BuddyChat.js`
5. **🤖 Discord Bot** - Python integration example
6. **📊 Data Analysis Tool** - Python integration example

### Run Examples

```bash
# JavaScript examples
cd integrations/javascript
node examples.js

# Python examples  
cd integrations/python
python examples.py

# Web widget
cd integrations/web
# Open chat-widget.html in browser

# Mobile (React Native)
cd integrations/mobile
# Import BuddyChat.js in your React Native project
```

---

## 🆘 Support

- **Documentation**: This file and inline code comments
- **Issues**: Check BUDDY server logs and client console
- **GitHub**: https://github.com/2021WB15454/BUDDY_2.0
- **API**: http://localhost:8081/docs for interactive documentation

---

## 🔄 Updates

This integration guide is updated with each BUDDY release. Check the GitHub repository for the latest version and new integration examples.

**Last Updated**: August 25, 2025
**BUDDY Version**: 2.0
**API Version**: 1.0
