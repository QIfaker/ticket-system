import os

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ticket_system.db')
    
    # 应用配置
    TITLE = '车站售票系统'
    ADMIN_EMAIL = 'admin@example.com'
    
    # 数据库配置
    DB_INIT_SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = 3600  # 会话有效期（秒）
    
    # 上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大上传大小（16MB）