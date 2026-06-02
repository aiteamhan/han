from flask_socketio import emit, join_room, leave_room, rooms
from flask_jwt_extended import decode_token
from database import DatabaseManager
from models import db, User
import jwt
import logging

logger = logging.getLogger(__name__)

# 在线用户映射：user_id -> session_id
online_users = {}

def handle_connect(sid, environ, auth):
    """处理WebSocket连接"""
    try:
        # 从认证令牌中获取用户ID
        token = auth.get('token') if auth else None
        
        if not token:
            return False
        
        # 解码JWT令牌
        from flask import current_app
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = payload.get('sub')
        
        if not user_id:
            return False
        
        # 获取用户
        user = DatabaseManager.get_user(user_id)
        if not user:
            return False
        
        # 记录在线用户
        online_users[user_id] = sid
        
        # 设置用户在线
        DatabaseManager.set_user_online(user_id, True)
        
        # 加入用户的私有房间
        join_room(f'user_{user_id}')
        
        # 广播用户在线状态
        emit('user_status', {
            'userId': user_id,
            'online': True,
            'username': user.username
        }, broadcast=True)
        
        logger.info(f'User {user_id} connected (session: {sid})')
        
        return True
    
    except Exception as e:
        logger.error(f'Connection error: {e}')
        return False

def handle_disconnect(sid):
    """处理WebSocket断开连接"""
    try:
        # 查找断开连接的用户
        user_id = None
        for uid, session_id in online_users.items():
            if session_id == sid:
                user_id = uid
                break
        
        if user_id:
            # 移除在线用户记录
            del online_users[user_id]
            
            # 设置用户离线
            DatabaseManager.set_user_online(user_id, False)
            
            # 广播用户离线状态
            emit('user_status', {
                'userId': user_id,
                'online': False
            }, broadcast=True)
            
            logger.info(f'User {user_id} disconnected (session: {sid})')
    
    except Exception as e:
        logger.error(f'Disconnect error: {e}')

def handle_send_message(data, sid):
    """处理发送消息"""
    try:
        # 获取发送者用户ID
        sender_id = None
        for uid, session_id in online_users.items():
            if session_id == sid:
                sender_id = uid
                break
        
        if not sender_id:
            emit('error', {'message': '未授权'})
            return
        
        conversation_id = data.get('conversation_id')
        content = data.get('content', '').strip()
        
        if not conversation_id or not content:
            emit('error', {'message': '消息数据不完整'})
            return
        
        # 保存消息到数据库
        message = DatabaseManager.create_message(
            conversation_id, sender_id, content, 'text'
        )
        
        if not message:
            emit('error', {'message': '保存消息失败'})
            return
        
        sender = DatabaseManager.get_user(sender_id)
        
        # 获取会话的所有成员
        from models import ConversationMember
        members = ConversationMember.query.filter_by(conversation_id=conversation_id).all()
        member_ids = [m.user_id for m in members]
        
        # 广播消息给会话的所有成员
        message_data = {
            'id': message.id,
            'conversationId': conversation_id,
            'senderId': sender_id,
            'senderName': sender.username,
            'senderAvatar': sender.avatar,
            'content': content,
            'type': 'text',
            'timestamp': int(message.timestamp.timestamp() * 1000)
        }
        
        # 发送给会话的每个成员
        for member_id in member_ids:
            emit('message', {
                'type': 'message',
                'event': 'new_message',
                'data': message_data
            }, room=f'user_{member_id}')
        
        logger.info(f'Message from {sender_id} in conversation {conversation_id}')
    
    except Exception as e:
        logger.error(f'Send message error: {e}')
        emit('error', {'message': str(e)})

def handle_join_conversation(data, sid):
    """处理加入会话"""
    try:
        # 获取用户ID
        user_id = None
        for uid, session_id in online_users.items():
            if session_id == sid:
                user_id = uid
                break
        
        if not user_id:
            emit('error', {'message': '未授权'})
            return
        
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            emit('error', {'message': '会话ID不能为空'})
            return
        
        # 加入会话房间
        join_room(f'conversation_{conversation_id}')
        
        logger.info(f'User {user_id} joined conversation {conversation_id}')
    
    except Exception as e:
        logger.error(f'Join conversation error: {e}')
        emit('error', {'message': str(e)})

def handle_leave_conversation(data, sid):
    """处理离开会话"""
    try:
        # 获取用户ID
        user_id = None
        for uid, session_id in online_users.items():
            if session_id == sid:
                user_id = uid
                break
        
        if not user_id:
            return
        
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            return
        
        # 离开会话房间
        leave_room(f'conversation_{conversation_id}')
        
        logger.info(f'User {user_id} left conversation {conversation_id}')
    
    except Exception as e:
        logger.error(f'Leave conversation error: {e}')

def handle_typing(data, sid):
    """处理正在输入状态"""
    try:
        # 获取用户ID
        user_id = None
        for uid, session_id in online_users.items():
            if session_id == sid:
                user_id = uid
                break
        
        if not user_id:
            return
        
        conversation_id = data.get('conversation_id')
        is_typing = data.get('typing', True)
        
        if not conversation_id:
            return
        
        user = DatabaseManager.get_user(user_id)
        
        # 广播正在输入状态
        emit('typing', {
            'userId': user_id,
            'username': user.username,
            'typing': is_typing
        }, room=f'conversation_{conversation_id}')
    
    except Exception as e:
        logger.error(f'Typing error: {e}')

def handle_ping(data, sid):
    """处理心跳包"""
    try:
        emit('pong', {'timestamp': data.get('timestamp')})
    except Exception as e:
        logger.error(f'Ping error: {e}')

def emit_to_conversation(conversation_id, event_name, data):
    """向指定会话中的所有用户广播事件"""
    try:
        from flask_socketio import emit as socketio_emit
        socketio_emit(event_name, data, room=f'conversation_{conversation_id}')
    except Exception as e:
        logger.error(f'Error emitting to conversation: {e}')

def register_websocket_handlers(socketio):
    """注册所有WebSocket事件处理器"""
    
    @socketio.on('connect')
    def on_connect(auth):
        logger.info('Client connecting...')
        return handle_connect(__import__('flask_socketio').request.sid, __import__('flask').request.environ, auth)
    
    @socketio.on('disconnect')
    def on_disconnect():
        logger.info('Client disconnecting...')
        handle_disconnect(__import__('flask_socketio').request.sid)
    
    @socketio.on('send_message')
    def on_send_message(data):
        handle_send_message(data, __import__('flask_socketio').request.sid)
    
    @socketio.on('join_conversation')
    def on_join_conversation(data):
        handle_join_conversation(data, __import__('flask_socketio').request.sid)
    
    @socketio.on('leave_conversation')
    def on_leave_conversation(data):
        handle_leave_conversation(data, __import__('flask_socketio').request.sid)
    
    @socketio.on('typing')
    def on_typing(data):
        handle_typing(data, __import__('flask_socketio').request.sid)
    
    @socketio.on('ping')
    def on_ping(data):
        handle_ping(data, __import__('flask_socketio').request.sid)