/**
 * BUDDY Cross-Device Synchronization Manager
 * Handles real-time sync between devices and conversation continuity
 */

class BuddyDeviceSync {
    constructor(apiBase = 'http://localhost:8081', userId = null) {
        this.apiBase = apiBase;
        this.userId = userId || this.generateUserId();
        this.deviceId = this.getDeviceId();
        this.deviceType = this.getDeviceType();
        this.conversationHistory = [];
        this.isConnected = false;
        
        // WebSocket for real-time sync (when available)
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.init();
    }
    
    init() {
        console.log('🔄 Initializing BUDDY Device Sync...');
        console.log(`📱 Device: ${this.deviceType} (${this.deviceId})`);
        console.log(`👤 User: ${this.userId}`);
        
        this.setupWebSocket();
        this.loadConversationHistory();
    }
    
    generateUserId() {
        // Generate or retrieve persistent user ID
        let userId = localStorage.getItem('buddy_user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('buddy_user_id', userId);
        }
        return userId;
    }
    
    getDeviceId() {
        let deviceId = localStorage.getItem('buddy_device_id');
        if (!deviceId) {
            deviceId = this.deviceType + '_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
            localStorage.setItem('buddy_device_id', deviceId);
        }
        return deviceId;
    }
    
    getDeviceType() {
        // Detect device type based on browser characteristics
        const userAgent = navigator.userAgent.toLowerCase();
        const screenWidth = window.screen.width;
        
        if (/mobile|android|iphone|ipad|ipod|blackberry|windows phone/.test(userAgent)) {
            if (screenWidth < 600) {
                return 'mobile';
            } else {
                return 'tablet';
            }
        } else if (screenWidth < 800) {
            return 'desktop_small';
        } else {
            return 'desktop';
        }
    }
    
    setupWebSocket() {
        try {
            // Try to establish WebSocket connection for real-time sync
            const wsUrl = this.apiBase.replace('http://', 'ws://') + '/ws';
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected for real-time sync');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                // Send device registration
                this.websocket.send(JSON.stringify({
                    type: 'device_register',
                    user_id: this.userId,
                    device_id: this.deviceId,
                    device_type: this.deviceType,
                    capabilities: this.getDeviceCapabilities()
                }));
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(JSON.parse(event.data));
            };
            
            this.websocket.onclose = () => {
                console.log('❌ WebSocket disconnected');
                this.isConnected = false;
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.log('⚠️ WebSocket error:', error);
                this.isConnected = false;
            };
            
        } catch (error) {
            console.log('⚠️ WebSocket not available, using polling fallback');
            this.setupPollingFallback();
        }
    }
    
    setupPollingFallback() {
        // Fallback to polling for sync when WebSocket isn't available
        setInterval(() => {
            this.checkForUpdates();
        }, 10000); // Check every 10 seconds
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.setupWebSocket();
            }, 2000 * this.reconnectAttempts); // Exponential backoff
        }
    }
    
    getDeviceCapabilities() {
        return {
            screen_size: window.screen.width + 'x' + window.screen.height,
            touch_enabled: 'ontouchstart' in window,
            voice_enabled: 'speechSynthesis' in window,
            camera_enabled: 'mediaDevices' in navigator,
            geolocation_enabled: 'geolocation' in navigator,
            notifications_enabled: 'Notification' in window,
            storage_available: 'localStorage' in window
        };
    }
    
    async sendMessage(message, additionalContext = {}) {
        try {
            // Prepare message with full context
            const messageData = {
                message: message,
                user_id: this.userId,
                device_id: this.deviceId,
                device_type: this.deviceType,
                session_id: this.getSessionId(),
                capabilities: this.getDeviceCapabilities(),
                conversation_context: this.getRecentContext(),
                timestamp: new Date().toISOString(),
                ...additionalContext
            };
            
            console.log('📤 Sending message with context:', messageData);
            
            const response = await fetch(`${this.apiBase}/chat/universal`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Device-Id': this.deviceId,
                    'X-User-Id': this.userId
                },
                body: JSON.stringify(messageData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Update local conversation history
            this.addToHistory({
                user_message: message,
                buddy_response: result.response,
                timestamp: Date.now(),
                device_type: this.deviceType,
                metadata: result.metadata || {}
            });
            
            console.log('📥 Received response:', result);
            return result;
            
        } catch (error) {
            console.error('❌ Message send error:', error);
            throw error;
        }
    }
    
    getSessionId() {
        let sessionId = sessionStorage.getItem('buddy_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('buddy_session_id', sessionId);
        }
        return sessionId;
    }
    
    getRecentContext() {
        // Return last 5 messages for context
        return this.conversationHistory.slice(-5).map(item => ({
            user: item.user_message,
            buddy: item.buddy_response,
            timestamp: item.timestamp,
            device: item.device_type
        }));
    }
    
    addToHistory(conversationItem) {
        this.conversationHistory.push(conversationItem);
        
        // Keep only last 50 conversations in memory
        if (this.conversationHistory.length > 50) {
            this.conversationHistory = this.conversationHistory.slice(-50);
        }
        
        // Save to localStorage for persistence
        this.saveConversationHistory();
        
        // Broadcast to other tabs/windows
        this.broadcastToLocalTabs('conversation_update', conversationItem);
    }
    
    saveConversationHistory() {
        try {
            localStorage.setItem('buddy_conversation_history', JSON.stringify(this.conversationHistory));
        } catch (error) {
            console.warn('⚠️ Could not save conversation history:', error);
        }
    }
    
    loadConversationHistory() {
        try {
            const saved = localStorage.getItem('buddy_conversation_history');
            if (saved) {
                this.conversationHistory = JSON.parse(saved);
                console.log(`📚 Loaded ${this.conversationHistory.length} previous conversations`);
            }
        } catch (error) {
            console.warn('⚠️ Could not load conversation history:', error);
        }
    }
    
    handleWebSocketMessage(message) {
        console.log('📨 WebSocket message received:', message);
        
        switch (message.type) {
            case 'conversation_sync':
                this.handleConversationSync(message);
                break;
            case 'device_update':
                this.handleDeviceUpdate(message);
                break;
            case 'user_profile_update':
                this.handleProfileUpdate(message);
                break;
            default:
                console.log('🤷 Unknown message type:', message.type);
        }
    }
    
    handleConversationSync(message) {
        if (message.user_id === this.userId && message.device_id !== this.deviceId) {
            console.log('🔄 Syncing conversation from another device:', message.device_type);
            
            // Add to history if not already present
            const exists = this.conversationHistory.some(item => 
                item.timestamp === message.timestamp && 
                item.user_message === message.preview
            );
            
            if (!exists) {
                this.addToHistory({
                    user_message: message.preview,
                    buddy_response: message.response || 'Response from ' + message.device_type,
                    timestamp: message.timestamp,
                    device_type: message.device_type,
                    synced: true
                });
                
                // Notify UI about sync
                this.dispatchEvent('conversationSynced', message);
            }
        }
    }
    
    handleDeviceUpdate(message) {
        console.log('📱 Device update received:', message);
        this.dispatchEvent('deviceUpdate', message);
    }
    
    handleProfileUpdate(message) {
        console.log('👤 Profile update received:', message);
        this.dispatchEvent('profileUpdate', message);
    }
    
    broadcastToLocalTabs(type, data) {
        try {
            // Use localStorage event to communicate between tabs
            const message = {
                type: type,
                data: data,
                timestamp: Date.now(),
                device_id: this.deviceId
            };
            
            localStorage.setItem('buddy_tab_broadcast', JSON.stringify(message));
            localStorage.removeItem('buddy_tab_broadcast'); // Trigger event
        } catch (error) {
            console.warn('⚠️ Could not broadcast to tabs:', error);
        }
    }
    
    setupTabSync() {
        // Listen for messages from other tabs
        window.addEventListener('storage', (event) => {
            if (event.key === 'buddy_tab_broadcast' && event.newValue) {
                try {
                    const message = JSON.parse(event.newValue);
                    if (message.device_id !== this.deviceId) {
                        this.handleTabMessage(message);
                    }
                } catch (error) {
                    console.warn('⚠️ Tab sync error:', error);
                }
            }
        });
    }
    
    handleTabMessage(message) {
        console.log('📑 Tab message received:', message);
        this.dispatchEvent('tabSync', message);
    }
    
    dispatchEvent(eventName, data) {
        window.dispatchEvent(new CustomEvent(`buddy${eventName}`, {
            detail: data
        }));
    }
    
    async checkForUpdates() {
        try {
            // Polling fallback for when WebSocket isn't available
            const response = await fetch(`${this.apiBase}/sync/check?user_id=${this.userId}&device_id=${this.deviceId}`);
            if (response.ok) {
                const updates = await response.json();
                if (updates.has_updates) {
                    console.log('🔄 Updates found via polling');
                    // Handle updates
                }
            }
        } catch (error) {
            console.warn('⚠️ Update check failed:', error);
        }
    }
    
    getConnectionStatus() {
        return {
            websocket: this.isConnected,
            api_reachable: true, // Would check with a ping
            device_id: this.deviceId,
            user_id: this.userId,
            last_sync: new Date().toISOString()
        };
    }
    
    clearHistory() {
        this.conversationHistory = [];
        localStorage.removeItem('buddy_conversation_history');
        console.log('🗑️ Conversation history cleared');
    }
}

// Auto-initialize if in browser environment
if (typeof window !== 'undefined') {
    window.BuddyDeviceSync = BuddyDeviceSync;
}
