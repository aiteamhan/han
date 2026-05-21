// API 调用封装

class ApiClient {
    constructor(baseURL = 'http://localhost:5000') {
        this.baseURL = baseURL;
        this.timeout = 10000;
    }

    // 设置基础URL
    setBaseURL(url) {
        this.baseURL = url;
    }

    // 获取认证头
    getAuthHeaders() {
        const token = storage.getToken();
        return {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        };
    }

    // 发送请求
    async request(method, endpoint, data = null) {
        const url = `${this.baseURL}${endpoint}`;
        const options = {
            method,
            headers: this.getAuthHeaders(),
            timeout: this.timeout
        };

        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            const result = await response.json();

            if (!response.ok) {
                const error = new Error(result.message || `HTTP ${response.status}`);
                error.code = result.code || response.status;
                error.response = result;
                throw error;
            }

            return result;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // ============ 用户相关 ============
    register(username, password) {
        return this.request('POST', '/api/auth/register', { username, password });
    }

    login(username, password) {
        return this.request('POST', '/api/auth/login', { username, password });
    }

    getUserInfo() {
        return this.request('GET', '/api/users/me');
    }

    updateUserInfo(data) {
        return this.request('PUT', '/api/users/me', data);
    }

    // ============ 会话相关 ============
    getConversations() {
        return this.request('GET', '/api/conversations');
    }

    getConversation(conversationId) {
        return this.request('GET', `/api/conversations/${conversationId}`);
    }

    createConversation(type, participants, name = null) {
        return this.request('POST', '/api/conversations', {
            type, // 'private' or 'group'
            participants,
            name
        });
    }

    deleteConversation(conversationId) {
        return this.request('DELETE', `/api/conversations/${conversationId}`);
    }

    // ============ 消息相关 ============
    getMessages(conversationId, limit = 50, offset = 0) {
        return this.request('GET', `/api/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`);
    }

    sendMessage(conversationId, content, type = 'text') {
        return this.request('POST', `/api/conversations/${conversationId}/messages`, {
            content,
            type
        });
    }

    markAsRead(conversationId) {
        return this.request('POST', `/api/conversations/${conversationId}/mark-read`);
    }

    revokeMessage(messageId) {
        return this.request('DELETE', `/api/messages/${messageId}`);
    }

    // ============ 联系人相关 ============
    getContacts() {
        return this.request('GET', '/api/contacts');
    }

    searchUsers(query) {
        return this.request('GET', `/api/users/search?q=${encodeURIComponent(query)}`);
    }

    addContact(userId) {
        return this.request('POST', '/api/contacts', { user_id: userId });
    }

    removeContact(userId) {
        return this.request('DELETE', `/api/contacts/${userId}`);
    }

    // ============ 群聊相关 ============
    createGroup(name, members) {
        return this.request('POST', '/api/groups', { name, members });
    }

    addGroupMember(groupId, userId) {
        return this.request('POST', `/api/groups/${groupId}/members`, { user_id: userId });
    }

    removeGroupMember(groupId, userId) {
        return this.request('DELETE', `/api/groups/${groupId}/members/${userId}`);
    }

    updateGroupInfo(groupId, data) {
        return this.request('PUT', `/api/groups/${groupId}`, data);
    }

    getGroupMembers(groupId) {
        return this.request('GET', `/api/groups/${groupId}/members`);
    }
}

// 全局API客户端实例
const api = new ApiClient();