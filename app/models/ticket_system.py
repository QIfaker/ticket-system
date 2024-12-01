import sqlite3
from datetime import datetime
from flask import g

class TicketSystem:
    def __init__(self, database):
        self.database = database

    def get_db(self):
        """获取数据库连接"""
        if 'db' not in g:
            g.db = sqlite3.connect(self.database)
            g.db.row_factory = sqlite3.Row
        return g.db

    def close_db(self):
        """关闭数据库连接"""
        db = g.pop('db', None)
        if db is not None:
            db.close()

    def create_tables(self):
        """创建所需的表、索引和视图"""
        db = self.get_db()
        cursor = db.cursor()
        
        # 创建车次信息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trains (
            train_id TEXT PRIMARY KEY,     -- 车次编号
            departure TEXT,                -- 出发站
            destination TEXT,              -- 目的站
            departure_time TEXT,           -- 发车时间
            arrival_time TEXT,             -- 到达时间
            total_seats INTEGER,           -- 总座位数
            price REAL                     -- 票价
        )
        ''')
        
        # 创建车次查询索引
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_trains_departure 
        ON trains(departure)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_trains_destination 
        ON trains(destination)
        ''')
        
        # 创建车票订单表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id TEXT,                 -- 车次编号
            passenger_name TEXT,           -- 乘客姓名
            passenger_id TEXT,             -- 乘客身份证号
            seat_number INTEGER,           -- 座位号
            booking_time TEXT,             -- 订票时间
            status TEXT,                   -- 票状态(已售/已退)
            is_group BOOLEAN,              -- 是否团体票
            FOREIGN KEY (train_id) REFERENCES trains(train_id)
        )
        ''')
        
        # 创建订单查询索引
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tickets_passenger 
        ON tickets(passenger_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tickets_train 
        ON tickets(train_id)
        ''')
        
        # 创建销售统计视图
        cursor.execute('''
        CREATE VIEW IF NOT EXISTS sales_summary AS
        SELECT 
            t.train_id,
            tr.departure,
            tr.destination,
            COUNT(*) as tickets_sold,
            SUM(tr.price) as total_revenue,
            date(t.booking_time) as sale_date
        FROM tickets t
        JOIN trains tr ON t.train_id = tr.train_id
        WHERE t.status = '已售'
        GROUP BY t.train_id, date(t.booking_time)
        ''')
        
        # 创建余票查询视图
        cursor.execute('''
        CREATE VIEW IF NOT EXISTS available_tickets AS
        SELECT 
            t.train_id,
            t.departure,
            t.destination,
            t.departure_time,
            t.arrival_time,
            t.total_seats,
            t.price,
            t.total_seats - (
                SELECT COUNT(*) 
                FROM tickets tk 
                WHERE tk.train_id = t.train_id 
                AND tk.status = '已售'
            ) as available_seats
        FROM trains t
        ''')
        
        # 创建每日统计表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_statistics (
            date TEXT PRIMARY KEY,           -- 日期
            tickets_sold INTEGER,            -- 售票数量
            tickets_refunded INTEGER,        -- 退票数量
            total_revenue REAL,              -- 总收入
            total_refund REAL,              -- 退票金额
            created_at TEXT,                 -- 创建时间
            updated_at TEXT                  -- 更新时间
        )
        ''')
        
        # 创建月度统计表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_statistics (
            year_month TEXT PRIMARY KEY,     -- 年月(YYYY-MM)
            tickets_sold INTEGER,            -- 售票数量
            tickets_refunded INTEGER,        -- 退票数量
            total_revenue REAL,              -- 总收入
            total_refund REAL,              -- 退票金额
            avg_daily_sales REAL,           -- 日均销售
            peak_day TEXT,                  -- 销售峰值日
            peak_sales INTEGER,             -- 峰值销售量
            created_at TEXT,                 -- 创建时间
            updated_at TEXT                  -- 更新时间
        )
        ''')
        
        # 创建年度统计表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS yearly_statistics (
            year TEXT PRIMARY KEY,           -- 年份
            tickets_sold INTEGER,            -- 售票数量
            tickets_refunded INTEGER,        -- 退票数量
            total_revenue REAL,              -- 总收入
            total_refund REAL,              -- 退票金额
            avg_monthly_sales REAL,         -- 月均销售
            peak_month TEXT,                -- 销售峰值月
            peak_sales INTEGER,             -- 峰值销售量
            created_at TEXT,                 -- 创建时间
            updated_at TEXT                  -- 更新时间
        )
        ''')
        
        # 创建管理员账户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            real_name TEXT,               -- 真实姓名
            phone TEXT,                   -- 联系电话
            email TEXT,                   -- 电子邮箱
            last_login TEXT,             -- 最后登录时间
            created_at TEXT,             -- 创建时间
            status TEXT DEFAULT 'active'  -- 账户状态(active/disabled)
        )
        ''')
        
        # 创建普通用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            real_name TEXT,               -- 真实姓名
            id_number TEXT UNIQUE,        -- 身份证号
            phone TEXT,                   -- 联系电话
            email TEXT,                   -- 电子邮箱
            last_login TEXT,             -- 最后登录时间
            created_at TEXT,             -- 创建时间
            status TEXT DEFAULT 'active'  -- 账户状态(active/pending/disabled)
        )
        ''')
        
        # 添加默认管理员账户
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO admin_users 
            (username, password, real_name, created_at, status) 
            VALUES (?, ?, ?, datetime('now'), 'active')
            ''', ('admin', 'admin123', '系统管理员'))
            db.commit()
            print("默认管理员账户创建成功")
        except sqlite3.Error as e:
            print(f"创建管理员账户失败: {e}")

        # 添加统计更新触发器
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_statistics_after_sale
        AFTER INSERT ON tickets
        WHEN NEW.status = '已售'
        BEGIN
            -- 更新每日统计
            INSERT OR REPLACE INTO daily_statistics 
            (date, tickets_sold, total_revenue, created_at, updated_at)
            VALUES (
                date(NEW.booking_time),
                COALESCE((SELECT tickets_sold FROM daily_statistics 
                          WHERE date = date(NEW.booking_time)), 0) + 1,
                COALESCE((SELECT total_revenue FROM daily_statistics 
                          WHERE date = date(NEW.booking_time)), 0) + 
                (SELECT price FROM trains WHERE train_id = NEW.train_id),
                COALESCE((SELECT created_at FROM daily_statistics 
                          WHERE date = date(NEW.booking_time)), 
                         datetime('now')),
                datetime('now')
            );
            
            -- 更新月度统计
            INSERT OR REPLACE INTO monthly_statistics 
            (year_month, tickets_sold, total_revenue, created_at, updated_at)
            VALUES (
                strftime('%Y-%m', NEW.booking_time),
                COALESCE((SELECT tickets_sold FROM monthly_statistics 
                          WHERE year_month = strftime('%Y-%m', NEW.booking_time)), 0) + 1,
                COALESCE((SELECT total_revenue FROM monthly_statistics 
                          WHERE year_month = strftime('%Y-%m', NEW.booking_time)), 0) + 
                (SELECT price FROM trains WHERE train_id = NEW.train_id),
                COALESCE((SELECT created_at FROM monthly_statistics 
                          WHERE year_month = strftime('%Y-%m', NEW.booking_time)), 
                         datetime('now')),
                datetime('now')
            );
            
            -- 更新年度统计
            INSERT OR REPLACE INTO yearly_statistics 
            (year, tickets_sold, total_revenue, created_at, updated_at)
            VALUES (
                strftime('%Y', NEW.booking_time),
                COALESCE((SELECT tickets_sold FROM yearly_statistics 
                          WHERE year = strftime('%Y', NEW.booking_time)), 0) + 1,
                COALESCE((SELECT total_revenue FROM yearly_statistics 
                          WHERE year = strftime('%Y', NEW.booking_time)), 0) + 
                (SELECT price FROM trains WHERE train_id = NEW.train_id),
                COALESCE((SELECT created_at FROM yearly_statistics 
                          WHERE year = strftime('%Y', NEW.booking_time)), 
                         datetime('now')),
                datetime('now')
            );
        END;
        ''')
        
        # 添加退票统计触发器
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_statistics_after_refund
        AFTER UPDATE ON tickets
        WHEN NEW.status = '已退' AND OLD.status = '已售'
        BEGIN
            -- 更新每日统计
            UPDATE daily_statistics 
            SET tickets_refunded = COALESCE(tickets_refunded, 0) + 1,
                total_refund = COALESCE(total_refund, 0) + 
                              (SELECT price FROM trains WHERE train_id = NEW.train_id),
                updated_at = datetime('now')
            WHERE date = date(NEW.booking_time);
            
            -- 更新月度统计
            UPDATE monthly_statistics 
            SET tickets_refunded = COALESCE(tickets_refunded, 0) + 1,
                total_refund = COALESCE(total_refund, 0) + 
                              (SELECT price FROM trains WHERE train_id = NEW.train_id),
                updated_at = datetime('now')
            WHERE year_month = strftime('%Y-%m', NEW.booking_time);
            
            -- 更新年度统计
            UPDATE yearly_statistics 
            SET tickets_refunded = COALESCE(tickets_refunded, 0) + 1,
                total_refund = COALESCE(total_refund, 0) + 
                              (SELECT price FROM trains WHERE train_id = NEW.train_id),
                updated_at = datetime('now')
            WHERE year = strftime('%Y', NEW.booking_time);
        END;
        ''')
        
        # 添加测试数据
        try:
            # 添加车次数据
            test_trains = [
                ('G100', '北京', '上海', '08:00', '13:00', 400, 553.0),
                ('G200', '广州', '武汉', '09:30', '14:30', 350, 463.0),
                ('D100', '深圳', '厦门', '10:00', '16:00', 300, 363.0),
                ('K100', '西安', '成都', '20:00', '08:00', 200, 263.0),
                ('G300', '北京', '广州', '08:30', '16:30', 400, 863.0),
                ('G101', '上海', '北京', '09:00', '14:00', 400, 553.0),
                ('G201', '武汉', '广州', '10:30', '15:30', 350, 463.0),
                ('D101', '厦门', '深圳', '11:00', '17:00', 300, 363.0),
                ('K101', '成都', '西安', '21:00', '09:00', 200, 263.0),
                ('G301', '广州', '北京', '09:30', '17:30', 400, 863.0),
                ('D200', '南京', '杭州', '08:30', '10:30', 300, 213.0),
                ('D201', '杭州', '南京', '09:30', '11:30', 300, 213.0),
                ('G400', '天津', '济南', '10:00', '12:00', 350, 323.0),
                ('G401', '济南', '天津', '13:00', '15:00', 350, 323.0),
                ('K200', '长沙', '贵阳', '19:00', '06:00', 250, 243.0)
            ]
            cursor.executemany('''
            INSERT OR IGNORE INTO trains 
            (train_id, departure, destination, departure_time, arrival_time, 
             total_seats, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', test_trains)
            
            # 添加测试用户数据
            test_users = [
                ('user1', 'pass123', '张三', '110101199001011234', '13800138001', 'zhang@example.com'),
                ('user2', 'pass123', '李四', '110101199001011235', '13800138002', 'li@example.com'),
                ('user3', 'pass123', '王五', '110101199001011236', '13800138003', 'wang@example.com'),
                ('user4', 'pass123', '赵六', '110101199001011237', '13800138004', 'zhao@example.com'),
                ('test', 'test123', '测试用户', '110101199001011238', '13800138005', 'test@example.com')
            ]
            cursor.executemany('''
            INSERT OR IGNORE INTO users 
            (username, password, real_name, id_number, phone, email, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 'active')
            ''', test_users)
            
            # 添加测试订单数据
            test_tickets = [
                ('G100', '张三', '110101199001011234', 1, '2024-01-01 08:00:00', '已售', False),
                ('G100', '李四', '110101199001011235', 2, '2024-01-01 08:05:00', '已售', False),
                ('G200', '王五', '110101199001011236', 1, '2024-01-01 09:00:00', '已售', False),
                ('G200', '赵六', '110101199001011237', 2, '2024-01-01 09:10:00', '已退', False),
                ('D100', '张三', '110101199001011234', 5, '2024-01-02 10:00:00', '已售', False),
                ('G300', '李四', '110101199001011235', 8, '2024-01-02 08:30:00', '已售', False),
                ('G101', '王五', '110101199001011236', 12, '2024-01-02 09:00:00', '已退', False),
                ('D200', '赵六', '110101199001011237', 15, '2024-01-03 08:30:00', '已售', False),
                ('G400', '张三', '110101199001011234', 20, '2024-01-03 10:00:00', '已售', False),
                ('K200', '李四', '110101199001011235', 25, '2024-01-03 19:00:00', '已售', False)
            ]
            cursor.executemany('''
            INSERT OR IGNORE INTO tickets 
            (train_id, passenger_name, passenger_id, seat_number, booking_time, 
             status, is_group)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', test_tickets)
            
            # 添加管理员账���
            cursor.execute('''
            INSERT OR IGNORE INTO admin_users 
            (username, password, real_name, phone, email, created_at, status)
            VALUES 
            ('admin', 'admin123', '系统管理员', '13900000000', 'admin@system.com', datetime('now'), 'active'),
            ('manager', 'manager123', '销售经理', '13900000001', 'manager@system.com', datetime('now'), 'active')
            ''')
            
            db.commit()
            print("测试数据添加成功")
            
        except sqlite3.Error as e:
            print(f"添加测试数据失败: {e}")

    def add_train(self, train_id, departure, destination, departure_time, 
                  arrival_time, total_seats, price):
        """添加新车次"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            INSERT INTO trains VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (train_id, departure, destination, departure_time, 
                 arrival_time, total_seats, price))
            db.commit()
            return True
        except sqlite3.Error as e:
            print(f"添加车次失败: {e}")
            return False

    def search_trains(self, departure=None, destination=None):
        """查询车次"""
        query = "SELECT * FROM trains WHERE 1=1"
        params = []
        
        if departure:
            query += " AND departure = ?"
            params.append(departure)
        if destination:
            query += " AND destination = ?"
            params.append(destination)
            
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
            return []

    def book_ticket(self, train_id, passenger_name, passenger_id, is_group=False):
        """订票功能"""
        try:
            # 检查余票
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            SELECT total_seats, 
                   (SELECT COUNT(*) FROM tickets 
                    WHERE train_id = ? AND status = '已售') as sold_seats 
            FROM trains WHERE train_id = ?
            ''', (train_id, train_id))
            
            result = cursor.fetchone()
            if not result:
                return False, "车次不存在"
                
            total_seats, sold_seats = result
            if sold_seats >= total_seats:
                return False, "无余票"
            
            # 分配座位号
            seat_number = sold_seats + 1
            
            # 创建订单
            cursor.execute('''
            INSERT INTO tickets 
            (train_id, passenger_name, passenger_id, seat_number, 
             booking_time, status, is_group)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (train_id, passenger_name, passenger_id, seat_number,
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '已售', is_group))
            
            db.commit()
            return True, f"订票成功，座位号: {seat_number}"
            
        except sqlite3.Error as e:
            print(f"订票失败: {e}")
            return False, "订票失败"

    def refund_ticket(self, ticket_id):
        """退票功能"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            UPDATE tickets SET status = '已退' 
            WHERE ticket_id = ? AND status = '已售'
            ''', (ticket_id,))
            
            if cursor.rowcount > 0:
                db.commit()
                return True, "退票成功"
            return False, "退票失败，票不存在或已退"
            
        except sqlite3.Error as e:
            print(f"退票失败: {e}")
            return False, "退票失败"

    def update_train_price(self, train_id, new_price):
        """更新票价"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            UPDATE trains SET price = ? WHERE train_id = ?
            ''', (new_price, train_id))
            
            if cursor.rowcount > 0:
                db.commit()
                return True, "票价更新成功"
            return False, "更新失败，车次不存在"
            
        except sqlite3.Error as e:
            print(f"更新票价失败: {e}")
            return False, "更新票价失败"

    def generate_sales_report(self, start_date, end_date):
        """生成销售报表"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            SELECT t.train_id, 
                   COUNT(*) as tickets_sold,
                   SUM(tr.price) as total_amount
            FROM tickets t
            JOIN trains tr ON t.train_id = tr.train_id
            WHERE t.status = '已售'
            AND date(t.booking_time) BETWEEN ? AND ?
            GROUP BY t.train_id
            ''', (start_date, end_date))
            
            return cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f"生成报表失败: {e}")
            return []

    def authenticate_user(self, username, password, is_admin=False):
        """验证用户登录"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            
            if is_admin:
                cursor.execute('''
                SELECT username, real_name, status
                FROM admin_users 
                WHERE username = ? AND password = ?
                ''', (username, password))
            else:
                cursor.execute('''
                SELECT username, real_name, status
                FROM users 
                WHERE username = ? AND password = ?
                ''', (username, password))
            
            user = cursor.fetchone()
            
            if user:
                # 检查用户状态
                if user[2] != 'active':
                    return None
                
                # 更新最后登录时间
                table = 'admin_users' if is_admin else 'users'
                cursor.execute(f'''
                UPDATE {table}
                SET last_login = datetime('now')
                WHERE username = ?
                ''', (username,))
                db.commit()
            
            return user
            
        except sqlite3.Error as e:
            print(f"验证用户失败: {e}")
            return None

    def register_user(self, username, password, real_name, id_number, phone=None, email=None):
        """注册新用户"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            
            # 添加 created_at 和 status 字段
            cursor.execute('''
            INSERT INTO users 
            (username, password, real_name, id_number, phone, email, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 'active')
            ''', (username, password, real_name, id_number, phone, email))
            
            db.commit()
            return True, "注册成功"
            
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                return False, "用户名已存在"
            elif 'id_number' in str(e):
                return False, "身证号已被注册"
            return False, "注册失败"
        except sqlite3.Error as e:
            print(f"注册用户失败: {e}")
            return False, "注册失败"

    def get_user_info(self, username, is_admin=False):
        """获取用户信息"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            
            if is_admin:
                cursor.execute('''
                SELECT username, password, real_name, phone, email, last_login, created_at, status 
                FROM admin_users WHERE username = ?
                ''', (username,))
            else:
                cursor.execute('''
                SELECT username, password, real_name, phone, id_number, email, last_login, created_at, status 
                FROM users WHERE username = ?
                ''', (username,))
            
            return cursor.fetchone()
            
        except sqlite3.Error as e:
            print(f"获取用户信息失败: {e}")
            return None

    def update_user_info(self, username, data, is_admin=False):
        """更新用户信息"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            
            fields = []
            values = []
            for key, value in data.items():
                if value is not None:
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if not fields:
                return False, "没有要更新的数据"
            
            values.append(username)
            table = 'admin_users' if is_admin else 'users'
            query = f'''
            UPDATE {table}
            SET {', '.join(fields)}
            WHERE username = ?
            '''
            
            cursor.execute(query, values)
            db.commit()
            
            return True, "更新成功"
            
        except sqlite3.Error as e:
            print(f"更新用户信息失败: {e}")
            return False, "更新失败"

    def get_train_statistics(self):
        """获取车次统计信息"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            SELECT 
                train_type,
                COUNT(*) as train_count,
                AVG(price) as avg_price,
                SUM(total_seats) as total_capacity
            FROM trains
            GROUP BY train_type
            ''')
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
            return []

    def get_daily_sales(self, date):
        """获取指定日期的销售统计"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            SELECT * FROM sales_summary
            WHERE sale_date = ?
            ''', (date,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
            return []

    def get_available_seats(self, train_id, date):
        """获取指定车次的余票信息"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            SELECT * FROM available_tickets
            WHERE train_id = ?
            ''', (train_id,))
            return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
            return None

    def get_passenger_orders(self, passenger_id):
        """获取乘客的订票记录"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            SELECT 
                t.ticket_id,
                t.train_id,
                tr.departure,
                tr.destination,
                tr.departure_time,
                tr.arrival_time,
                t.seat_number,
                t.booking_time,
                t.status,
                tr.price
            FROM tickets t
            JOIN trains tr ON t.train_id = tr.train_id
            WHERE t.passenger_id = ?
            ORDER BY t.booking_time DESC
            ''', (passenger_id,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
            return []

    def get_statistics(self, period='daily', start_date=None, end_date=None):
        """获取统计数据
        period: daily/monthly/yearly
        """
        try:
            db = self.get_db()
            cursor = db.cursor()
            
            if period == 'daily':
                table = 'daily_statistics'
                date_format = '%Y-%m-%d'
            elif period == 'monthly':
                table = 'monthly_statistics'
                date_format = '%Y-%m'
            else:
                table = 'yearly_statistics'
                date_format = '%Y'
            
            query = f'SELECT * FROM {table}'
            params = []
            
            if start_date and end_date:
                query += ' WHERE date >= ? AND date <= ?'
                params.extend([start_date, end_date])
            
            query += ' ORDER BY date DESC'
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f"查询统计数据失败: {e}")
            return []

    def search_tickets_by_person(self, name=None, id_number=None):
        """根据姓名或身份证号查询车票"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            
            query = '''
            SELECT 
                t.ticket_id,
                t.train_id,
                tr.departure,
                tr.destination,
                tr.departure_time,
                tr.arrival_time,
                t.seat_number,
                t.booking_time,
                t.status,
                tr.price,
                t.passenger_name,
                t.passenger_id
            FROM tickets t
            JOIN trains tr ON t.train_id = tr.train_id
            WHERE 1=1
            '''
            params = []
            
            if name:
                query += " AND t.passenger_name LIKE ?"
                params.append(f"%{name}%")
            if id_number:
                query += " AND t.passenger_id = ?"
                params.append(id_number)
                
            query += " ORDER BY t.booking_time DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
            return []

    def change_ticket(self, ticket_id, new_train_id):
        """改签功能"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            
            # 检查原票是否存在且为已售状态
            cursor.execute('''
            SELECT t.*, tr.price as old_price
            FROM tickets t
            JOIN trains tr ON t.train_id = tr.train_id
            WHERE t.ticket_id = ? AND t.status = '已售'
            ''', (ticket_id,))
            old_ticket = cursor.fetchone()
            
            if not old_ticket:
                return False, "原车票不存在或已退票"
            
            # 检查新车次是否存在且有余票
            cursor.execute('''
            SELECT total_seats, 
                   (SELECT COUNT(*) FROM tickets 
                    WHERE train_id = ? AND status = '已售') as sold_seats,
                   price as new_price
            FROM trains WHERE train_id = ?
            ''', (new_train_id, new_train_id))
            
            new_train = cursor.fetchone()
            if not new_train:
                return False, "目标车次不存在"
            
            if new_train[0] <= new_train[1]:
                return False, "目标车次无余票"
            
            # 计算座位号
            new_seat = new_train[1] + 1
            
            # 计算差价
            price_diff = new_train[2] - old_ticket['old_price']
            
            # 开始改签事务
            cursor.execute('BEGIN TRANSACTION')
            try:
                # 将原票改为已退状态
                cursor.execute('''
                UPDATE tickets SET status = '已退'
                WHERE ticket_id = ?
                ''', (ticket_id,))
                
                # 创建新票
                cursor.execute('''
                INSERT INTO tickets 
                (train_id, passenger_name, passenger_id, seat_number, 
                 booking_time, status, is_group)
                VALUES (?, ?, ?, ?, ?, '已售', ?)
                ''', (new_train_id, old_ticket['passenger_name'], 
                     old_ticket['passenger_id'], new_seat,
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                     old_ticket['is_group']))
                
                cursor.execute('COMMIT')
                
                message = "改签成功"
                if price_diff > 0:
                    message += f"，需补差价：¥{price_diff:.2f}"
                elif price_diff < 0:
                    message += f"，可退差价：¥{-price_diff:.2f}"
                    
                return True, message
                
            except sqlite3.Error:
                cursor.execute('ROLLBACK')
                raise
                
        except sqlite3.Error as e:
            print(f"改签失败: {e}")
            return False, "改签失败，请稍后重试"

    def get_ticket_info(self, ticket_id):
        """获取车票详细信息"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute('''
            SELECT 
                t.ticket_id,
                t.train_id,
                t.passenger_name,
                t.passenger_id,
                t.seat_number,
                t.booking_time,
                t.status,
                t.is_group,
                tr.departure,
                tr.destination,
                tr.departure_time,
                tr.arrival_time,
                tr.price
            FROM tickets t
            JOIN trains tr ON t.train_id = tr.train_id
            WHERE t.ticket_id = ?
            ''', (ticket_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'ticket_id': result[0],
                    'train_id': result[1],
                    'passenger_name': result[2],
                    'passenger_id': result[3],
                    'seat_number': result[4],
                    'booking_time': result[5],
                    'status': result[6],
                    'is_group': result[7],
                    'departure': result[8],
                    'destination': result[9],
                    'departure_time': result[10],
                    'arrival_time': result[11],
                    'price': result[12]
                }
            return None
            
        except sqlite3.Error as e:
            print(f"获取车票信息失败: {e}")
            return None
    