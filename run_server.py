import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000")) # 设置端口号
    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=True) # 设置了主机地址
    """
    1.当 app.run() 被调用后，程序会在这里“卡住”（阻塞）。内置服务器开始在一个无限循环中监听
    2.app.run() 启动服务器后，程序就处于“待命”状态。只有当用户在浏览器中访问你的网站（例如访问 http://127.0.0.1:5000/）时，代码才会继续“动”起来：
    3.Flask 接收到请求，根据请求的 URL（如 /）在路由表中查找。
    4.找到对应的视图函数（例如 main_bp 下的 index 函数）。
    5.如果视图函数中需要操作数据库，此时才会执行 app/db.py 中的 get_connection()，真正建立数据库连接。
    6.视图函数执行完毕，返回 HTML 或 JSON 数据给浏览器。
    7.请求结束，触发 teardown_appcontext，执行 close_connection 关闭本次请求的数据库连接。
    8.程序再次回到“待命”状态，等待下一个请求。
    """