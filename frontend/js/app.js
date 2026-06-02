// 主应用逻辑

class App {
    constructor() {
        this.currentUser = null;
        this.currentConversationId = null;
        this.conversations = [];
        this.contacts = [];
        this.initialized = false;
        this.messageInput = null;
    }

    // 初始化应用
    async init() {
        console.log('Initializing app...');
        
        // 检查是否已登录
        const token = storage.getToken();
        const user = storage.getCurrentUser();

        if (!token || !user) {
            ui.showModal('loginModal');
            this.bindEvents();
            return;
        }

        this.currentUser = user;
        ui.setCurrentUser(user);

        // 隐藏登录模态框，显示主界面
        ui.hideModal('loginModal');
        ui.hideModal('registerModal');

        // 绑定事件
        if (!this.initialized) {
            this.bindEvents();
        }

        // 连接WebSocket
        this.connectWebSocket(token);

        // 加载数据
        await this.loadConversations();
        await this.loadContacts();

        // 初始化消息编辑/删除功能
        ui.initMessageActions();
        
        // 监听编辑/删除消息事件
        if (wsManager.socket) {
            wsManager.socket.on('message_edited', (data) => {
                ui.updateMessageBubble(data.messageId, { content: data.content });
            });
            wsManager.socket.on('message_revoked', (data) => {
                ui.updateMessageBubble(data.messageId, { isDeleted: true });
            });
            wsManager.socket.on('message_deleted', (data) => {
                ui.updateMessageBubble(data.messageId, { isDeleted: true });
            });
        }

        this.initialized = true;
        console.log('App initialized');
    }

    // 切换个人菜单显示
    toggleProfileMenu() {
        const menu = $('#profileMenu');
        if (!menu) return;
        menu.classList.toggle('hidden');
    }

    // 连接WebSocket
    connectWebSocket(token) {
        wsManager.connect(token);

        // 监听WebSocket事件
        wsManager.on('new_message', (data) => this.onNewMessage(data));
        wsManager.on('user_status', (data) => this.onUserStatusChange(data));
        wsManager.on('connected', () => console.log('WebSocket connected'));
        wsManager.on('disconnected', () => console.log('WebSocket disconnected'));
        wsManager.on('error', (error) => console.error('WebSocket error:', error));
    }

    // 加载会话列表
    async loadConversations() {
        try {
            const response = await api.getConversations();
            this.conversations = response.data || [];
            ui.renderConversations(this.conversations);
        } catch (error) {
            console.error('Failed to load conversations:', error);
            // 使用本地缓存
            this.conversations = storage.getConversations();
            ui.renderConversations(this.conversations);
        }
    }

    // 加载联系人列表
    async loadContacts() {
        try {
            const response = await api.getContacts();
            this.contacts = response.data || [];
            storage.setContacts(this.contacts);
        } catch (error) {
            console.error('Failed to load contacts:', error);
            this.contacts = storage.getContacts();
        }
    }

    // 选择会话
    async selectConversation(conversationId) {
        if (this.currentConversationId === conversationId) return;

        this.currentConversationId = conversationId;
        ui.currentConversationId = conversationId;

        // 更新UI
        $$('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        $(`[data-conversation-id="${conversationId}"]`).classList.add('active');

        // 获取会话详情
        const conversation = this.conversations.find(c => c.id === conversationId);
        if (conversation) {
            ui.updateChatHeader(conversation);

            // 加载消息
            await this.loadMessages(conversationId);

            // 标记为已读
            try {
                await api.markAsRead(conversationId);
                // 更新会话的未读计数
                conversation.unread = 0;
                ui.updateConversationItem(conversation);
            } catch (error) {
                console.error('Failed to mark as read:', error);
            }
        }
    }

    // 加载消息
    async loadMessages(conversationId) {
        try {
            // 先尝试从服务器加载
            const response = await api.getMessages(conversationId, 50, 0);
            const messages = response.data || [];
            
            // 保存到本地
            storage.saveMessages(conversationId, messages);
            
            ui.renderMessages(messages);
        } catch (error) {
            console.error('Failed to load messages:', error);
            
            // 使用本地缓存
            const messages = storage.getMessages(conversationId);
            ui.renderMessages(messages);
        }
    }

    // 发送消息
    async sendMessage(content) {
        if (!content.trim() || !this.currentConversationId) return;

        try {
            // 创建消息对象
            const message = {
                id: generateId(),
                senderId: this.currentUser.id,
                senderName: this.currentUser.username,
                senderAvatar: this.currentUser.avatar,
                content: content,
                timestamp: Date.now(),
                status: 'sending'
            };

            // 立即显示消息
            ui.appendMessage(message, true);
            storage.saveMessage(this.currentConversationId, message);

            // 通过WebSocket或API发送
            const sent = wsManager.sendMessage(this.currentConversationId, content);

            if (!sent) {
                // WebSocket未连接，使用REST API
                const response = await api.sendMessage(this.currentConversationId, content);
                message.id = response.data.id;
                message.status = 'sent';
                message.timestamp = response.data.timestamp;
            }

            // 清空输入框
            $('#messageInput').value = '';
            $('#messageInput').style.height = 'auto';
        } catch (error) {
            console.error('Failed to send message:', error);
            ui.showError('发送消息失败');
        }
    }

    // 接收新消息
    onNewMessage(data) {
        const { conversationId, senderId, content, timestamp, senderName, senderAvatar } = data;

        const message = {
            id: data.id || generateId(),
            senderId,
            senderName,
            senderAvatar,
            content,
            timestamp
        };

        // 保存消息
        storage.saveMessage(conversationId, message);

        // 如果是当前会话，立即显示
        if (conversationId === this.currentConversationId) {
            const isOwn = senderId === this.currentUser.id;
            ui.appendMessage(message, isOwn);
        } else {
            // 更新会话未读计数
            const conversation = this.conversations.find(c => c.id === conversationId);
            if (conversation) {
                conversation.unread = (conversation.unread || 0) + 1;
                conversation.lastMessage = content;
                conversation.lastMessageTime = timestamp;
                ui.updateConversationItem(conversation);
            }
        }
    }

    // 用户状态变化
    onUserStatusChange(data) {
        const { userId, online } = data;
        
        // 更新联系人状态
        const contact = this.contacts.find(c => c.id === userId);
        if (contact) {
            contact.online = online;
        }

        // 如果是当前会话的用户，更新标题
        const conversation = this.conversations.find(c => c.id === this.currentConversationId);
        if (conversation && conversation.type === 'private' && conversation.participantId === userId) {
            conversation.online = online;
            ui.updateChatHeader(conversation);
        }
    }

    // 删除会话
    async deleteConversation() {
        if (!this.currentConversationId) return;

        if (!confirm('确定要删除这个会话吗？')) return;

        try {
            await api.deleteConversation(this.currentConversationId);
            
            const index = this.conversations.findIndex(c => c.id === this.currentConversationId);
            if (index >= 0) {
                this.conversations.splice(index, 1);
            }

            storage.removeConversation(this.currentConversationId);
            storage.clearMessages(this.currentConversationId);

            this.currentConversationId = null;
            ui.renderConversations(this.conversations);
            ui.renderMessages([]);
            ui.closeInfoPanel();
        } catch (error) {
            console.error('Failed to delete conversation:', error);
            ui.showError('删除会话失败');
        }
    }

    // 登出
    logout() {
        storage.clearAll();
        wsManager.disconnect();
        window.location.reload();
    }

    // 处理登录
    async handleLogin(username, password) {
        try {
            const res = await api.login(username, password);
            if (res.code !== 0) throw new Error(res.message || '登录失败');

            const { token, user } = res.data;
            storage.setToken(token);
            storage.setCurrentUser(user);
            ui.hideModal('loginModal');

            // 管理员直接跳转后台
            if (user && user.username === 'admin') {
                ui.showSuccess('管理员登录，正在跳转...');
                window.location.href = '/admin';
                return;
            }

            // 普通用户：显示成功提示并刷新页面以确保聊天界面完整初始化
            ui.showSuccess('登录成功，正在进入聊天...');
            try {
                this.connectWebSocket(token);
                await this.loadConversations();
            } catch (e) {
                // 如果加载会话失败，仍然刷新以尝试完整初始化
                console.warn('会话加载失败，刷新页面以重试', e);
            }

            // 刷新页面让主界面基于已保存 token 重新初始化
            setTimeout(() => window.location.reload(), 400);
        } catch (error) {
            console.error('Login failed:', error);
            let errorMsg = '登录失败';
            
            if (error.response?.message) {
                errorMsg = error.response.message;
            } else if (error.message) {
                errorMsg = error.message;
            }
            
            ui.showError(errorMsg);
        }
    }

    // 处理注册
    async handleRegister(username, password, confirm) {
        // 验证用户名
        username = (username || '').trim();
        if (!username) {
            ui.showError('用户名不能为空');
            return;
        }
        if (username.length < 3) {
            ui.showError('用户名长度至少3个字符');
            return;
        }
        if (username.length > 20) {
            ui.showError('用户名长度不能超过20个字符');
            return;
        }
        if (!/^[a-zA-Z0-9_\u4e00-\u9fa5]+$/.test(username)) {
            ui.showError('用户名只能包含字母、数字、下划线和中文');
            return;
        }

        // 验证密码
        password = password || '';
        if (!password) {
            ui.showError('密码不能为空');
            return;
        }
        if (password.length < 6) {
            ui.showError('密码长度不能少于6位');
            return;
        }
        if (password.length > 50) {
            ui.showError('密码长度不能超过50位');
            return;
        }

        // 验证确认密码
        if (password !== confirm) {
            ui.showError('两次输入的密码不一致');
            return;
        }

        try {
            // 禁用提交按钮
            const submitBtn = $('#registerForm').querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '注册中...';
            }

            const response = await api.register(username, password);
            
            if (response.code !== 0) {
                ui.showError(response.message || '注册失败');
                return;
            }
            
            ui.showSuccess('注册成功，请登录');
            
            // 清空注册表单
            $('#registerForm').reset();
            
            // 预填用户名到登录表单
            $('#loginUsername').value = username;
            $('#loginPassword').focus();
            
            // 切换到登录界面
            ui.hideModal('registerModal');
            ui.showModal('loginModal');
        } catch (error) {
            console.error('Register failed:', error);
            
            // 解析错误信息
            let errorMsg = '注册失败';
            if (error.message.includes('用户已存在')) {
                errorMsg = '用户名已存在，请选择其他用户名';
            } else if (error.message) {
                errorMsg = error.message;
            }
            
            ui.showError(errorMsg);
        } finally {
            // 重新启用提交按钮
            const submitBtn = $('#registerForm').querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = '注册';
            }
        }
    }

    // 绑定事件
    bindEvents() {
        // 登录表单
        $('#loginForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            const username = $('#loginUsername').value.trim();
            const password = $('#loginPassword').value.trim();
            this.handleLogin(username, password);
        });

        // 注册表单
        $('#registerForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            const username = $('#registerUsername').value.trim();
            const password = $('#registerPassword').value.trim();
            const confirmPassword = $('#registerConfirm').value.trim();
            if (password !== confirmPassword) {
                ui.showError('两次输入的密码不一致');
                return;
            }
            this.handleRegister(username, password, confirmPassword);
        });

        // 切换登录/注册
        $('#switchToRegister')?.addEventListener('click', (e) => {
            e.preventDefault();
            ui.hideModal('loginModal');
            ui.showModal('registerModal');
        });

        $('#switchToLogin')?.addEventListener('click', (e) => {
            e.preventDefault();
            ui.hideModal('registerModal');
            ui.showModal('loginModal');
        });

        // 搜索框
        $('#searchInput')?.addEventListener('input', (e) => {
            this.searchConversations(e.target.value);
        });

        // 新建会话按钮
        $('#addBtn')?.addEventListener('click', () => {
            ui.showModal('newChatModal');
        });

        // 用户搜索
        $('#userSearchInput')?.addEventListener('input', (e) => {
            this.searchUsers(e.target.value);
        });

        // 消息输入框
        this.messageInput = $('#messageInput');
        this.messageInput?.addEventListener('input', () => {
            // 自动调整高度
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 100) + 'px';
        });

        this.messageInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage(this.messageInput.value);
            }
        });

        // 发送按钮
        $('#sendBtn')?.addEventListener('click', () => {
            this.sendMessage(this.messageInput.value);
        });

        // 退出登录
        $('#logoutBtn')?.addEventListener('click', () => {
            if (confirm('确定要退出登录吗？')) {
                this.logout();
            }
        });

        // 用户头像点击：打开/关闭个人菜单
        $('#userAvatar')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleProfileMenu();
        });

        // 打开个人菜单按钮
        $('#profileMenuBtn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleProfileMenu();
        });

        // 更改头像
        $('#profileChangeAvatarBtn')?.addEventListener('click', () => {
            const input = $('#avatarFileInput');
            if (!input) return;
            input.value = '';
            input.click();
        });

        $('#avatarFileInput')?.addEventListener('change', async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;

            if (!file.type.startsWith('image/')) {
                ui.showError('请选择有效的图片文件');
                return;
            }

            if (file.size > 5 * 1024 * 1024) {
                ui.showError('图片大小不能超过 5MB');
                return;
            }

            try {
                ui.showSuccess('正在上传头像...');
                const res = await api.uploadAvatar(file);
                const user = res.data;
                storage.setCurrentUser(user);
                ui.setCurrentUser(user);
                ui.showSuccess('头像已更新');
            } catch (error) {
                console.error('Avatar upload failed:', error);
                ui.showError(error.response?.message || error.message || '头像上传失败');
            }
        });

        // 退出账号
        $('#profileLogoutBtn')?.addEventListener('click', () => {
            if (confirm('确定要退出账号吗？')) {
                this.logout();
            }
        });

        // 点击页面其它区域关闭菜单
        document.addEventListener('click', () => {
            const menu = $('#profileMenu');
            if (menu && !menu.classList.contains('hidden')) {
                menu.classList.add('hidden');
            }
        });

        $('#profileMenu')?.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // 会话信息按钮
        $('#infoBtn')?.addEventListener('click', () => {
            const conversation = this.conversations.find(c => c.id === this.currentConversationId);
            if (conversation) {
                ui.openInfoPanel(conversation);
            }
        });

        // 关闭信息面板
        $('#closePanelBtn')?.addEventListener('click', () => {
            ui.closeInfoPanel();
        });

        // 文件按钮点击
        $('#fileBtn')?.addEventListener('click', () => {
            $('#fileInput').click();
        });

        // 文件输入变化
        $('#fileInput')?.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
            e.target.value = ''; // 重置输入
        });

        // 消息容器拖拽
        const messagesContainer = $('#messagesContainer');
        if (messagesContainer) {
            messagesContainer.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.stopPropagation();
                messagesContainer.style.backgroundColor = '#f9f9f9';
            });

            messagesContainer.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.stopPropagation();
                messagesContainer.style.backgroundColor = '';
            });

            messagesContainer.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                messagesContainer.style.backgroundColor = '';
                this.handleFileSelect(e.dataTransfer.files);
            });
        }

        // 消息输入框粘贴
        this.messageInput?.addEventListener('paste', (e) => {
            const items = e.clipboardData.items;
            for (let item of items) {
                if (item.kind === 'file') {
                    e.preventDefault();
                    this.handleFileSelect([item.getAsFile()]);
                    break;
                }
            }
        });
    }

    // 处理文件选择
    async handleFileSelect(files) {
        if (!files || files.length === 0 || !this.currentConversationId) return;

        for (let file of files) {
            try {
                // 检查文件大小
                const maxSize = 100 * 1024 * 1024; // 100MB
                if (file.size > maxSize) {
                    ui.showError(`文件 ${file.name} 超过大小限制 (最大100MB)`);
                    continue;
                }

                // 检查文件类型
                const isImage = file.type.startsWith('image/');
                const isAudio = file.type.startsWith('audio/');
                const isVideo = file.type.startsWith('video/');

                console.log(`上传文件: ${file.name}, 类型: ${file.type}, 大小: ${file.size}`);

                // 上传文件到服务器
                try {
                    const response = await api.uploadFile(this.currentConversationId, file);
                    
                    if (response.code === 0) {
                        // 成功上传，消息已由服务器创建
                        const message = response.data.message;
                        
                        // 解析文件信息
                        let fileInfo;
                        try {
                            fileInfo = JSON.parse(message.content);
                        } catch (e) {
                            fileInfo = {};
                        }
                        
                        // 显示上传的文件消息
                        const displayMessage = {
                            id: message.id,
                            senderId: this.currentUser.id,
                            senderName: this.currentUser.username,
                            senderAvatar: this.currentUser.avatar,
                            content: `[文件] ${fileInfo.fileName || file.name}`,
                            type: 'file',
                            timestamp: message.timestamp,
                            status: 'sent',
                            fileInfo: fileInfo
                        };
                        
                        ui.appendMessage(displayMessage, true);
                        storage.saveMessage(this.currentConversationId, displayMessage);
                        
                        // 通过WebSocket通知其他用户
                        wsManager.send('send_message', {
                            conversation_id: this.currentConversationId,
                            content: message.content,
                            type: 'file'
                        });
                    } else {
                        ui.showError(`上传失败: ${response.message}`);
                    }
                } catch (error) {
                    console.error('文件上传失败:', error);
                    ui.showError(`上传文件 ${file.name} 失败: ${error.message}`);
                }
            } catch (error) {
                console.error('文件处理失败:', error);
                ui.showError('文件处理失败');
            }
        }
    }

    // 搜索会话
    searchConversations(query) {
        if (!query.trim()) {
            ui.renderConversations(this.conversations);
            return;
        }

        const filtered = this.conversations.filter(c => 
            c.name.toLowerCase().includes(query.toLowerCase()) ||
            (c.lastMessage && c.lastMessage.toLowerCase().includes(query.toLowerCase()))
        );

        ui.renderConversations(filtered);
    }

    // 搜索用户
    async searchUsers(query) {
        if (!query.trim()) {
            ui.renderUserSearchResults([]);
            return;
        }

        try {
            const response = await api.searchUsers(query);
            const users = response.data || [];
            ui.renderUserSearchResults(users);
        } catch (error) {
            console.error('Search users failed:', error);
        }
    }

    // 添加用户为联系人并开始聊天
    async addContactAndChat(userId) {
        try {
            console.log('正在添加联系人:', userId);
            const response = await api.addContact(userId);
            console.log('添加联系人响应:', response);
            
            const { conversation } = response.data;
            if (!conversation) {
                throw new Error('响应中没有会话信息');
            }

            console.log('收到会话:', conversation);

            // 添加到会话列表
            const existingIndex = this.conversations.findIndex(c => c.id === conversation.id);
            if (existingIndex >= 0) {
                this.conversations[existingIndex] = conversation;
            } else {
                this.conversations.unshift(conversation);
            }

            storage.setConversations(this.conversations);
            ui.renderConversations(this.conversations);

            // 选择新会话
            this.selectConversation(conversation.id);

            // 隐藏模态框
            ui.hideModal('newChatModal');
        } catch (error) {
            console.error('Add contact failed:', error);
            ui.showError('添加联系人失败: ' + error.message);
        }
    }
}

// 全局应用实例
const app = new App();
window.app = app;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 确保所有依赖都已加载
    if (typeof ui === 'undefined' || typeof storage === 'undefined' || typeof api === 'undefined' || typeof wsManager === 'undefined') {
        console.error('Missing dependencies:', {
            ui: typeof ui,
            storage: typeof storage,
            api: typeof api,
            wsManager: typeof wsManager
        });
        setTimeout(() => app.init(), 100);
        return;
    }
    app.init();
});