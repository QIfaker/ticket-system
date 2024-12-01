from flask import (
    Blueprint, render_template, request, jsonify, flash, 
    redirect, url_for, session
)
from app.routes.auth import login_required
from app.models import get_db
from datetime import datetime, timedelta
from functools import wraps

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            flash('需要管理员权限', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def dashboard():
    """管理员仪表板"""
    db = get_db()
    
    # 获取今天的日期
    today = datetime.now().date()
    
    # 获取销售统计
    sales = db.get_daily_sales(today.strftime('%Y-%m-%d'))
    
    # 获取车次统计
    trains = db.search_trains()
    
    # 计算总收入
    total_revenue = sum(sale[4] for sale in sales) if sales else 0
    
    return render_template('admin/dashboard.html',
                         sales=sales,
                         trains=trains,
                         today=today.strftime('%Y-%m-%d'),
                         total_revenue=total_revenue)

@bp.route('/reports')
@login_required
@admin_required
def reports():
    """销售报表"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        today = datetime.now().date()
        end_date = today.strftime('%Y-%m-%d')
        start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    
    db = get_db()
    report_data = db.generate_sales_report(start_date, end_date)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(report_data)
    
    return render_template('admin/reports.html',
                         report_data=report_data,
                         start_date=start_date,
                         end_date=end_date)

@bp.route('/trains/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_train():
    """添加新车次"""
    if request.method == 'POST':
        train_id = request.form.get('train_id')
        departure = request.form.get('departure')
        destination = request.form.get('destination')
        departure_time = request.form.get('departure_time')
        arrival_time = request.form.get('arrival_time')
        total_seats = request.form.get('total_seats')
        price = request.form.get('price')
        
        if not all([train_id, departure, destination, departure_time, 
                   arrival_time, total_seats, price]):
            flash('请填写所有必要信息', 'error')
            return redirect(url_for('admin.add_train'))
        
        try:
            total_seats = int(total_seats)
            price = float(price)
        except ValueError:
            flash('座位数和票价必须是数字', 'error')
            return redirect(url_for('admin.add_train'))
        
        db = get_db()
        success = db.add_train(train_id, departure, destination, departure_time,
                             arrival_time, total_seats, price)
        
        if success:
            flash('车次添加成功', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('车次添加失败', 'error')
    
    return render_template('admin/add_train.html')

@bp.route('/statistics')
@login_required
@admin_required
def statistics():
    """统计数据"""
    period = request.args.get('period', 'daily')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    db = get_db()
    stats = db.get_statistics(period, start_date, end_date)
    
    return render_template('admin/statistics.html',
                         stats=stats,
                         period=period,
                         start_date=start_date,
                         end_date=end_date) 