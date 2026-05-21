import os
import sys
from app import create_app

if __name__ == '__main__':
    # 获取环境配置
    env = os.environ.get('FLASK_ENV', 'development')
    
    # 创建应用
    app, socketio = create_app(env)
    
    # 运行应用
    print(f'Starting WeChat server in {env} mode...')
    print(f'Server running at http://0.0.0.0:5000')
    print(f'WebSocket at ws://0.0.0.0:5000/socket.io')
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=(env == 'development'),
        allow_unsafe_werkzeug=True
    )