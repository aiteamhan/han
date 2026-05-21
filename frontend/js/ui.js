// UI 更新管理

class UIManager {
    constructor() {
        this.currentConversationId = null;
        this.currentUser = null;
    }

    // 渲染会话列表
    renderConversations(conversations) {
        const container = $('#conversationsList');
        container.innerHTML = '';

        conversations.forEach(conv => {
            const item = this.createConversationItem(conv);
            container.appendChild(item);
        });
    }

    // 创建会话项
    createConversationItem(conversation) {
        const item = document.createElement('div');
        item.className = 'conversation-item';
        item.dataset.conversationId = conversation.id;

        if (this.currentConversationId === conversation.id) {
            item.classList.add('active');
        }

        // 获取头像
        const avatar = conversation.avatar || 'https://via.placeholder.com/48';

        // 创建内容
        const contentHTML = `
            <img src="${avatar}" alt="" class="conversation-avatar">
            <div class="conversation-content">
                <div class="conversation-header">
                    <span class="conversation-name">${this.escapeHtml(conversation.name)}</span>
                    <span class="conversation-time">${formatTime(conversation.lastMessageTime || Date.now())}</span>
                </div>
                <div class="conversation-preview">${this.escapeHtml(conversation.lastMessage || '暂无消息')}</div>
            </div>
            ${conversation.unread > 0 ? `<div class="unread-badge">${conversation.unread}</div>` : ''}
        `;

        item.innerHTML = contentHTML;
        
        item.addEventListener('click', () => {
            window.app.selectConversation(conversation.id);
        });

        return item;
    }

    // 更新会话列表中的一个项目
    updateConversationItem(conversation) {
        const item = $(`[data-conversation-id="${conversation.id}"]`);
        if (item) {
            const newItem = this.createConversationItem(conversation);
            item.replaceWith(newItem);
        }
    }

    // 渲染消息列表
    renderMessages(messages) {
        const container = $('#messagesContainer');
        container.innerHTML = '';

        if (messages.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无消息</p></div>';
            return;
        }

        messages.forEach((msg, index) => {
            const isOwn = msg.senderId === this.currentUser.id;
            const bubble = this.createMessageBubble(msg, isOwn);
            container.appendChild(bubble);
        });

        // 滚动到底部
        container.scrollTop = container.scrollHeight;
    }

    // 创建消息气泡
    createMessageBubble(message, isOwn) {
        const group = document.createElement('div');
        group.className = `message-group ${isOwn ? 'self' : 'other'}`;
        group.dataset.messageId = message.id;
        group.style.position = 'relative';

        const avatar = message.senderAvatar || 'https://via.placeholder.com/36';

        let html = `<img src="${avatar}" alt="" class="message-avatar">`;
        html += `<div style="display: flex; flex-direction: column; align-items: ${isOwn ? 'flex-end' : 'flex-start'}; position: relative; width: 100%;">
                    <div class="message-bubble ${isOwn ? 'self' : 'other'}" style="position: relative;">
                        ${this.escapeHtml(message.content)}
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div class="message-time">${formatTime(message.timestamp)}</div>
                        ${isOwn && message.status === 'read' ? '<span class="message-read-status">（已读）</span>' : ''}
                    </div>`;
        
        // 自己的消息显示编辑/撤回菜单
        if (isOwn) {
            html += `<div class="message-actions" style="display: none;">
                        <button data-action="edit" title="编辑">编辑</button>
                        <button data-action="revoke" title="撤回">撤回</button>
                    </div>`;
        }
        
        html += `</div>`;

        group.innerHTML = html;

        // 为自己的消息添加右键菜单和点击处理
        if (isOwn) {
            const bubble = group.querySelector('.message-bubble');
            bubble.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                const menu = group.querySelector('.message-actions');
                menu.style.display = menu.style.display === 'none' ? 'flex' : 'none';
            });

            // 菜单按钮事件
            group.querySelectorAll('.message-actions button').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const action = e.target.dataset.action;
                    if (action === 'edit') {
                        console.log('编辑消息:', message.id);
                        // TODO: 实现消息编辑功能
                    } else if (action === 'revoke') {
                        if (confirm('确定要撤回这条消息吗？')) {
                            console.log('撤回消息:', message.id);
                            // TODO: 实现消息撤回功能
                        }
                    }
                    group.querySelector('.message-actions').style.display = 'none';
                });
            });

            // 点击消息外部隐藏菜单
            document.addEventListener('click', (e) => {
                if (!group.contains(e.target)) {
                    group.querySelector('.message-actions').style.display = 'none';
                }
            });
        }

        return group;
    }

    // 添加消息到列表
    appendMessage(message, isOwn = false) {
        const container = $('#messagesContainer');
        
        // 如果是空状态，清空
        if (container.querySelector('.empty-state')) {
            container.innerHTML = '';
        }

        const bubble = this.createMessageBubble(message, isOwn);
        container.appendChild(bubble);
        container.scrollTop = container.scrollHeight;
    }

    // 更新聊天标题
    updateChatHeader(conversation) {
        $('#chatTitle').textContent = conversation.name;
        
        let subtitle = '';
        if (conversation.type === 'private') {
            subtitle = conversation.online ? '在线' : '离线';
        } else {
            subtitle = `${conversation.memberCount}个成员`;
        }
        $('#chatSubtitle').textContent = subtitle;
    }

    // 显示错误消息
    showError(message) {
        alert(`错误：${message}`);
    }

    // 显示成功消息
    showSuccess(message) {
        console.log('Success:', message);
        // 可以添加toast通知
    }

    // 隐藏模态框
    hideModal(modalId) {
        const modal = $(`#${modalId}`);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // 显示模态框
    showModal(modalId) {
        const modal = $(`#${modalId}`);
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    // 打开信息面板
    openInfoPanel(conversation) {
        const panel = $('#infoPanel');
        panel.classList.add('visible');

        const content = $('#panelContent');
        content.innerHTML = this.generatePanelContent(conversation);
    }

    // 生成面板内容
    generatePanelContent(conversation) {
        let html = '';

        if (conversation.type === 'group') {
            html += `
                <div class="panel-section">
                    <div class="panel-section-title">群成员 (${conversation.members.length})</div>
                    <div class="panel-members">
                        ${conversation.members.map(member => `
                            <div class="member-item">
                                <img src="${member.avatar}" alt="" class="member-avatar">
                                <div class="member-name">${this.escapeHtml(member.name)}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        html += `
            <div class="panel-section">
                <button class="btn-primary" onclick="app.deleteConversation()">删除会话</button>
            </div>
        `;

        return html;
    }

    // 关闭信息面板
    closeInfoPanel() {
        const panel = $('#infoPanel');
        panel.classList.remove('visible');
    }

    // 渲染用户搜索结果
    renderUserSearchResults(users) {
        const container = $('#userSearchResults');
        if (!container) return;
        
        container.innerHTML = '';

        if (!users || users.length === 0) {
            container.innerHTML = '<p style="text-align: center; padding: 20px; color: #999;">未找到用户</p>';
            return;
        }

        users.forEach(user => {
            const userItem = document.createElement('div');
            userItem.className = 'user-search-item';
            userItem.style.cssText = 'padding: 10px; display: flex; align-items: center; cursor: pointer; border-bottom: 1px solid #f0f0f0; hover: background-color: #f5f5f5;';
            
            userItem.innerHTML = `
                <img src="${user.avatar || 'https://via.placeholder.com/40'}" alt="" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px;">
                <div style="flex: 1;">
                    <div style="font-weight: 500;">${this.escapeHtml(user.username)}</div>
                    <div style="font-size: 12px; color: #999;">${this.escapeHtml(user.nickname || user.username)}</div>
                </div>
            `;
            
            // 确保点击时能调用全局 app 的方法
            userItem.dataset.userId = user.id;
            userItem.onclick = async () => {
                try {
                    if (window.app && typeof window.app.addContactAndChat === 'function') {
                        // 优先使用 app 中的方法（可能包含额外行为）
                        await window.app.addContactAndChat(user.id);
                        return;
                    }
                } catch (err) {
                    console.error('调用 app.addContactAndChat 失败，尝试后备逻辑：', err);
                }

                // 后备：直接使用 API 添加联系人并更新会话列表
                try {
                    const resp = await api.addContact(user.id);
                    const conversation = resp.data && resp.data.conversation;
                    if (conversation) {
                        const conversations = storage.getConversations() || [];
                        const existingIndex = conversations.findIndex(c => c.id === conversation.id);
                        if (existingIndex >= 0) conversations[existingIndex] = conversation;
                        else conversations.unshift(conversation);
                        storage.setConversations(conversations);
                        ui.renderConversations(conversations);
                        // 选择新会话
                        if (window.app && typeof window.app.selectConversation === 'function') {
                            window.app.selectConversation(conversation.id);
                        }
                        ui.hideModal('newChatModal');
                    } else {
                        ui.showError('未能创建会话');
                    }
                } catch (err) {
                    console.error('后备添加联系人失败:', err);
                    ui.showError('添加联系人失败');
                }
            };
            
            container.appendChild(userItem);
        });
    }

    // HTML转义（防止XSS）
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 设置当前用户
    setCurrentUser(user) {
        this.currentUser = user;
        const avatar = $('#userAvatar');
        if (avatar) {
            avatar.src = user.avatar || 'https://via.placeholder.com/36';
        }
    }
}

// 全局UI管理实例
const ui = new UIManager();