from models import db, User, Contact, Conversation, ConversationMember, Message, MessageRead
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    """数据库操作管理器"""
    
    @staticmethod
    def init_db(app):
        """初始化数据库"""
        with app.app_context():
            db.create_all()
    
    @staticmethod
    def create_user(username, password):
        """创建用户"""
        # 验证用户名
        if not username or len(username.strip()) == 0:
            raise ValueError('用户名不能为空')
        
        username = username.strip()
        if len(username) < 3:
            raise ValueError('用户名长度至少3个字符')
        if len(username) > 20:
            raise ValueError('用户名长度不能超过20个字符')
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            raise ValueError('用户名已存在，请选择其他用户名')
        
        # 验证密码
        if not password or len(password) == 0:
            raise ValueError('密码不能为空')
        if len(password) < 6:
            raise ValueError('密码长度不能少于6位')
        if len(password) > 50:
            raise ValueError('密码长度不能超过50位')
        
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def get_user(user_id):
        """获取用户"""
        return User.query.get(user_id)
    
    @staticmethod
    def get_user_by_username(username):
        """通过用户名获取用户"""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def verify_password(user, password):
        """验证密码"""
        return check_password_hash(user.password_hash, password)
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """更新用户信息"""
        user = User.query.get(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            user.updated_at = datetime.utcnow()
            db.session.commit()
        return user
    
    @staticmethod
    def set_user_online(user_id, online=True):
        """设置用户在线状态"""
        user = User.query.get(user_id)
        if user:
            user.online = online
            user.last_seen = datetime.utcnow()
            db.session.commit()
        return user
    
    # ============ 联系人操作 ============
    @staticmethod
    def add_contact(user_id, contact_id, remarks=''):
        """添加联系人"""
        if user_id == contact_id:
            raise ValueError('不能添加自己为联系人')
        
        # 检查是否已添加
        existing = Contact.query.filter_by(user_id=user_id, contact_id=contact_id).first()
        if existing:
            return existing
        
        contact = Contact(
            id=str(uuid.uuid4()),
            user_id=user_id,
            contact_id=contact_id,
            remarks=remarks
        )
        db.session.add(contact)
        db.session.commit()
        return contact
    
    @staticmethod
    def remove_contact(user_id, contact_id):
        """删除联系人"""
        Contact.query.filter_by(user_id=user_id, contact_id=contact_id).delete()
        db.session.commit()
    
    @staticmethod
    def get_contacts(user_id):
        """获取用户的联系人列表"""
        contacts = Contact.query.filter_by(user_id=user_id).all()
        return [c.to_dict() for c in contacts]
    
    # ============ 会话操作 ============
    @staticmethod
    def create_private_conversation(user1_id, user2_id):
        """创建私聊会话"""
        # 检查是否已存在
        existing = Conversation.query.join(ConversationMember).filter(
            Conversation.type == 'private',
            ConversationMember.user_id.in_([user1_id, user2_id])
        ).all()
        
        for conv in existing:
            members = [m.user_id for m in conv.members.all()]
            if set(members) == {user1_id, user2_id}:
                return conv
        
        # 创建新会话
        conversation = Conversation(
            id=str(uuid.uuid4()),
            type='private',
            created_by=user1_id
        )
        
        db.session.add(conversation)
        db.session.flush()
        
        # 添加成员
        member1 = ConversationMember(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            user_id=user1_id
        )
        member2 = ConversationMember(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            user_id=user2_id
        )
        
        db.session.add(member1)
        db.session.add(member2)
        db.session.commit()
        
        return conversation
    
    @staticmethod
    def create_group_conversation(group_name, creator_id, members):
        """创建群聊会话"""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            type='group',
            name=group_name,
            created_by=creator_id
        )
        
        db.session.add(conversation)
        db.session.flush()
        
        # 添加成员
        for member_id in members:
            member = ConversationMember(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                user_id=member_id
            )
            db.session.add(member)
        
        db.session.commit()
        return conversation
    
    @staticmethod
    def get_conversations(user_id):
        """获取用户的所有会话"""
        conversations = Conversation.query.join(ConversationMember).filter(
            ConversationMember.user_id == user_id
        ).all()
        
        result = []
        for conv in conversations:
            conv_dict = conv.to_dict()
            
            # 对于私聊，设置对方信息
            if conv.type == 'private':
                members = [m.user_id for m in conv.members.all() if m.user_id != user_id]
                if members:
                    other_user = User.query.get(members[0])
                    conv_dict['name'] = other_user.username
                    conv_dict['avatar'] = other_user.avatar
                    conv_dict['online'] = other_user.online
                    conv_dict['participantId'] = other_user.id
            else:
                # 群聊设置成员信息
                conv_dict['members'] = [m.to_dict() for m in conv.members.all()]
            
            result.append(conv_dict)
        
        return result
    
    @staticmethod
    def get_conversation(conversation_id):
        """获取会话详情"""
        return Conversation.query.get(conversation_id)
    
    @staticmethod
    def delete_conversation(conversation_id):
        """删除会话"""
        Conversation.query.filter_by(id=conversation_id).delete()
        db.session.commit()
    
    @staticmethod
    def add_group_member(conversation_id, user_id):
        """添加群成员"""
        # 检查是否已是成员
        existing = ConversationMember.query.filter_by(
            conversation_id=conversation_id,
            user_id=user_id
        ).first()
        
        if existing:
            return existing
        
        member = ConversationMember(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            user_id=user_id
        )
        db.session.add(member)
        db.session.commit()
        return member
    
    @staticmethod
    def remove_group_member(conversation_id, user_id):
        """移除群成员"""
        ConversationMember.query.filter_by(
            conversation_id=conversation_id,
            user_id=user_id
        ).delete()
        db.session.commit()
    
    # ============ 消息操作 ============
    @staticmethod
    def create_message(conversation_id, sender_id, content, msg_type='text'):
        """创建消息"""
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            type=msg_type
        )
        db.session.add(message)
        db.session.commit()
        return message
    
    @staticmethod
    def get_messages(conversation_id, limit=50, offset=0):
        """获取会话消息"""
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(
            Message.timestamp
        ).limit(limit).offset(offset).all()
        
        return [m.to_dict() for m in messages]
    
    @staticmethod
    def get_message(message_id):
        """获取消息"""
        return Message.query.get(message_id)
    
    @staticmethod
    def delete_message(message_id):
        """删除消息"""
        message = Message.query.get(message_id)
        if message:
            message.status = 'deleted'
            db.session.commit()
        return message
    
    @staticmethod
    def search_users(query, limit=10):
        """搜索用户"""
        users = User.query.filter(
            User.username.ilike(f'%{query}%')
        ).limit(limit).all()
        
        return [u.to_dict() for u in users]