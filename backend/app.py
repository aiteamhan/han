from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from config import config
from models import db
from database import DatabaseManager
from routes import api_bp
from websocket_handler import register_websocket_handlers
import logging
import os

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='development'):
    """创建Flask应用"""
    
    # 选择配置
    config_obj = config.get(config_name, config['default'])
    
    # 创建应用
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    app.config.from_object(config_obj)
    
    # 初始化数据库
    db.init_app(app)
    
    # 初始化JWT
    jwt = JWTManager(app)
    
    # 初始化CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 初始化SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # 注册WebSocket处理器
    register_websocket_handlers(socketio)
    
    # 注册蓝图
    app.register_blueprint(api_bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    # 首页路由
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    # 管理后台路由
    @app.route('/admin')
    def admin_panel():
        return app.send_static_file('admin.html')
    
    # 健康检查路由
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok'}), 200
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'message': '资源不存在'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({'message': '服务器错误'}), 500
    
    # 请求前钩子
    @app.before_request
    def before_request():
        logger.info(f'{__import__("flask").request.method} {__import__("flask").request.path}')
    
    logger.info(f'App created with config: {config_name}')
    
    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app(os.environ.get('FLASK_ENV', 'development'))
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)