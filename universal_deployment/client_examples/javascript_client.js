// BUDDY JavaScript/TypeScript Client SDK
// Universal client for web, mobile apps, and Node.js

class BuddyClient {
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || 'http://localhost:8000';
        this.deviceId = options.deviceId || this.generateUUID();
        this.deviceName = options.deviceName || 'Web Client';
        this.deviceType = options.deviceType || 'web';
        this.platform = options.platform || 'javascript';
        this.userId = null;
        this.ws = null;
        this.isConnected = false;
        this.messageHandlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    async connect() {
        try {
            // Register device
            const response = await fetch(`${this.baseUrl}/api/v1/devices/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device_id: this.deviceId,
                    device_name: this.deviceName,
                    device_type: this.deviceType,
                    platform: this.platform,
                    metadata: {
                        sdk_version: '1.0.0',
                        connected_at: new Date().toISOString(),
                        user_agent: navigator.userAgent || 'Node.js'
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`Registration failed: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Device registered successfully:', this.deviceId);

            // Connect WebSocket
            await this.connectWebSocket();

            this.isConnected = true;
            return true;

        } catch (error) {
            console.error('Failed to connect to BUDDY Core:', error);
            return false;
        }
    }

    async connectWebSocket() {
        try {
            // For demo using default user ID
            const userId = '550e8400-e29b-41d4-a716-446655440000';
            const wsUrl = `${this.baseUrl.replace('http', 'ws')}/ws/${userId}`;

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            this.ws.onclose = () => {
                console.log('WebSocket connection closed');
                this.isConnected = false;
                this.attemptReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

        } catch (error) {
            console.error('WebSocket connection failed:', error);
        }
    }

    async attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            
            console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    handleMessage(data) {
        const messageType = data.type;
        
        if (this.messageHandlers.has(messageType)) {
            this.messageHandlers.get(messageType)(data);
        } else {
            this.handleDefaultMessage(data);
        }
    }

    handleDefaultMessage(data) {
        console.log('Received message:', data);
    }

    onMessage(messageType, handler) {
        this.messageHandlers.set(messageType, handler);
    }

    async sendMessage(text, context = {}) {
        try {
            const response = await fetch(`${this.baseUrl}/api/v1/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    device_id: this.deviceId,
                    session_id: this.generateUUID(),
                    context: context
                })
            });

            if (!response.ok) {
                throw new Error(`Chat request failed: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            console.error('Failed to send message:', error);
            throw error;
        }
    }

    async createTask(options = {}) {
        try {
            const taskData = {
                title: options.title,
                device_id: this.deviceId,
                priority: options.priority || 'medium'
            };

            if (options.description) taskData.description = options.description;
            if (options.dueDate) taskData.due_date = options.dueDate;
            if (options.category) taskData.category = options.category;

            const response = await fetch(`${this.baseUrl}/api/v1/tasks`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(taskData)
            });

            if (!response.ok) {
                throw new Error(`Task creation failed: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            console.error('Failed to create task:', error);
            throw error;
        }
    }

    async syncData(options = {}) {
        try {
            const syncData = {
                device_id: this.deviceId,
                sync_types: options.syncTypes || ['conversations', 'tasks', 'preferences']
            };

            if (options.lastSync) {
                syncData.last_sync = options.lastSync;
            }

            const response = await fetch(`${this.baseUrl}/api/v1/sync`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(syncData)
            });

            if (!response.ok) {
                throw new Error(`Sync failed: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            console.error('Failed to sync data:', error);
            throw error;
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
        this.isConnected = false;
        console.log('Disconnected from BUDDY Core');
    }
}

// Example usage for web applications
async function webExample() {
    const client = new BuddyClient({
        deviceName: 'My Web App',
        deviceType: 'web',
        platform: 'javascript'
    });

    // Set up message handlers
    client.onMessage('new_message', (data) => {
        console.log('New message from another device:', data);
        // Update UI with new message
    });

    client.onMessage('task_created', (data) => {
        console.log('Task created on another device:', data);
        // Update task list in UI
    });

    try {
        if (await client.connect()) {
            console.log('Connected to BUDDY Core!');

            // Send a message
            const response = await client.sendMessage(
                'Hello BUDDY! This is from web client.',
                { app: 'web-example', version: '1.0' }
            );
            console.log('BUDDY Response:', response);

            // Create a task
            const task = await client.createTask({
                title: 'Test task from web',
                description: 'This task was created via JavaScript SDK',
                priority: 'high'
            });
            console.log('Task created:', task);

            // Sync data
            const syncResult = await client.syncData();
            console.log('Sync completed:', syncResult);

        }
    } catch (error) {
        console.error('Example error:', error);
    }
}

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
    // Node.js
    module.exports = BuddyClient;
} else if (typeof window !== 'undefined') {
    // Browser
    window.BuddyClient = BuddyClient;
}

// React Hook for easy integration
function useBuddy(options = {}) {
    const [client, setClient] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [messages, setMessages] = useState([]);

    useEffect(() => {
        const buddyClient = new BuddyClient(options);
        
        buddyClient.onMessage('new_message', (data) => {
            setMessages(prev => [...prev, data]);
        });

        buddyClient.connect().then(connected => {
            setIsConnected(connected);
            setClient(buddyClient);
        });

        return () => {
            buddyClient.disconnect();
        };
    }, []);

    const sendMessage = async (text, context) => {
        if (client && isConnected) {
            return await client.sendMessage(text, context);
        }
        throw new Error('Not connected to BUDDY Core');
    };

    const createTask = async (options) => {
        if (client && isConnected) {
            return await client.createTask(options);
        }
        throw new Error('Not connected to BUDDY Core');
    };

    return {
        client,
        isConnected,
        messages,
        sendMessage,
        createTask
    };
}
