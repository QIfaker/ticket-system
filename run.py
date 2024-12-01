from app import create_app
from app.models import get_db
import os

app = create_app()

def init_database():
    """初始化数据库"""
    print("初始化数据库...")
    with app.app_context():
        db = get_db()
        db.create_tables()
    print("数据库初始化完成")

def test_database():
    """测试数据库功能"""
    with app.app_context():
        db = get_db()
        
        print("=== 数据库测试 ===")
        
        # 查看车次统计
        print("\n1. 车次统计:")
        stats = db.get_train_statistics()
        for stat in stats:
            print(f"类型: {stat[0]}, 数量: {stat[1]}, 平均票价: {stat[2]:.2f}, 总座位: {stat[3]}")
        
        # 查看销售统计
        print("\n2. 销售统计:")
        sales = db.get_daily_sales('2024-01-01')
        for sale in sales:
            print(f"车次: {sale[0]}, 路线: {sale[1]}->{sale[2]}, 售票数: {sale[3]}, 收入: {sale[4]}")
        
        # 查看余票
        print("\n3. 余票查询:")
        seats = db.get_available_seats('G100', '2024-01-01')
        if seats:
            print(f"车次: {seats[0]}, 路线: {seats[1]}->{seats[2]}, 余票: {seats[7]}")
        
        # 查看乘客订单
        print("\n4. 乘客订单:")
        orders = db.get_passenger_orders('110101199001011234')
        for order in orders:
            print(f"订单号: {order[0]}, 车次: {order[1]}, "
                  f"路线: {order[2]}->{order[3]}, 座位号: {order[6]}")

def run_server():
    """启动Web服务器"""
    print("\n=== 启动Web服务器 ===")
    print("请访问: http://127.0.0.1:8080")
    app.run(host='127.0.0.1', port=8080, debug=True)

if __name__ == '__main__':
    import sys
    
    # 确保目录存在
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'app', 'templates')
    static_dir = os.path.join(base_dir, 'app', 'static')
    
    for directory in [template_dir, static_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # 根据命令行参数决定运行模式
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            test_database()
        elif sys.argv[1] == 'init':
            init_database()
    else:
        # 确保数据库已初始化
        init_database()
        run_server() 