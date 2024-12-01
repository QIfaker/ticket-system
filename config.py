import os
from datetime import timedelta

class Config:
    # 基础配置
    SECRET_KEY = os.urandom(24)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # 数据库配置
    DATABASE = os.path.join(BASE_DIR, 'ticket_system.db')
    
    # Session配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # 应用配置
    DEBUG = True
    PORT = 8080
    HOST = '0.0.0.0' 