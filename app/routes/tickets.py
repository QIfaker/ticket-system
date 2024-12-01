from datetime import datetime, date
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from app.routes.auth import login_required
from app.models import get_db

bp = Blueprint('tickets', __name__, url_prefix='/tickets')

@bp.route('/search')
def search():
    departure = request.args.get('departure')
    destination = request.args.get('destination')
    date_str = request.args.get('date')
    time_range = request.args.get('time_range')
    
    # 获取今天的日期
    today = date.today().strftime('%Y-%m-%d')
    
    trains = []
    if departure or destination:
        trains = get_db().search_trains(departure, destination)
        
        # 根据时间段筛选
        if time_range:
            filtered_trains = []
            for train in trains:
                time = datetime.strptime(train[3], '%H:%M').time()
                if time_range == 'morning' and 6 <= time.hour < 12:
                    filtered_trains.append(train)
                elif time_range == 'afternoon' and 12 <= time.hour < 18:
                    filtered_trains.append(train)
                elif time_range == 'evening' and 18 <= time.hour < 24:
                    filtered_trains.append(train)
            trains = filtered_trains
    
    return render_template('tickets/search.html', 
                         trains=trains, 
                         today=today)

@bp.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    """购票功能"""
    if request.method == 'POST':
        train_id = request.form.get('train_id')
        passenger_name = request.form.get('passenger_name')
        passenger_id = request.form.get('passenger_id')
        is_group = request.form.get('is_group') == 'on'
        
        if not all([train_id, passenger_name, passenger_id]):
            flash('请填写所有必要信息', 'error')
            return redirect(url_for('tickets.book'))
        
        # 获取用户信息
        db = get_db()
        user = db.get_user_info(session['username'], session.get('is_admin', False))
        if not user:
            flash('用户信息获取失败', 'error')
            return redirect(url_for('tickets.book'))
        
        # 如果没有提供乘客信息，使用用户自己的信息
        if not passenger_name:
            passenger_name = user[2]  # real_name 字段
        if not passenger_id:
            passenger_id = user[4]    # id_number 字段
        
        success, message = db.book_ticket(
            train_id, passenger_name, passenger_id, is_group
        )
        
        if success:
            flash('订票成功！' + message, 'success')
            return redirect(url_for('tickets.search_person'))
        else:
            flash('订票失败：' + message, 'error')
            return redirect(url_for('tickets.book'))
            
    # 获取预选的车次ID
    train_id = request.args.get('train_id')
    
    # 获取用户信息
    db = get_db()
    user = db.get_user_info(session['username'], session.get('is_admin', False))
    user_data = {
        'real_name': user[2] if user else '',
        'id_number': user[4] if user else ''
    }
    
    return render_template('tickets/book.html', 
                         train_id=train_id,
                         user=user_data)

@bp.route('/refund', methods=['GET', 'POST'])
@login_required
def refund():
    return render_template('tickets/refund.html')

@bp.route('/search_person', methods=['GET', 'POST'])
def search_person():
    """个人车票查询"""
    tickets = []
    db = get_db()
    user_data = None
    
    if request.method == 'POST':
        name = request.form.get('name')
        id_number = request.form.get('id_number')
        
        if not name and not id_number:
            flash('请输入姓名或身份证号', 'error')
            return redirect(url_for('tickets.search_person'))
        
        tickets = db.search_tickets_by_person(name, id_number)
    else:
        # 如果用户已登录，默认查询自己的车票
        if 'username' in session:
            user = db.get_user_info(session['username'], session.get('is_admin', False))
            if user:
                user_data = {
                    'real_name': user[2],
                    'id_number': user[4]
                }
                tickets = db.search_tickets_by_person(
                    name=user[2],
                    id_number=user[4]
                )
    
    return render_template('tickets/search_person.html', 
                         tickets=tickets,
                         user=user_data) 

@bp.route('/refund_ticket', methods=['POST'])
@login_required
def refund_ticket():
    """退票处理"""
    ticket_id = request.form.get('ticket_id')
    if not ticket_id:
        flash('请选择要退的票', 'error')
        return redirect(url_for('tickets.search_person'))
    
    db = get_db()
    success, message = db.refund_ticket(ticket_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('tickets.search_person')) 

@bp.route('/change_ticket', methods=['GET', 'POST'])
@login_required
def change_ticket():
    """改签处理"""
    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id')
        new_train_id = request.form.get('new_train_id')
        
        if not all([ticket_id, new_train_id]):
            flash('请选择要改签的车票和目标车次', 'error')
            return redirect(url_for('tickets.search_person'))
        
        db = get_db()
        success, message = db.change_ticket(ticket_id, new_train_id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('tickets.search_person'))
    
    # GET 请求显示改签页面
    ticket_id = request.args.get('ticket_id')
    if not ticket_id:
        flash('请选择要改签的车票', 'error')
        return redirect(url_for('tickets.search_person'))
    
    db = get_db()
    # 获取原车票信息
    ticket = db.get_ticket_info(ticket_id)
    # 获取可改签的车次列表
    available_trains = db.search_trains(
        departure=ticket['departure'],
        destination=ticket['destination']
    ) if ticket else []
    
    return render_template('tickets/change_ticket.html',
                         ticket=ticket,
                         available_trains=available_trains) 