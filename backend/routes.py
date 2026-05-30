from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import DatabaseManager, db
from models import User, Message, MessageRead, ConversationMember
import uuid

api_bp = Blueprint('api', __name__, url_prefix='/api')

# ============ 认证路由 ============
@api_bp.route('/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    # 基本验证
    if not username or not password:
        return jsonify({
            'code': 1001,
            'message': '用户名和密码不能为空'
        }), 400
    
    try:
        user = DatabaseManager.create_user(username, password)
        return jsonify({
            'code': 0,
            'message': '注册成功',
            'data': {
                'user': user.to_dict()
            }
        }), 201
    except ValueError as e:
        error_msg = str(e)
        error_code = 1002  # 默认错误码
        
        # 根据错误信息设置特定的错误码
        if '已存在' in error_msg:
            error_code = 1002  # 用户名已存在
        elif '长度' in error_msg:
            error_code = 1003  # 长度不符
        
        return jsonify({
            'code': error_code,
            'message': error_msg
        }), 400
    except Exception as e:
        print(f'Register error: {e}')
        return jsonify({
            'code': 5000,
            'message': '注册失败，请稍后重试'
        }), 500

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """用户登录"""
    from flask_jwt_extended import create_access_token
    
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')

    # 兼容异常请求体，防止 username/password 为 dict 或其他类型导致 500
    if isinstance(username, dict):
        username = username.get('username', '')
    if isinstance(password, dict):
        password = password.get('password', '')
    if not isinstance(username, str):
        username = ''
    if not isinstance(password, str):
        password = ''

    username = username.strip()
    password = password.strip()
    
    if not username or not password:
        return jsonify({'message': '用户名和密码不能为空'}), 400
    
    user = DatabaseManager.get_user_by_username(username)
    
    if not user or not DatabaseManager.verify_password(user, password):
        return jsonify({'message': '用户名或密码错误'}), 401
    
    # 创建JWT令牌
    token = create_access_token(identity=user.id)
    
    # 设置用户在线
    DatabaseManager.set_user_online(user.id, True)
    
    return jsonify({
        'code': 0,
        'message': '登录成功',
        'data': {
            'token': token,
            'user': user.to_dict()
        }
    }), 200

# ============ 用户路由 ============
@api_bp.route('/users/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前用户信息"""
    user_id = get_jwt_identity()
    user = DatabaseManager.get_user(user_id)
    
    if not user:
        return jsonify({'message': '用户不存在'}), 404
    
    return jsonify({
        'code': 0,
        'data': user.to_dict()
    }), 200

@api_bp.route('/users/me', methods=['PUT'])
@jwt_required()
def update_user():
    """更新当前用户信息"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # 只允许更新这些字段
    allowed_fields = ['avatar', 'nickname', 'bio']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    user = DatabaseManager.update_user(user_id, **update_data)
    
    return jsonify({
        'code': 0,
        'data': user.to_dict()
    }), 200

@api_bp.route('/users/search', methods=['GET'])
@jwt_required()
def search_users():
    """搜索用户"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'code': 0, 'data': []}), 200
    
    users = DatabaseManager.search_users(query)
    
    return jsonify({
        'code': 0,
        'data': users
    }), 200

# ============ 会话路由 ============
@api_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """获取用户的所有会话"""
    user_id = get_jwt_identity()
    conversations = DatabaseManager.get_conversations(user_id)
    
    return jsonify({
        'code': 0,
        'data': conversations
    }), 200

@api_bp.route('/conversations', methods=['POST'])
@jwt_required()
def create_conversation():
    """创建会话"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    conv_type = data.get('type')  # 'private' or 'group'
    
    try:
        if conv_type == 'private':
            participants = data.get('participants', [])
            if not participants or len(participants) != 1:
                return jsonify({'message': '私聊必须指定一个其他用户'}), 400
            
            other_user_id = participants[0]
            conversation = DatabaseManager.create_private_conversation(user_id, other_user_id)
        
        elif conv_type == 'group':
            name = data.get('name', '新群聊')
            members = data.get('participants', [])
            if user_id not in members:
                members.append(user_id)
            
            conversation = DatabaseManager.create_group_conversation(name, user_id, members)
        
        else:
            return jsonify({'message': '无效的会话类型'}), 400
        
        return jsonify({
            'code': 0,
            'data': conversation.to_dict(user_id)
        }), 201
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/conversations/<conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    """获取会话详情"""
    user_id = get_jwt_identity()
    conversation = DatabaseManager.get_conversation(conversation_id)
    
    if not conversation:
        return jsonify({'message': '会话不存在'}), 404
    
    return jsonify({
        'code': 0,
        'data': conversation.to_dict(user_id)
    }), 200

@api_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    """删除会话"""
    user_id = get_jwt_identity()
    conversation = DatabaseManager.get_conversation(conversation_id)
    
    if not conversation:
        return jsonify({'message': '会话不存在'}), 404
    
    # 检查权限
    from models import ConversationMember
    member = ConversationMember.query.filter_by(
        conversation_id=conversation_id,
        user_id=user_id
    ).first()
    
    if not member:
        return jsonify({'message': '无权限'}), 403
    
    DatabaseManager.delete_conversation(conversation_id)
    
    return jsonify({
        'code': 0,
        'message': '删除成功'
    }), 200

@api_bp.route('/conversations/<conversation_id>/mark-read', methods=['POST'])
@jwt_required()
def mark_as_read(conversation_id):
    """标记会话消息为已读"""
    user_id = get_jwt_identity()
    conversation = DatabaseManager.get_conversation(conversation_id)

    if not conversation:
        return jsonify({'message': '会话不存在'}), 404

    member = ConversationMember.query.filter_by(
        conversation_id=conversation_id,
        user_id=user_id
    ).first()

    if not member:
        return jsonify({'message': '无权限'}), 403

    unread_messages = Message.query.filter(
        Message.conversation_id == conversation_id,
        Message.sender_id != user_id
    ).all()

    for message in unread_messages:
        existing = MessageRead.query.filter_by(message_id=message.id, user_id=user_id).first()
        if not existing:
            read_record = MessageRead(
                id=str(uuid.uuid4()),
                message_id=message.id,
                user_id=user_id
            )
            db.session.add(read_record)

    db.session.commit()

    return jsonify({
        'code': 0,
        'message': '标记成功'
    }), 200

# ============ 消息路由 ============
@api_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
@jwt_required()
def get_messages(conversation_id):
    """获取会话消息"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    messages = DatabaseManager.get_messages(conversation_id, limit, offset)
    
    return jsonify({
        'code': 0,
        'data': messages
    }), 200

@api_bp.route('/conversations/<conversation_id>/messages', methods=['POST'])
@jwt_required()
def send_message(conversation_id):
    """发送消息"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    content = data.get('content', '').strip()
    msg_type = data.get('type', 'text')
    
    if not content:
        return jsonify({'message': '消息内容不能为空'}), 400
    
    try:
        message = DatabaseManager.create_message(
            conversation_id, user_id, content, msg_type
        )
        
        return jsonify({
            'code': 0,
            'data': message.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/messages/<message_id>', methods=['DELETE'])
@jwt_required()
def revoke_message(message_id):
    """撤回消息"""
    user_id = get_jwt_identity()
    message = DatabaseManager.get_message(message_id)
    
    if not message:
        return jsonify({'message': '消息不存在'}), 404
    
    if message.sender_id != user_id:
        return jsonify({'message': '只能撤回自己的消息'}), 403
    
    DatabaseManager.delete_message(message_id)
    
    return jsonify({
        'code': 0,
        'message': '撤回成功'
    }), 200

# ============ 联系人路由 ============
@api_bp.route('/contacts', methods=['GET'])
@jwt_required()
def get_contacts():
    """获取联系人列表"""
    user_id = get_jwt_identity()
    contacts = DatabaseManager.get_contacts(user_id)
    
    return jsonify({
        'code': 0,
        'data': contacts
    }), 200

@api_bp.route('/contacts', methods=['POST'])
@jwt_required()
def add_contact():
    """添加联系人"""
    user_id = get_jwt_identity()
    data = request.get_json()
    contact_id = data.get('user_id')
    
    if not contact_id:
        return jsonify({'message': '用户ID不能为空'}), 400
    
    try:
        contact = DatabaseManager.add_contact(user_id, contact_id)
        
        # 创建或获取私聊会话
        conversation = DatabaseManager.create_private_conversation(user_id, contact_id)
        
        return jsonify({
            'code': 0,
            'data': {
                'contact': contact.to_dict(),
                'conversation': conversation.to_dict(user_id)
            }
        }), 201
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/contacts/<contact_id>', methods=['DELETE'])
@jwt_required()
def remove_contact(contact_id):
    """删除联系人"""
    user_id = get_jwt_identity()
    DatabaseManager.remove_contact(user_id, contact_id)
    
    return jsonify({
        'code': 0,
        'message': '删除成功'
    }), 200

# ============ 群聊路由 ============
@api_bp.route('/groups', methods=['POST'])
@jwt_required()
def create_group():
    """创建群聊"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    name = data.get('name', '新群聊')
    members = data.get('members', [])
    
    if user_id not in members:
        members.append(user_id)
    
    try:
        conversation = DatabaseManager.create_group_conversation(name, user_id, members)
        
        return jsonify({
            'code': 0,
            'data': conversation.to_dict(user_id)
        }), 201
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/groups/<group_id>/members', methods=['GET'])
@jwt_required()
def get_group_members(group_id):
    """获取群成员"""
    from models import ConversationMember
    
    members = ConversationMember.query.filter_by(conversation_id=group_id).all()
    
    return jsonify({
        'code': 0,
        'data': [m.to_dict() for m in members]
    }), 200

@api_bp.route('/groups/<group_id>/members', methods=['POST'])
@jwt_required()
def add_group_member(group_id):
    """添加群成员"""
    user_id = get_jwt_identity()
    data = request.get_json()
    new_member_id = data.get('user_id')
    
    try:
        member = DatabaseManager.add_group_member(group_id, new_member_id)
        
        return jsonify({
            'code': 0,
            'data': member.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/groups/<group_id>/members/<member_id>', methods=['DELETE'])
@jwt_required()
def remove_group_member(group_id, member_id):
    """移除群成员"""
    user_id = get_jwt_identity()
    
    DatabaseManager.remove_group_member(group_id, member_id)
    
    return jsonify({
        'code': 0,
        'message': '移除成功'
    }), 200

@api_bp.route('/groups/<group_id>', methods=['PUT'])
@jwt_required()
def update_group(group_id):
    """更新群信息"""
    data = request.get_json() or {}
    return jsonify({
        'code': 0,
        'message': '更新成功'
    }), 200


# ============ 管理员API路由 ============
@api_bp.route('/admin/stats', methods=['GET'])
def get_admin_stats():
    """获取管理员仪表板统计数据"""
    try:
        from models import Conversation, Message
        
        total_users = User.query.count()
        online_users = User.query.filter_by(online=True).count()
        total_conversations = Conversation.query.count()
        total_messages = Message.query.count()
        
        return jsonify({
            'code': 0,
            'data': {
                'totalUsers': total_users,
                'onlineUsers': online_users,
                'totalConversations': total_conversations,
                'totalMessages': total_messages
            }
        }), 200
    except Exception as e:
        print(f'Admin stats error: {e}')
        return jsonify({
            'code': 5000,
            'message': '获取统计数据失败'
        }), 500


@api_bp.route('/admin/users', methods=['GET'])
def get_admin_users():
    """获取所有用户列表"""
    try:
        users = User.query.all()
        users_data = []
        
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'avatar': user.avatar,
                'online': user.online,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_seen': user.last_seen.isoformat() if user.last_seen else None
            })
        
        return jsonify({
            'code': 0,
            'data': {
                'users': users_data,
                'total': len(users_data)
            }
        }), 200
    except Exception as e:
        print(f'Get admin users error: {e}')
        return jsonify({
            'code': 5000,
            'message': '获取用户列表失败'
        }), 500


# ============ 文件上传路由 ============
@api_bp.route('/files/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """上传文件"""
    import os
    from werkzeug.utils import secure_filename
    
    user_id = get_jwt_identity()
    
    if 'file' not in request.files:
        return jsonify({
            'code': 1005,
            'message': '请选择要上传的文件'
        }), 400
    
    file = request.files['file']
    conversation_id = request.form.get('conversation_id')
    
    if file.filename == '':
        return jsonify({
            'code': 1005,
            'message': '文件名不能为空'
        }), 400
    
    if not conversation_id:
        return jsonify({
            'code': 1005,
            'message': '会话ID不能为空'
        }), 400
    
    try:
        # 验证文件大小 (限制为 100MB)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            return jsonify({
                'code': 1006,
                'message': '文件大小超过限制 (最大 100MB)'
            }), 400
        
        # 创建文件保存目录
        upload_dir = os.path.join(os.path.dirname(__file__), '../uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(filename)[1]
        saved_filename = f'{file_id}{file_ext}'
        file_path = os.path.join(upload_dir, saved_filename)
        
        # 保存文件
        file.save(file_path)
        
        # 保存文件信息到数据库
        from models import FileUpload
        file_record = FileUpload(
            id=file_id,
            conversation_id=conversation_id,
            sender_id=user_id,
            original_name=filename,
            saved_name=saved_filename,
            file_size=file_size,
            file_type=file.content_type
        )
        db.session.add(file_record)
        db.session.commit()
        
        # 创建文件消息
        message = DatabaseManager.create_message(
            conversation_id,
            user_id,
            f'/api/files/{file_id}',  # 文件URL
            'file'
        )
        
        # 添加文件元数据到消息内容
        message.content = f'{{"fileId": "{file_id}", "fileName": "{filename}", "fileSize": {file_size}, "fileType": "{file.content_type}"}}'
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': '上传成功',
            'data': {
                'fileId': file_id,
                'fileName': filename,
                'fileSize': file_size,
                'fileType': file.content_type,
                'url': f'/api/files/{file_id}',
                'message': message.to_dict()
            }
        }), 201
    
    except Exception as e:
        print(f'File upload error: {e}')
        return jsonify({
            'code': 5000,
            'message': '上传失败，请稍后重试'
        }), 500


@api_bp.route('/files/<file_id>', methods=['GET'])
def download_file(file_id):
    """下载/查看文件"""
    import os
    from flask import send_file
    
    try:
        from models import FileUpload
        file_record = FileUpload.query.get(file_id)
        
        if not file_record:
            return jsonify({
                'code': 1007,
                'message': '文件不存在'
            }), 404
        
        upload_dir = os.path.join(os.path.dirname(__file__), '../uploads')
        file_path = os.path.join(upload_dir, file_record.saved_name)
        
        if not os.path.exists(file_path):
            return jsonify({
                'code': 1007,
                'message': '文件未找到'
            }), 404
        
        return send_file(
            file_path,
            download_name=file_record.original_name,
            as_attachment=True
        )
    
    except Exception as e:
        print(f'File download error: {e}')
        return jsonify({
            'code': 5000,
            'message': '下载失败'
        }), 500


@api_bp.route('/messages/<message_id>/edit', methods=['PUT'])
@jwt_required()
def edit_message(message_id):
    """编辑消息"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    message = DatabaseManager.get_message(message_id)
    
    if not message:
        return jsonify({'message': '消息不存在'}), 404
    
    if message.sender_id != user_id:
        return jsonify({'message': '只能编辑自己的消息'}), 403
    
    new_content = data.get('content', '').strip()
    
    if not new_content:
        return jsonify({'message': '消息内容不能为空'}), 400
    
    try:
        message = DatabaseManager.edit_message(message_id, new_content)
        
        return jsonify({
            'code': 0,
            'data': message.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500
        return jsonify({
            'code': 5000,
            'message': '获取用户列表失败'
        }), 500
def update_group(group_id):
    """更新群聊信息"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    from models import Conversation
    group = Conversation.query.get(group_id)
    
    if not group:
        return jsonify({'message': '群聊不存在'}), 404
    
    allowed_fields = ['name', 'avatar', 'description']
    for field in allowed_fields:
        if field in data:
            setattr(group, field, data[field])
    
    db.session.commit()
    
    return jsonify({
        'code': 0,
        'data': group.to_dict(user_id)
    }), 200