
from decimal import Decimal
import pymysql
from flask import current_app, g
# 当客户端发来一个 HTTP 请求时，Flask 会自动创建并推入一个应用上下文，此时 g 对象也会被初始化。当这个 HTTP 请求处理完毕、响应返回给客户端后，Flask 会自动销毁该请求的应用上下文，g 里面绑定的所有属性都会被清空回收。

# 自定义异常类
# 当数据库操作失败时会抛出这个异常，便于在应用层统一捕获和处理数据库错误。
class DatabaseError(RuntimeError):
    pass

# 获取当前请求的数据库连接
def get_connection():
    """
    获取当前 Flask 请求上下文中的数据库连接。
    如果 g 对象中还没有连接，则创建一个新的 pymysql 连接并缓存到 g 中。
    这样同一个 HTTP 请求内的所有数据库操作都复用同一个连接，避免频繁建立/断开连接的开销。
    """
    if "db_conn" not in g:
        # 从 Flask 应用配置中读取数据库连接参数，创建一个新的 pymysql 连接，并将其存储在 g.db_conn 中。
        g.db_conn = pymysql.connect(
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor, # 返回字典格式而非元组
            autocommit=True, # 自动提交事务
        )
    return g.db_conn


# 请求结束时关闭数据库连接
def close_connection(exception):
    """
    Flask 应用上下文销毁时（即 HTTP 请求结束时）自动关闭数据库连接。
    通过 Flask 的 teardown_appcontext 钩子注册，确保连接不会泄漏。
    """
    conn = g.pop("db_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


# 核心 SQL 执行函数
def run_sql(sql, params=None, expect_rows=False, columns=None):
    """
    执行 SQL 语句并返回结果。
    参数:
        sql: SQL 语句模板，使用 %s 作为参数占位符。
        params: 参数列表，按顺序替换 SQL 中的 %s 占位符。
        expect_rows: 是否期望返回数据行。查询语句设为 True，增删改语句设为 False。
        columns: 可选的列名列表。如果提供，则用该列表作为结果字典的键；
                 如果省略，则自动从 cursor.description 中读取列名（推荐）。
    返回:
        如果 expect_rows=True，返回字典列表（每行一个字典）；
        如果 expect_rows=False，返回空列表。
    pymysql 的优势:
        - 参数化查询由 pymysql 内部处理，自动完成转义，彻底杜绝 SQL 注入。
        - 返回结果自动转换为 Python 原生类型（int、float、Decimal、datetime 等）。
        - 使用 DictCursor 直接返回字典格式，无需手动解析 TSV 文本。
    """

    # 获取数据库连接配置信息
    conn = get_connection()
    try:
        # 创建一个数据库游标（Cursor），用于执行 SQL 并接收结果。
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ()) # 默认传入一个空元组 ()，防止 execute 方法报错。

            # 如果是 INSERT、UPDATE、DELETE 等不需要返回数据集的操作（expect_rows=False），直接返回一个空列表，结束函数。
            if not expect_rows:
                return []

            rows = cursor.fetchall()
            """
            结果返回的是一个字典列表
            [
                {
                    "user_id": 1,
                    "username": "农场主",
                    "role": "玩家",
                    "coins": Decimal("500.00")
                },
                {
                    "user_id": 2,
                    "username": "皮埃尔",
                    "role": "皮埃尔",
                    "coins": Decimal("9999.00")
                }
            ]
            """

            # 如果调用者指定了列名，则用指定的列名重新构建字典；
            # 否则直接使用 DictCursor 返回的字典（已包含正确的列名）。
            if columns:
                return [
                    {col: row.get(col) for col in columns} for row in rows
                ]

            return rows

    except pymysql.MySQLError as exc:
        raise DatabaseError(str(exc)) from exc


# 这个函数 select_all 是对 run_sql 的封装，专门用于查询多条记录。设置 expect_rows=True 表示期望返回数据行。
def select_all(sql, params=None, columns=None):
    return run_sql(sql, params, expect_rows=True, columns=columns)


# 这个函数 select_one 是对 select_all 的进一步封装，专门用于查询单条记录。它调用 select_all 获取所有匹配的行，然后返回第一行（如果存在的话），否则返回 None。
def select_one(sql, params=None, columns=None):
    rows = select_all(sql, params, columns)
    return rows[0] if rows else None


# 这个函数 execute 是对 run_sql 的封装，专门用于执行不需要返回数据行的 SQL 语句（如 INSERT、UPDATE、DELETE）。设置 expect_rows=False 表示不期望返回数据行。
def execute(sql, params=None):
    run_sql(sql, params, expect_rows=False)


# int_value 先将值转换为浮点数再转换为整数，这样可以处理字符串形式的数字（如 "10.5"）。
def int_value(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


# 直接转换为浮点数。如果转换失败，则返回默认值
def float_value(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
