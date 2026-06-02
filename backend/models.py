from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import jwt
from functools import wraps

db = SQLAlchemy()

# ============ 用户表 ============
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255), default='https://via.placeholder.com/36')
    nickname = db.Column(db.String(80), default='')
    bio = db.Column(db.String(255), default='')
    online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    messages = db.relationship('Message', backref='sender', lazy='dynamic', foreign_keys='Message.sender_id')
    contacts = db.relationship('Contact', backref='user', lazy='dynamic', foreign_keys='Contact.user_id')
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'avatar': self.avatar,
            'nickname': self.nickname,
            'bio': self.bio,
            'online': self.online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat()
        }

# ============ 联系人表 ============
class Contact(db.Model):
    __tablename__ = 'contacts'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    contact_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    remarks = db.Column(db.String(80), default='')  # 备注名
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    contact = db.relationship('User', foreign_keys=[contact_id], backref='followers')
    
    def to_dict(self):
        return {
            'id': self.contact_id,
            'username': self.contact.username,
            'avatar': self.contact.avatar,
            'nickname': self.contact.nickname or self.contact.username,
            'remarks': self.remarks,
            'online': self.contact.online
        }

# ============ 会话表 ============
class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'private' or 'group'
    name = db.Column(db.String(255), default='')  # 群聊名称
    avatar = db.Column(db.String(255), default='')
    description = db.Column(db.String(255), default='')
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    members = db.relationship('ConversationMember', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, current_user_id=None):
        member_count = self.members.count()
        
        # 获取最后一条消息
        last_message = self.messages.order_by(Message.timestamp.desc()).first()
        if last_message:
            # 检查消息状态，如果已删除则显示[已撤回]
            last_msg_content = '[已撤回]' if last_message.status == 'deleted' else last_message.content
            last_msg_time = last_message.timestamp
        else:
            last_msg_content = '暂无消息'
            last_msg_time = self.created_at
        
        # 对于私聊，name应该是对方的用户名
        name = self.name
        if self.type == 'private' and not name and current_user_id:
            # 找到对方用户
            other_member = self.members.filter(ConversationMember.user_id != current_user_id).first()
            if other_member:
                other_user = User.query.get(other_member.user_id)
                name = other_user.username if other_user else '未知用户'
        
        data = {
            'id': self.id,
            'type': self.type,
            'name': name or '',
            'avatar': self.avatar or 'https://via.placeholder.com/48',
            'memberCount': member_count,
            'lastMessage': last_msg_content,
            'lastMessageTime': int(last_msg_time.timestamp() * 1000),
            'unread': 0,  # 需要从消息读取状态计算
        }
        
        return data

# ============ 会话成员表 ============
class ConversationMember(db.Model):
    __tablename__ = 'conversation_members'
    
    id = db.Column(db.String(36), primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    user = db.relationship('User', backref='conversations')
    
    def to_dict(self):
        return {
            'id': self.user_id,
            'username': self.user.username,
            'avatar': self.user.avatar,
            'nickname': self.user.nickname or self.user.username,
            'online': self.user.online
        }

# ============ 消息表 ============
class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    sender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='text')  # 'text', 'image', 'file', etc.
    status = db.Column(db.String(20), default='sent')  # 'sent', 'read', 'deleted'
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversationId': self.conversation_id,
            'senderId': self.sender_id,
            'senderName': self.sender.username,
            'senderAvatar': self.sender.avatar,
            'content': self.content,
            'type': self.type,
            'status': self.status,
            'isEdited': self.is_edited,
            'editedAt': int(self.edited_at.timestamp() * 1000) if self.edited_at else None,
            'timestamp': int(self.timestamp.timestamp() * 1000)
        }

# ============ 消息读取状态表 ============
class MessageRead(db.Model):
    __tablename__ = 'message_reads'
    
    id = db.Column(db.String(36), primary_key=True)
    message_id = db.Column(db.String(36), db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============ 文件上传表 ============
class FileUpload(db.Model):
    __tablename__ = 'file_uploads'
    
    id = db.Column(db.String(36), primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    sender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    saved_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # 字节
    file_type = db.Column(db.String(100), nullable=False)  # MIME type
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    sender = db.relationship('User', backref='files')
    conversation = db.relationship('Conversation', backref='files')
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversationId': self.conversation_id,
            'senderId': self.sender_id,
            'senderName': self.sender.username,
            'originalName': self.original_name,
            'fileSize': self.file_size,
            'fileType': self.file_type,
            'url': f'/api/files/{self.id}',
            'uploadedAt': int(self.uploaded_at.timestamp() * 1000)
        }