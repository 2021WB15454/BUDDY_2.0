/**
 * BUDDY AI Assistant - JavaScript SDK
 * 
 * Easy integration library for connecting to BUDDY API
 * Supports Node.js and Browser environments
 */

class BuddyClient {
    constructor(config = {}) {
        this.baseUrl = config.baseUrl || 'http://localhost:8081';
        this.apiKey = config.apiKey || null;
        this.userId = config.userId || this.generateUserId();
        this.sessionId = config.sessionId || this.generateSessionId();
        this.timeout = config.timeout || 30000;
        this.onMessage = config.onMessage || null;
        this.onError = config.onError || null;
    }

    /**
     * Send a message to BUDDY and get response
     * @param {string} message - The message to send
     * @param {Object} options - Additional options
     * @returns {Promise<Object>} - BUDDY's response
     */
    async chat(message, options = {}) {
        try {
            const payload = {
                message: message,
                user_id: options.userId || this.userId,
                session_id: options.sessionId || this.sessionId,
                context: options.context || {},
                metadata: {
                    timestamp: new Date().toISOString(),
                    client: 'buddy-js-sdk',
                    ...options.metadata
                }
            };

            const response = await this.makeRequest('/chat', {
                method: 'POST',
                body: JSON.stringify(payload),
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders()
                }
            });

            if (this.onMessage) {
                this.onMessage(response);
            }

            return response;
        } catch (error) {
            if (this.onError) {
                this.onError(error);
            }
            throw error;
        }
    }

    /**
     * Get available skills
     * @returns {Promise<Array>} - List of available skills
     */
    async getSkills() {
        return await this.makeRequest('/skills');
    }

    /**
     * Check BUDDY health status
     * @returns {Promise<Object>} - Health status
     */
    async getHealth() {
        return await this.makeRequest('/health');
    }

    /**
     * Get conversation history
     * @param {Object} options - Query options
     * @returns {Promise<Array>} - Conversation history
     */
    async getHistory(options = {}) {
        const params = new URLSearchParams({
            user_id: options.userId || this.userId,
            session_id: options.sessionId || this.sessionId,
            limit: options.limit || 50,
            offset: options.offset || 0
        });

        return await this.makeRequest(`/conversations?${params}`);
    }

    /**
     * Execute a specific skill
     * @param {string} skillName - Name of the skill to execute
     * @param {Object} params - Skill parameters
     * @returns {Promise<Object>} - Skill execution result
     */
    async executeSkill(skillName, params = {}) {
        const payload = {
            skill: skillName,
            parameters: params,
            user_id: this.userId,
            session_id: this.sessionId
        };

        return await this.makeRequest('/skills/execute', {
            method: 'POST',
            body: JSON.stringify(payload),
            headers: {
                'Content-Type': 'application/json',
                ...this.getAuthHeaders()
            }
        });
    }

    /**
     * Start a streaming conversation
     * @param {string} message - Initial message
     * @param {Function} onChunk - Callback for each response chunk
     * @returns {Promise<void>}
     */
    async streamChat(message, onChunk) {
        const payload = {
            message: message,
            user_id: this.userId,
            session_id: this.sessionId,
            stream: true
        };

        const response = await fetch(`${this.baseUrl}/chat/stream`, {
            method: 'POST',
            body: JSON.stringify(payload),
            headers: {
                'Content-Type': 'application/json',
                ...this.getAuthHeaders()
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n').filter(line => line.trim());

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        onChunk(data);
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    /**
     * Make HTTP request to BUDDY API
     * @private
     */
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...this.getAuthHeaders()
            },
            ...options
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    /**
     * Get authentication headers
     * @private
     */
    getAuthHeaders() {
        const headers = {};
        if (this.apiKey) {
            headers['Authorization'] = `Bearer ${this.apiKey}`;
        }
        return headers;
    }

    /**
     * Generate unique user ID
     * @private
     */
    generateUserId() {
        return 'user_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Generate unique session ID
     * @private
     */
    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9);
    }
}

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
    // Node.js environment
    module.exports = BuddyClient;
} else if (typeof window !== 'undefined') {
    // Browser environment
    window.BuddyClient = BuddyClient;
}
