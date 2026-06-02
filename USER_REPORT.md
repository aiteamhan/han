# 👤 用户检查报告

**生成时间**: 2026-06-02

---

## 📋 总体概览

该报告用于检查单个用户在系统中的注册、登录、资料、状态和安全性表现。

### 关键指标
- ✅ 用户名: `{{username}}`
- ✅ 用户ID: `{{user_id}}`
- ✅ 注册时间: `{{created_at}}`
- ✅ 最近登录: `{{last_seen}}`
- ✅ 在线状态: `{{online_status}}`

---

## 🔍 用户信息检查

### 用户基础信息
- 用户名: `{{username}}`
- 昵称: `{{nickname}}`
- 头像: `{{avatar}}`
- 个人签名: `{{bio}}`
- 注册时间: `{{created_at}}`
- 最后活跃时间: `{{last_seen}}`

### 账户状态
- 在线状态: `{{online_status}}`
- 是否已激活: `{{is_active}}`
- 密码安全: `{{password_security}}`

### 安全检查
- 密码长度: `{{password_length}}`（建议至少6位）
- 是否存在弱密码: `{{weak_password_check}}`
- 最近登录IP: `{{last_login_ip}}`
- 最近登录设备: `{{last_login_device}}`

---

## 🔐 登录与认证

### 登录行为
- 登录成功次数: `{{login_success_count}}`
- 登录失败次数: `{{login_failure_count}}`
- 最近登录时间: `{{recent_login_time}}`
- 是否存在异常登录: `{{suspicious_login}}`

### 认证令牌
- 当前 JWT 令牌: `{{token_status}}`
- 令牌过期时间: `{{token_expiry}}`
- 认证有效性: `{{token_validity}}`

---

## 🧾 用户活动摘要

### 最近活动
- 最近会话数量: `{{conversation_count}}`
- 最近消息数量: `{{message_count}}`
- 最近联系人数量: `{{contact_count}}`

### 关键操作
- 编辑资料次数: `{{profile_update_count}}`
- 上传头像次数: `{{avatar_update_count}}`
- 账号异常处理: `{{security_actions}}`

---

## ✅ 检查结论

- 用户状态: `{{status_summary}}`
- 主要风险点: `{{risk_summary}}`
- 建议改进:
  - `{{recommendation_1}}`
  - `{{recommendation_2}}`
  - `{{recommendation_3}}`

---

## 📞 备注

如需进一步排查该用户，请提供完整的登录日志、会话记录和系统审计数据。
