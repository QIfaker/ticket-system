from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from functools import wraps
from app.models import get_db
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login', next=request.url))
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

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'
        
        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return redirect(url_for('auth.login'))
            
        db = get_db()
        user = db.authenticate_user(username, password, is_admin)
        
        if user:
            if user[2] != 'active':
                flash('账户已被禁用', 'error')
                return redirect(url_for('auth.login'))
                
            session['username'] = user[0]
            session['real_name'] = user[1]
            session['is_admin'] = is_admin
            flash('登录成功！', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('用户名或密码错误', 'error')
        
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        real_name = request.form.get('real_name')
        id_number = request.form.get('id_number')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        if not all([username, password, confirm_password, real_name, id_number]):
            flash('请填写所有必要信息', 'error')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return redirect(url_for('auth.register'))
            
        db = get_db()
        success, message = db.register_user(
            username, password, real_name, id_number, phone, email
        )
        
        if success:
            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
        
    return render_template('auth/register.html')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db = get_db()
    user = db.get_user_info(session['username'], session.get('is_admin', False))
    
    if request.method == 'POST':
        data = {
            'phone': request.form.get('phone'),
            'email': request.form.get('email')
        }
        
        if request.form.get('password'):
            data['password'] = request.form.get('password')
        
        success, message = db.update_user_info(
            session['username'], 
            data, 
            session.get('is_admin', False)
        )
        
        if success:
            flash('信息更新成功', 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('auth.profile'))
        
    return render_template('auth/profile.html', user=user)

@bp.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'success')
    return redirect(url_for('index')) 