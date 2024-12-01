from flask import Flask, render_template, flash, redirect, url_for, g
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static')
    app.config.from_object(config_class)
    
    # 注册数据库关闭函数
    @app.teardown_appcontext
    def close_db(error):
        if hasattr(g, 'ticket_system'):
            g.ticket_system.close_db()
    
    # 注册主页路由
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # 注册错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        flash('页面不存在', 'error')
        return redirect(url_for('index'))

    @app.errorhandler(500)
    def internal_error(error):
        flash('服务器内部错误', 'error')
        return redirect(url_for('index'))
    
    # 注册蓝图
    from app.routes import admin, auth, tickets
    app.register_blueprint(admin.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(tickets.bp)
    
    return app 