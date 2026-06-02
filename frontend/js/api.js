// API 调用封装

class ApiClient {
    constructor(baseURL = '') {
        // 使用相对路径作为默认 baseURL，避免 origin 不一致导致的 CORS 问题
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

            // 如果返回内容不是 JSON（例如 500 页面 HTML），读取为 text 并抛出可读错误
            const contentType = response.headers.get('content-type') || '';
            let result = null;

            if (contentType.includes('application/json')) {
                try {
                    result = await response.json();
                } catch (err) {
                    // JSON 解析失败，尝试读取文本用于错误提示
                    const text = await response.text();
                    const error = new Error(text || `HTTP ${response.status}`);
                    error.code = response.status;
                    throw error;
                }
            } else {
                const text = await response.text();
                const error = new Error(text || `HTTP ${response.status}`);
                error.code = response.status;
                throw error;
            }

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

    uploadAvatar(file) {
        const formData = new FormData();
        formData.append('avatar', file);

        const token = storage.getToken();
        const options = {
            method: 'POST',
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            body: formData
        };

        return fetch(`${this.baseURL}/api/users/avatar`, options)
            .then(async response => {
                const result = await response.json();
                if (!response.ok) {
                    const error = new Error(result.message || `HTTP ${response.status}`);
                    error.code = result.status || response.status;
                    error.response = result;
                    throw error;
                }
                return result;
            });
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

    editMessage(messageId, content) {
        return this.request('PUT', `/api/messages/${messageId}`, { content });
    }

    uploadFile(conversationId, file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conversation_id', conversationId);

        const token = storage.getToken();
        const options = {
            method: 'POST',
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            body: formData
        };

        try {
            return fetch(`${this.baseURL}/api/files/upload`, options)
                .then(response => {
                    if (!response.ok) {
                        const error = new Error(`HTTP ${response.status}`);
                        error.code = response.status;
                        throw error;
                    }
                    return response.json();
                });
        } catch (error) {
            console.error('Upload Error:', error);
            throw error;
        }
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
window.api = api;