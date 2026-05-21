// ============ 管理后台主要逻辑 ============

const AdminPanel = {
    adminUsername: 'admin',
    adminPassword: 'qwerty',
    currentUser: null,
    allUsers: [],

    init() {
        this.checkLogin();
        this.bindEvents();
    },

    checkLogin() {
        const stored = localStorage.getItem('admin_user');
        if (stored) {
            this.currentUser = JSON.parse(stored);
            this.showPanel();
            this.loadDashboard();
        } else {
            this.showLogin();
        }
    },

    bindEvents() {
        // 登录表单
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // 导航链接
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchPage(link.dataset.page);
            });
        });

        // 退出登录
        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });

        // 侧边栏切换（移动设备）
        document.getElementById('sidebarToggle').addEventListener('click', () => {
            document.querySelector('.sidebar').classList.toggle('active');
        });

        // 用户搜索
        document.getElementById('userSearch').addEventListener('input', (e) => {
            this.filterUsers(e.target.value);
        });
    },

    handleLogin() {
        const username = document.getElementById('adminUsername').value.trim();
        const password = document.getElementById('adminPassword').value.trim();
        const errorEl = document.getElementById('loginError');

        if (!username || !password) {
            errorEl.textContent = '用户名和密码不能为空';
            return;
        }

        if (username === this.adminUsername && password === this.adminPassword) {
            this.currentUser = {
                username: username,
                loginTime: new Date().toISOString()
            };
            localStorage.setItem('admin_user', JSON.stringify(this.currentUser));
            errorEl.textContent = '';
            this.showPanel();
            this.loadDashboard();
        } else {
            errorEl.textContent = '用户名或密码错误';
        }
    },

    showLogin() {
        document.getElementById('loginModal').classList.remove('hidden');
        document.getElementById('adminPanel').classList.add('hidden');
    },

    showPanel() {
        document.getElementById('loginModal').classList.add('hidden');
        document.getElementById('adminPanel').classList.remove('hidden');
        document.getElementById('adminName').textContent = this.currentUser.username;
    },

    logout() {
        localStorage.removeItem('admin_user');
        this.currentUser = null;
        document.getElementById('loginForm').reset();
        document.getElementById('loginError').textContent = '';
        this.showLogin();
    },

    switchPage(page) {
        // 更新导航链接活动状态
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-page="${page}"]`).classList.add('active');

        // 隐藏所有页面
        document.querySelectorAll('.page-section').forEach(section => {
            section.classList.remove('active');
        });

        // 显示对应页面
        const pageMap = {
            'dashboard': 'dashboardPage',
            'messages': 'messagesPage',
            'settings': 'settingsPage',
            'users': 'usersPage',
            'reports': 'reportsPage'
        };

        const pageId = pageMap[page];
        if (pageId) {
            document.getElementById(pageId).classList.add('active');
            document.getElementById('pageTitle').textContent = this.getPageTitle(page);
        }

        // 如果切换到用户页面，加载用户数据
        if (page === 'users') {
            this.loadUsers();
        }

        // 关闭移动端侧边栏
        const sidebar = document.querySelector('.sidebar');
        if (sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
        }
    },

    getPageTitle(page) {
        const titles = {
            'dashboard': '首页',
            'messages': '消息',
            'settings': '设置',
            'users': '用户资料',
            'reports': '举报信息'
        };
        return titles[page] || '首页';
    },

    async loadDashboard() {
        try {
            // 加载统计数据
            const response = await fetch('/api/admin/stats', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('wechat_auth_token') || ''}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                // 处理API响应格式 {code: 0, data: {...}}
                const stats = data.data || data;
                document.getElementById('totalUsers').textContent = stats.totalUsers || 0;
                document.getElementById('onlineUsers').textContent = stats.onlineUsers || 0;
                document.getElementById('totalConversations').textContent = stats.totalConversations || 0;
                document.getElementById('totalMessages').textContent = stats.totalMessages || 0;
            } else {
                // 如果API不可用，显示默认值
                this.loadDashboardOffline();
            }
        } catch (error) {
            console.log('无法连接到API，使用离线模式');
            this.loadDashboardOffline();
        }
    },

    loadDashboardOffline() {
        // 从本地数据库查询（需要后端支持）
        document.getElementById('totalUsers').textContent = '正在加载...';
        document.getElementById('onlineUsers').textContent = '---';
        document.getElementById('totalConversations').textContent = '---';
        document.getElementById('totalMessages').textContent = '---';
    },

    async loadUsers() {
        try {
            // 首先尝试从API加载
            const response = await fetch('/api/admin/users', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('wechat_auth_token') || ''}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                // 处理API响应格式 {code: 0, data: {users: [...], total: 5}}
                const userData = data.data || data;
                this.allUsers = userData.users || [];
                this.renderUsers(this.allUsers);
            } else {
                // 如果API不可用，尝试从localStorage加载缓存数据
                throw new Error('API not available');
            }
        } catch (error) {
            console.log('从API加载失败，尝试本地数据');
            // 这里可以从localStorage或其他本地存储加载缓存的用户数据
            this.allUsers = this.getCachedUsers();
            this.renderUsers(this.allUsers);
        }
    },

    renderUsers(users) {
        const tbody = document.getElementById('usersTableBody');
        
        if (!users || users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">暂无用户数据</td></tr>';
            document.getElementById('userCount').textContent = '0';
            document.getElementById('onlineCount').textContent = '0';
            return;
        }

        const onlineCount = users.filter(u => u.online).length;
        document.getElementById('userCount').textContent = users.length;
        document.getElementById('onlineCount').textContent = onlineCount;

        tbody.innerHTML = users.map(user => `
            <tr>
                <td>${this.escapeHtml(user.username)}</td>
                <td><code style="font-size: 12px; color: #999;">${user.id.substring(0, 8)}...</code></td>
                <td>${this.escapeHtml(user.nickname || '(未设置)')}</td>
                <td>
                    <span class="online-badge ${user.online ? 'online' : 'offline'}">
                        ${user.online ? '在线' : '离线'}
                    </span>
                </td>
                <td>${this.formatTime(user.created_at)}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn" onclick="AdminPanel.viewUserDetail('${user.id}')">详情</button>
                    </div>
                </td>
            </tr>
        `).join('');
    },

    getCachedUsers() {
        // 从localStorage获取缓存的用户数据
        const cached = localStorage.getItem('admin_cached_users');
        return cached ? JSON.parse(cached) : [];
    },

    filterUsers(query) {
        const filtered = this.allUsers.filter(user => {
            const lowerQuery = query.toLowerCase();
            return user.username.toLowerCase().includes(lowerQuery) ||
                   user.id.toLowerCase().includes(lowerQuery);
        });
        this.renderUsers(filtered);
    },

    viewUserDetail(userId) {
        alert(`用户详情功能开发中 (ID: ${userId})`);
    },

    formatTime(timestamp) {
        if (!timestamp) return '---';
        try {
            const date = new Date(timestamp);
            return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN');
        } catch {
            return timestamp;
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    AdminPanel.init();
});
