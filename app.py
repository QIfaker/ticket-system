from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from program import TicketSystem # type: ignore
from datetime import datetime

app = Flask(__name__)
# 使用随机生成的密钥
app.secret_key = os.urandom(24)

# 创建全局数据库连接
def get_db():
    if not hasattr(app, 'ticket_system'):
        app.ticket_system = TicketSystem()
    return app.ticket_system

# 添加登录要求装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('请先登录', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            flash('需要管理员权限', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/trains')
def trains():
    try:
        departure = request.args.get('departure')
        destination = request.args.get('destination')
        trains = get_db().search_trains(departure, destination)
        return render_template('trains.html', trains=trains)
    except Exception as e:
        flash(f'查询失败: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/book_ticket', methods=['GET', 'POST'])
@login_required
def book_ticket():
    if request.method == 'POST':
        try:
            train_id = request.form.get('train_id')
            passenger_name = request.form.get('passenger_name')
            passenger_id = request.form.get('passenger_id')
            is_group = request.form.get('is_group') == 'on'
            
            if not all([train_id, passenger_name, passenger_id]):
                flash('请填写所有必要信息', 'error')
                return redirect(url_for('book_ticket'))
            
            success, message = get_db().book_ticket(
                train_id, passenger_name, passenger_id, is_group
            )
            
            if success:
                flash('订票成功！' + message, 'success')
            else:
                flash('订票失败：' + message, 'error')
            return redirect(url_for('book_ticket'))
        except Exception as e:
            flash(f'订票失败: {str(e)}', 'error')
            return redirect(url_for('book_ticket'))
            
    return render_template('book_ticket.html')

@app.route('/refund_ticket', methods=['GET', 'POST'])
@login_required
def refund_ticket():
    if request.method == 'POST':
        try:
            ticket_id = request.form.get('ticket_id')
            if not ticket_id:
                flash('请输入票号', 'error')
                return redirect(url_for('refund_ticket'))
                
            success, message = get_db().refund_ticket(int(ticket_id))
            
            if success:
                flash('退票成功！', 'success')
            else:
                flash('退票失败：' + message, 'error')
            return redirect(url_for('refund_ticket'))
        except ValueError:
            flash('无效的票号', 'error')
            return redirect(url_for('refund_ticket'))
        except Exception as e:
            flash(f'退票失败: {str(e)}', 'error')
            return redirect(url_for('refund_ticket'))
            
    return render_template('refund_ticket.html')

@app.route('/admin')
@login_required
@admin_required
def admin():
    return render_template('admin.html')

@app.route('/api/sales_report')
@login_required
@admin_required
def sales_report():
    try:
        start_date = request.args.get('start_date', '2024-01-01')
        end_date = request.args.get('end_date', '2024-12-31')
        report = get_db().generate_sales_report(start_date, end_date)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('请输入用户名和密码', 'error')
                return redirect(url_for('login'))
                
            user = get_db().authenticate_user(username, password)
            
            if user:
                session['username'] = user[0]
                session['is_admin'] = user[1]
                flash('登录成功！', 'success')
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('index'))
            else:
                flash('用户名或密码错误', 'error')
        except Exception as e:
            flash(f'登录失败: {str(e)}', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'success')
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    flash('页面不存在', 'error')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_server_error(e):
    flash('服务器内部错误', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    try:
        # 确保模板目录存在
        if not os.path.exists('templates'):
            os.makedirs('templates')
            
        # 启动应用
        app.run(host='0.0.0.0', port=8080, debug=True)
    except Exception as e:
        print(f"启动失败: {str(e)}") 