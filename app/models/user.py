
from functools import wraps

from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import select_one, execute, int_value


# 用来统一返回错误信息
def api_error(message, status=400):
    return jsonify({"ok": False, "message": message}), status


# 获取当前登录用户信息
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return select_one(
        "SELECT user_id, username, role, coins FROM users WHERE user_id = %s",
        [uid]
    )


# 保护页面和接口（权限校验）
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return api_error("请先登录。", 401)
            return redirect(url_for("auth.auth_page"))
        return view(*args, **kwargs)
    return wrapped


# 该装饰器主要用于接口级别的权限拦截，确保某些特定的 API 接口或页面只能由具有 "owner" 角色的用户访问。
def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or user["role"] != "owner":
            return api_error("只有皮埃尔账号可以进行该操作。", 403)
        return view(*args, **kwargs)
    return wrapped

def public_user(user):
    """
    将用户数据转换为公开的字典格式，过滤掉敏感信息。
    
    Args:
        user (dict): 包含用户信息的字典，必须包含以下字段：
            - user_id: 用户ID
            - username: 用户名
            - role: 用户角色（'owner' 或其他）
            - coins: 用户金币数量
    
    Returns:
        dict: 包含公开用户信息的字典，包含以下字段：
            - user_id (int): 用户ID
            - username (str): 用户名
            - role (str): 用户角色
            - coins (int): 用户金币数量
            - role_label (str): 角色标签，'owner' 角色显示为 '皮埃尔'，其他显示为 '玩家'
    """
    return {
        "user_id": int_value(user["user_id"]),
        "username": user["username"],
        "role": user["role"],
        "coins": int_value(user["coins"]),
        "role_label": "皮埃尔" if user["role"] == "owner" else "玩家",
    }
