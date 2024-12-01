from flask import Flask
from config import Config

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.update(test_config)
    
    # 注册数据库关闭函数
    from app.models import close_db
    app.teardown_appcontext(close_db)
    
    # 注册蓝图
    from app.routes import admin, auth, tickets
    app.register_blueprint(admin.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(tickets.bp)
    
    # 注册首页路由
    from app.routes.index import bp as index_bp
    app.register_blueprint(index_bp)
    
    return app 