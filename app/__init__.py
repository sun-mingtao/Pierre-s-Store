import os

from flask import Flask

from config import Config
from app.db import DatabaseError, close_connection


def create_app():
    """Flask 应用工厂函数"""

    # 这是搭建 Flask 服务的第一步。生成的 app 对象包含了路由映射、配置管理、请求处理等 Web 应用的所有核心功能。
    app = Flask(__name__)

    # 将数据库配置加载到 Flask 应用实例中
    # 将 config.py 中的环境变量（如 DB_HOST、DB_USER）读取到 Flask 的 app.config 字典中。此时没有任何数据库连接被建立。
    app.config.from_object(Config)

    # 注册一个钩子：每次请求结束时自动执行 close_connection 函数
    # 这个函数会关闭数据库连接，确保资源得到正确释放，避免连接泄漏。
    app.teardown_appcontext(close_connection)

    # 注册全局数据库错误处理器
    @app.errorhandler(DatabaseError)
    def handle_database_error(error):
        from flask import jsonify
        return jsonify({"ok": False, "message": f"数据库操作失败：{error}"}), 500

    # 引入蓝图
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    """
    Flask App (app)
    ├── auth_bp 蓝图 (auth.py)     →  负责：登录、注册、登出
    │     /auth                    →  登录页面
    │     /api/login               →  登录接口
    │     /api/register            →  注册接口
    │     /api/logout              →  登出接口
    │     /api/me                  →  获取当前用户
    │
    └── main_bp 蓝图 (main.py)    →  负责：商店、仓库、账单、管理
            /shop                    →  商店页面
            /warehouse               →  仓库页面
            /api/seeds               →  种子列表
            /api/buy                 →  购买
            /api/sell                →  出售
            /api/inventory           →  库存
            /api/logs                →  账单
            /api/recommend           →  智能推荐
            /api/admin/seeds         →  管理员操作
            /pictures/<filename>     →  图片文件
    """

    # 注册蓝图到应用
    # 只有通过 register_blueprint 将蓝图注册到 app 上，蓝图内部定义的路由、视图函数、错误处理等才会真正生效。
    app.register_blueprint(main_bp) # 页面 + 核心 API
    app.register_blueprint(auth_bp) # 认证蓝图：登录注册

    return app
