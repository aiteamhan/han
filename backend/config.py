import os
from datetime import timedelta

class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///wechat.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    # WebSocket配置
    SOCKETIO_CORS_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://localhost:8080', '*']
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # 应用配置
    JSON_SORT_KEYS = False

class DevelopmentConfig(Config):
    """开发配置"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """生产配置"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """测试配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# 获取当前配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}