from flask import g, current_app
from app.models.ticket_system import TicketSystem

def get_db():
    """获取数据库实例"""
    if 'db' not in g:
        g.db = TicketSystem(current_app.config['DATABASE'])
    return g.db

def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close_db() 