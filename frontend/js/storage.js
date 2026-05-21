// LocalStorage 管理模块

class StorageManager {
    constructor() {
        this.prefix = 'wechat_';
    }

    // 获取当前用户
    getCurrentUser() {
        const user = this.get('current_user');
        return user || null;
    }

    // 保存当前用户
    setCurrentUser(user) {
        this.set('current_user', user);
    }

    // 获取所有会话
    getConversations() {
        const conversations = this.get('conversations');
        return conversations || [];
    }

    // 保存会话列表
    setConversations(conversations) {
        this.set('conversations', conversations);
    }

    // 添加或更新会话
    saveConversation(conversation) {
        let conversations = this.getConversations();
        const index = conversations.findIndex(c => c.id === conversation.id);
        
        if (index >= 0) {
            conversations[index] = { ...conversations[index], ...conversation };
        } else {
            conversations.push(conversation);
        }
        
        this.setConversations(conversations);
    }

    // 删除会话
    removeConversation(conversationId) {
        let conversations = this.getConversations();
        conversations = conversations.filter(c => c.id !== conversationId);
        this.setConversations(conversations);
    }

    // 获取特定会话的消息
    getMessages(conversationId) {
        const messages = this.get(`messages_${conversationId}`);
        return messages || [];
    }

    // 保存消息
    saveMessage(conversationId, message) {
        let messages = this.getMessages(conversationId);
        messages.push(message);
        // 只保留最后1000条消息
        if (messages.length > 1000) {
            messages = messages.slice(-1000);
        }
        this.set(`messages_${conversationId}`, messages);
    }

    // 批量保存消息
    saveMessages(conversationId, messages) {
        let existingMessages = this.getMessages(conversationId);
        existingMessages = existingMessages.concat(messages);
        if (existingMessages.length > 1000) {
            existingMessages = existingMessages.slice(-1000);
        }
        this.set(`messages_${conversationId}`, existingMessages);
    }

    // 清空会话消息
    clearMessages(conversationId) {
        this.remove(`messages_${conversationId}`);
    }

    // 获取联系人列表
    getContacts() {
        const contacts = this.get('contacts');
        return contacts || [];
    }

    // 保存联系人列表
    setContacts(contacts) {
        this.set('contacts', contacts);
    }

    // 添加联系人
    addContact(contact) {
        let contacts = this.getContacts();
        const exists = contacts.find(c => c.id === contact.id);
        if (!exists) {
            contacts.push(contact);
            this.setContacts(contacts);
        }
    }

    // 获取用户信息
    getUser(userId) {
        const users = this.get('users') || {};
        return users[userId] || null;
    }

    // 保存用户信息
    saveUser(user) {
        let users = this.get('users') || {};
        users[user.id] = user;
        this.set('users', users);
    }

    // 获取认证令牌
    getToken() {
        return this.get('auth_token');
    }

    // 保存认证令牌
    setToken(token) {
        this.set('auth_token', token);
    }

    // 清除所有数据（登出）
    clearAll() {
        localStorage.clear();
    }

    // 内部方法：保存
    set(key, value) {
        try {
            localStorage.setItem(this.prefix + key, JSON.stringify(value));
        } catch (e) {
            console.error('Storage error:', e);
        }
    }

    // 内部方法：获取
    get(key) {
        try {
            const item = localStorage.getItem(this.prefix + key);
            return item ? JSON.parse(item) : null;
        } catch (e) {
            console.error('Storage error:', e);
            return null;
        }
    }

    // 内部方法：删除
    remove(key) {
        try {
            localStorage.removeItem(this.prefix + key);
        } catch (e) {
            console.error('Storage error:', e);
        }
    }
}

// 全局存储管理实例
const storage = new StorageManager();