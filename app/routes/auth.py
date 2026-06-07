
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

# 用于用户认证和权限控制
from app.models.user import current_user, login_required, public_user, api_error 
from app.db import select_one, execute

# 创建认证蓝图，用于将本文件中的所有路由注册到 Flask 应用中
# 在 __init__.py 中通过 app.register_blueprint(auth_bp) 挂载
auth_bp = Blueprint("auth", __name__)


# ─── 认证页面 ────────────────────────────────────────────

# 登录/注册页面 → templates/auth.html
# 前端初始化：app.js → bindAuth()
# 功能：用户登录和注册
# 已登录用户访问会被重定向到商店页
@auth_bp.route("/auth")
def auth_page():
    # 判断用户是否已经登录（即 session 中是否存在 user_id）
    if session.get("user_id"):
        return redirect(url_for("main.shop_page")) # 模板需要用户数据来渲染页面，需要传入 user=current_user()
    # 如果未登录，则渲染登录/注册页面 auth.html
    return render_template("auth.html")


# ─── 认证 API ────────────────────────────────────────────

# 注册 API
# 前端调用：app.js → bindAuth() 中的注册表单提交
#   填写用户名、密码、角色 → 点击注册 → POST /api/register { username, password, role }
#   注册成功后前端自动切换到登录标签页
# 业务流程：校验字段 → 检查用户名是否重复 → 密码哈希 → 插入 users 表
@auth_bp.route("/api/register", methods=["POST"])
def register():
    # 从请求体中解析 JSON 数据，得到一个 Python 字典
    data = request.get_json(force=True)

    # 从字典中提取用户名、密码和角色，并进行基本的验证
    username = (data.get("username") or "").strip()   # 用户名，去除首尾空格
    password = data.get("password") or ""             # 密码
    role = data.get("role") or "player"               # 角色，默认为玩家
    if not username or len(username) > 50:
        return api_error("用户名不能为空，且不能超过 50 个字符。")
    if len(password) < 4:
        return api_error("密码至少需要 4 位。")
    if role not in {"owner", "player"}:
        return api_error("用户类型不合法。")
    
    # 检查用户名是否已存在
    exists = select_one("SELECT user_id FROM users WHERE username = %s", [username], ["user_id"])

    if exists:
        return api_error("该用户名已经存在。")
    
    # 根据角色设置初始金币：皮埃尔99999，玩家1000
    coins = 99999 if role == "owner" else 1000

    # 插入新用户到 users 表
    # generate_password_hash() 对密码进行哈希加密存储，避免明文存储
    execute(
        "INSERT INTO users (username, password, role, coins) VALUES (%s, %s, %s, %s)",
        [username, generate_password_hash(password), role, coins],
    )

    # 返回注册成功信息，前端会显示提示并切换到登录标签页
    return jsonify({"ok": True, "message": "注册成功，可以登录了。"})
    """
    返回的 JSON 结构：
    {
        "ok": true,
        "message": "注册成功，可以登录了。"
    }
    """


# 登录 API
# 前端调用：app.js → bindAuth() 中的登录表单提交
#   填写用户名、密码 → 点击登录 → POST /api/login { username, password }
#   登录成功后前端跳转到 /shop 页面
# 业务流程：查用户 → 校验密码 → 写入 session → 返回用户信息
# 密码校验兼容两种格式：明文（开发用）和哈希（生产用）
@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True) # 从请求中解析 JSON 数据，得到一个 Python 字典 data
    username = (data.get("username") or "").strip()   # 用户名
    password = data.get("password") or ""             # 密码

    # 根据用户名查询用户记录
    user = select_one(
        "SELECT user_id, username, password, role, coins FROM users WHERE username = %s",
        [username],
        ["user_id", "username", "password", "role", "coins"],
    )
    # 用户不存在
    if not user:
        return api_error("用户名或密码错误。", 401)

    # 密码校验：兼容明文和哈希两种格式
    stored = user["password"] or ""
    valid = stored == password   # 先尝试明文比对（开发环境方便测试）
    
    if not valid:
        try:
            valid = check_password_hash(stored, password)  # 再尝试哈希比对（生产环境）
        except ValueError:
            valid = False
    if not valid:
        return api_error("用户名或密码错误。", 401)

    # 登录成功：将 user_id 写入 session，后续请求通过 session 判断登录状态
    session["user_id"] = int(user["user_id"])
    # 返回用户信息（不含密码），前端可用于更新页面显示
    return jsonify({"ok": True, "user": public_user(user)})
    """
    返回的 JSON 结构：
    {
        "ok": true,
        "user": {
            "user_id": 1,            // 用户ID
            "username": "张三",       // 用户名
            "role": "player",        // 角色："owner"(皮埃尔) 或 "player"(玩家)
            "coins": 1000,           // 金币数量
            "role_label": "玩家"      // 角色中文标签："皮埃尔" 或 "玩家"
        }
    }
    """


# 登出 API
# 前端调用：app.js → bindGlobal() 中的登出按钮点击
#   点击页面右上角「登出」按钮 → POST /api/logout → 清除 session → 跳转到 /auth
@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()   # 清除 session 中的所有数据（包括 user_id），用户即处于未登录状态
    return jsonify({"ok": True})
    """
    返回的 JSON 结构：
    {
        "ok": true
    }
    """


# 获取当前登录用户信息 API
# 前端调用：页面加载时检查登录状态
#   GET /api/me → 返回当前登录用户的信息（不含密码）
# 如果 session 中没有 user_id（未登录），@login_required 会返回 401 错误
@auth_bp.route("/api/me")
@login_required
def me():
    return jsonify({"ok": True, "user": public_user(current_user())})
    """
    返回的 JSON 结构：
    {
        "ok": true,
        "user": {
            "user_id": 1,            // 用户ID
            "username": "张三",       // 用户名
            "role": "player",        // 角色："owner"(皮埃尔) 或 "player"(玩家)
            "coins": 1000,           // 金币数量
            "role_label": "玩家"      // 角色中文标签："皮埃尔" 或 "玩家"
        }
    }
    """

