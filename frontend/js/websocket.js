// WebSocket 连接管理使用Socket.IO

class WebSocketManager {
    constructor(url = 'http://localhost:5000') {
        this.url = url;
        this.socket = null;
        this.connected = false;
        this.reconnecting = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.messageHandlers = {};
        this.eventHandlers = {};
    }

    // 连接到Socket.IO
    connect(token) {
        if (this.socket) return;

        try {
            // 使用Socket.IO客户端连接
            this.socket = io(this.url, {
                auth: {
                    token: token
                },
                reconnection: true,
                reconnectionDelay: 3000,
                reconnectionDelayMax: 10000,
                reconnectionAttempts: this.maxReconnectAttempts
            });
            
            this.socket.on('connect', () => this.onOpen());
            this.socket.on('disconnect', () => this.onClose());
            this.socket.on('error', (error) => this.onError(error));
            this.socket.on('message', (data) => this.onMessage(data));
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.reconnect(token);
        }
    }

    // 连接成功
    onOpen() {
        console.log('WebSocket connected');
        this.connected = true;
        this.reconnecting = false;
        this.reconnectAttempts = 0;
        
        // 启动心跳
        this.startHeartbeat();
        
        // 触发连接事件
        this.emit('connected');
    }

    // 接收消息
    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received message:', data);
            
            // 根据事件类型分发消息
            if (data.type === 'message') {
                this.emit('new_message', data.data);
            } else if (data.type === 'status') {
                this.emit('user_status', data.data);
            } else if (data.type === 'notification') {
                this.emit('notification', data.data);
            } else if (data.type === 'pong') {
                // 心跳响应
            }
            
            // 触发通用消息事件
            this.emit(`${data.type}:${data.event}`, data.data);
        } catch (error) {
            console.error('Message parsing error:', error);
        }
    }

    // 错误处理
    onError(error) {
        console.error('WebSocket error:', error);
        this.emit('error', error);
    }

    // 连接关闭
    onClose() {
        console.log('WebSocket disconnected');
        this.connected = false;
        this.stopHeartbeat();
        
        this.emit('disconnected');
        
        // 尝试重连
        if (!this.reconnecting && this.reconnectAttempts < this.maxReconnectAttempts) {
            const token = storage.getToken();
            if (token) {
                this.reconnect(token);
            }
        }
    }

    // 重新连接
    reconnect(token) {
        if (this.reconnecting) return;
        
        this.reconnecting = true;
        this.reconnectAttempts++;
        
        const delay = this.reconnectDelay * this.reconnectAttempts;
        console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.ws = null;
            this.connect(token);
        }, delay);
    }

    // 发送消息
    send(data) {
        if (!this.connected || !this.ws) {
            console.error('WebSocket not connected');
            return false;
        }

        try {
            this.ws.send(JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('Send error:', error);
            return false;
        }
    }

    // 发送文本消息
    sendMessage(conversationId, content) {
        return this.send({
            type: 'message',
            event: 'send_message',
            data: {
                conversation_id: conversationId,
                content,
                timestamp: Date.now()
            }
        });
    }

    // 心跳包
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.connected) {
                this.send({
                    type: 'ping',
                    timestamp: Date.now()
                });
            }
        }, 30000); // 每30秒发送一次
    }

    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    // 事件监听
    on(event, callback) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(callback);
    }

    // 事件移除
    off(event, callback) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event] = this.eventHandlers[event].filter(cb => cb !== callback);
        }
    }

    // 事件触发
    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Event handler error for ${event}:`, error);
                }
            });
        }
    }

    // 断开连接
    disconnect() {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.connected = false;
        this.reconnecting = false;
    }
}

// 全局WebSocket管理实例
const wsManager = new WebSocketManager();