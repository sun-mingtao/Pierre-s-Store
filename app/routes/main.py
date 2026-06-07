import os

from flask import Blueprint, jsonify, redirect, render_template, send_from_directory, session, url_for, request

from app.models.user import current_user, login_required, owner_required, api_error
from app.models.seed import (
    seed_columns, get_seed, normalize_seed, validate_seed_payload,
    seed_select_sql, expected_harvests, optimize_plan, SEASONS,
)
from app.db import select_one, select_all, execute, get_connection, int_value, float_value

# 创建 Flask 蓝图（Blueprint），用于将本文件中的所有路由注册到 Flask 应用中
# 蓝图相当于一个模块化的路由组，在 __init__.py 中通过 app.register_blueprint(main_bp) 挂载
main_bp = Blueprint("main", __name__)


# ─── 页面路由 ────────────────────────────────────────────
# 页面路由负责返回 HTML 页面，而非 JSON 数据
# 每个页面对应一个模板文件（templates 目录下）和一个前端 JS 初始化逻辑

# 首页重定向：根据登录状态跳转到不同页面
# 已登录 → /shop（商店页）  未登录 → /auth（登录/注册页）
@main_bp.route("/")
def index():
    return redirect(url_for("main.shop_page") if session.get("user_id") else url_for("auth.auth_page"))
    

# 商店页面 → templates/shop.html
# 前端初始化：app.js → bindFilters(loadShop) + bindShopActions() + loadShop()
# 功能：展示所有上架种子，支持购买操作
@main_bp.route("/shop")
@login_required  # 判断用户是否登录的装饰器，未登录会被重定向到登录页面
def shop_page():
    return render_template("shop.html", user=current_user())


# 仓库（背包）页面 → templates/warehouse.html
# 前端初始化：app.js → bindFilters(loadInventory) + bindInventoryActions() + loadInventory()
# 功能：展示用户持有的种子库存，支持出售操作
@main_bp.route("/warehouse")
@login_required
def warehouse_page():
    return render_template("warehouse.html", user=current_user())


# 种植规划页面 → templates/planner.html
# 前端初始化：app.js → bindPlanner()
# 功能：输入天数和预算，推荐最优种植方案
@main_bp.route("/planner")
@login_required
def planner_page():
    return render_template("planner.html", user=current_user())


# 交易流水（账单）页面 → templates/billing.html
# 前端初始化：app.js → bindBills() + loadBills()
# 功能：展示购买/出售的交易记录，支持筛选和搜索
@main_bp.route("/billing")
@login_required
def billing_page():
    return render_template("billing.html", user=current_user())


# 商品管理页面 → templates/admin.html（仅皮埃尔角色可访问）
# 前端初始化：app.js → bindFilters(loadAdmin) + bindAdminActions() + loadAdmin()
# 功能：添加/编辑/删除种子，上架/下架切换
# 权限控制：非 owner 角色访问会被重定向到商店页
@main_bp.route("/admin")
@login_required
def admin_page():
    user = current_user()
    if user["role"] != "owner":
        return redirect(url_for("main.shop_page"))
    return render_template("admin.html", user=user)


# 静态图片文件服务
# 前端调用：<img src="/pictures/xxx.png"> → 返回 app/pictures/ 目录下的图片文件
# <path:filename> 匹配任意路径，支持子目录
@main_bp.route("/pictures/<path:filename>")
def picture_file(filename):
    from flask import current_app
    return send_from_directory(os.path.join(current_app.root_path, "pictures"), filename)


# ─── 种子 API ────────────────────────────────────────────

# 获取种子列表 API
# 前端调用：app.js → loadAdmin() / loadShop()
#   loadAdmin():  GET /api/seeds?season=&q=  → 管理页加载所有种子（含已下架）
#   loadShop():   GET /api/seeds?season=春季&q=  → 商店页加载上架种子
# 权限差异：皮埃尔(owner)能看到已下架种子，玩家(player)只能看到上架的
@main_bp.route("/api/seeds")
@login_required
def seeds():
    user = current_user()

    # seed_select_sql 根据是否包含已下架种子，动态构建 SQL 查询语句
    # 皮埃尔角色 → include_unavailable=True，查询所有种子
    # 玩家角色   → include_unavailable=False，只查询 is_available=1 的种子
    sql, params = seed_select_sql(include_unavailable = user["role"]=="owner")

    # seed_columns() 返回种子相关列名列表，用于将查询结果映射为字典
    # normalize_seed(row) 将数据库原始行转换为规范化的字典（处理 None、类型不一致等问题）
    rows = select_all(sql, params, seed_columns())

    return jsonify({"ok": True, "seeds": [normalize_seed(row) for row in rows]})


# 购买种子 API
# 前端调用：app.js → bindShopActions() 中的两种购买方式
#   单次购买：点击卡片上的「购买」按钮 → POST /api/buy { product_id, quantity }
#   批量购买：点击底栏「购买选中」→ buySelectedSeeds() → 串行循环调用 POST /api/buy
# 业务流程：校验权限 → 校验商品 → 校验余额 → 扣钱 → 加库存
# 注意：对 inventory 表的 INSERT/UPDATE 会触发 MySQL 触发器自动写入购买日志到 logs 表
@main_bp.route("/api/buy", methods=["POST"])
@login_required
def buy_seed():
    from app.models.user import public_user
    user = current_user()

    # 权限检查：只有玩家能购买，皮埃尔角色不能买
    if user["role"] != "player":
        return api_error("皮埃尔账号不能购买种子，请使用玩家账号。")
    
    # 解析请求参数
    data = request.get_json(force=True)
    product_id = int_value(data.get("product_id"))   # 商品ID
    quantity = int_value(data.get("quantity"))        # 购买数量

    # 校验数量必须是正整数
    if product_id <= 0 or quantity <= 0:
        return api_error("购买数量必须是正整数。")
    
    # 查商品是否存在且处于上架状态
    seed = get_seed(product_id)
    if not seed or int_value(seed["is_available"]) != 1:
        return api_error("该商品不存在或已下架。")
    
    # 计算总价并校验金币是否足够
    unit_price = float_value(seed["seed_buy_price"])   # 种子购买单价
    total = unit_price * quantity                       # 总价 = 单价 × 数量
    coins = int_value(user["coins"])                   # 用户当前金币
    if total > coins:
        return api_error("金币不足，无法购买。")
    
    # 扣除用户金币
    execute("UPDATE users SET coins = coins - %s WHERE user_id = %s", [total, user["user_id"]])

    # 查询仓库中是否已有该种子（决定是新增还是累加）
    inv = select_one(
        "SELECT inventory_id, quantity FROM inventory WHERE user_id = %s AND product_id = %s",
        [user["user_id"], product_id],
        ["inventory_id", "quantity"],
    )
    # 情况1：仓库里已有这个种子 → 数量累加
    # 触发 trg_inventory_after_update → 自动写入 buy 日志（记录增量）
    if inv:
        execute("UPDATE inventory SET quantity = quantity + %s WHERE inventory_id = %s", [quantity, inv["inventory_id"]])
    # 情况2：仓库里没有这个种子 → 新增一条库存记录
    # 触发 trg_inventory_after_insert → 自动写入 buy 日志（记录全量）
    else:
        execute(
            "INSERT INTO inventory (user_id, product_id, quantity) VALUES (%s, %s, %s)",
            [user["user_id"], product_id, quantity],
        )
    # 返回最新用户信息，前端用于更新页面上的金币显示
    return jsonify({"ok": True, "message": "购买成功。", "user": public_user(current_user())})


# 出售种子 API
# 前端调用：app.js → bindInventoryActions()
#   点击背包卡片上的「出售」按钮 → POST /api/sell { product_id, quantity }
# 业务流程：校验权限 → 校验库存 → 扣库存 → 加钱
# 注意：对 inventory 表的 UPDATE 会触发 trg_inventory_after_update → 自动写入 sell 日志
# 出售单价使用 seed_sell_price（种子卖出价），而非 seed_buy_price（种子购买价），形成差价
@main_bp.route("/api/sell", methods=["POST"])
@login_required
def sell_seed():
    from app.models.user import public_user
    user = current_user()

    # 权限检查：只有玩家能出售，皮埃尔角色不能卖
    if user["role"] != "player":
        return api_error("皮埃尔账号不能出售背包中的种子。")
    data = request.get_json(force=True)

    # 解析请求参数
    product_id = int_value(data.get("product_id"))   # 商品ID
    quantity = int_value(data.get("quantity"))        # 出售数量
    if product_id <= 0 or quantity <= 0:
        return api_error("出售数量必须是正整数。")
    
    # 查商品信息和当前用户的库存
    seed = get_seed(product_id)
    inv = select_one(
        "SELECT inventory_id, quantity FROM inventory WHERE user_id = %s AND product_id = %s",
        [user["user_id"], product_id],
        ["inventory_id", "quantity"],
    )

    # 校验：商品必须存在，且库存数量必须足够
    if not seed or not inv or int_value(inv["quantity"]) < quantity:
        return api_error("仓库库存不足。")
    
    # 扣库存 + 加钱（注意顺序和购买相反：先减库存再加金币）
    unit_price = float_value(seed["seed_sell_price"])   # 按 seed_sell_price（种子卖出价）计算
    # 减少 inventory 数量 → 触发 trg_inventory_after_update → 自动写入 sell 日志（记录减量）
    execute("UPDATE inventory SET quantity = quantity - %s WHERE inventory_id = %s", [quantity, inv["inventory_id"]])
    # 增加用户金币
    execute("UPDATE users SET coins = coins + %s WHERE user_id = %s", [unit_price * quantity, user["user_id"]])

    # 返回最新用户信息，前端用于更新页面上的金币显示，并重新加载库存列表
    return jsonify({"ok": True, "message": "出售成功。", "user": public_user(current_user())})

# 仓库（背包）列表 API
# 前端调用：app.js → loadInventory()
#   GET /api/inventory?season=春季&q=南瓜 → 加载仓库中当前用户的种子列表
# 与 /api/seeds 的区别：本接口查的是 inventory 表（用户拥有的种子），而非 seeds 表（在售种子）
# 返回数据额外包含 inventory_id 和 quantity 字段
@main_bp.route("/api/inventory")
@login_required
def inventory():
    user = current_user()

    # WHERE 条件：只查当前用户 + 数量>0
    where = ["i.user_id = %s", "i.quantity > 0"]
    params = [user["user_id"]]

    # 可选筛选条件：季节和搜索关键词
    season = request.args.get("season", "")   # 季节筛选
    q = (request.args.get("q") or "").strip()  # 搜索关键词（匹配种子名或作物名）
    if season:
        where.append("s.selling_season LIKE %s")
        params.append(f"%{season}%")
    if q:
        where.append("(s.name LIKE %s OR c.name LIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])

    # 三表联查：inventory（库存） JOIN seeds（种子） LEFT JOIN crops（作物）
    # 使用 LEFT JOIN crops 是因为种子可能没有关联的作物记录
    rows = select_all(
        f"""
        SELECT i.inventory_id, i.quantity,
               s.product_id, s.crop_id, s.name, s.image_url, s.description, s.selling_season,
               c.growth_time_single, c.growth_time_multiple, s.seed_buy_price,
               c.name as mature_crop_name, c.sell_price as mature_crop_price, c.harvest_type,
               s.is_available, s.seed_sell_price
        FROM inventory i
        JOIN seeds s ON i.product_id = s.product_id
        LEFT JOIN crops c ON s.crop_id = c.crop_id
        WHERE {' AND '.join(where)}
        ORDER BY FIELD(s.selling_season, '春季', '夏季', '秋季', '全年', '冬季'), s.name
        """,
        params,
        ["inventory_id", "quantity"] + seed_columns(),
    )
    items = []

    #  inventory_id（库存记录ID）和 quantity（持有数量）转为整数，添加到每个种子字典中返回给前端
    for row in rows:
        seed = normalize_seed(row)
        seed["inventory_id"] = int_value(row["inventory_id"])
        seed["quantity"] = int_value(row["quantity"])
        items.append(seed)

    return jsonify({"ok": True, "items": items})
    """
    返回的 JSON 结构：
    {
        "ok": true,
        "items": [
            {
            "product_id": 3,
            "name": "南瓜种子",
            "seed_buy_price": 100,
            "seed_sell_price": 50,
            "selling_season": "秋季",
            "quantity": 5,           // ← 仓库中持有5包
            "inventory_id": 12,
            ...
            },
            {
            "product_id": 7,
            "name": "草莓种子",
            "seed_sell_price": 110,
            "quantity": 2,           // ← 仓库中持有2包
            "inventory_id": 15,
            ...
            }
        ]
    }
    """

# 交易流水（账单）API
# 前端调用：app.js → loadBills()
#   GET /api/logs?action=buy&q=南瓜 → 加载交易流水列表
# 权限差异：皮埃尔(owner)能看所有用户的流水，玩家(player)只能看自己的
# 日志来源：不是应用代码写入的，而是 MySQL 触发器自动记录的
#   trg_inventory_after_insert → 购买日志（新增库存）
#   trg_inventory_after_update → 购买/出售日志（库存增减）
#   trg_inventory_after_delete → 出售日志（库存删除）
@main_bp.route("/api/logs")
@login_required
def logs():
    user = current_user()
    is_owner = user["role"] == "owner"  # 皮埃尔角色标识，用于前端控制用户列显示
    where = []
    params = []
    action = (request.args.get("action") or "").strip()  # 操作类型筛选：buy/sell
    q = (request.args.get("q") or "").strip()              # 搜索关键词（匹配种子名或用户名）

    # 权限控制：玩家只能看自己的流水，皮埃尔能看所有人的
    if not is_owner:
        where.append("l.user_id = %s")
        params.append(user["user_id"])
    # 按操作类型筛选
    if action:
        where.append("l.action = %s")
        params.append(action)
    # 按种子名或用户名搜索
    if q:
        where.append("(s.name LIKE %s OR u.username LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])
    sql = """
        SELECT DISTINCT l.log_id, l.action, l.quantity, l.unit_price, l.created_at,
               s.name AS seed_name, s.selling_season, u.username
        FROM logs l
        JOIN seeds s ON l.product_id = s.product_id
        JOIN users u ON l.user_id = u.user_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY l.created_at DESC, l.log_id DESC"
    rows = select_all(
        sql,
        params,
        [
            "log_id",
            "action",
            "quantity",
            "unit_price",
            "created_at",
            "seed_name",
            "selling_season",
            "username",
        ],
    )
    # 组装日志列表，计算每条记录的小计 = unit_price × quantity
    items = []
    for row in rows:
        unit_price = float_value(row["unit_price"])
        quantity = int_value(row["quantity"])
        items.append(
            {
                "log_id": int_value(row["log_id"]),
                "action": row["action"],              # 操作类型：buy（购买）/ sell（出售）
                "quantity": quantity,                  # 数量
                "unit_price": unit_price,              # 单价（buy时为seed_buy_price，sell时为seed_sell_price）
                "total": round(unit_price * quantity, 2),  # 小计
                "seed_name": row["seed_name"],        # 种子名称
                "selling_season": row["selling_season"] or "",  # 销售季节
                "username": row["username"],          # 操作用户名
                "created_at": str(row["created_at"]), # 操作时间
            }
        )
    # is_owner 用于前端控制是否显示「用户」列
    return jsonify({"ok": True, "logs": items, "is_owner": is_owner})


# 种植规划推荐 API
# 前端调用：app.js → bindPlanner()
#   提交规划表单 → POST /api/recommend { days, budget, season }
# 业务逻辑：根据剩余天数和预算，计算每种种子的预期收益，筛选出正收益组合，再用贪心算法优化购买方案
@main_bp.route("/api/recommend", methods=["POST"])
@login_required
def recommend():
    data = request.get_json(force=True)
    days = int_value(data.get("days"))       # 剩余天数（1-112）
    budget = int_value(data.get("budget"))   # 预算金额
    season = (data.get("season") or "").strip()  # 季节筛选

    # 校验天数范围
    if days <= 0 or days > 112:
        return api_error("剩余天数必须是 1 到 112 之间的整数。")
    # 校验预算必须大于0
    if budget <= 0:
        return api_error("预算必须大于 0。")

    # 查询所有上架且单价不超过预算的种子
    where = ["s.is_available = 1", "s.seed_buy_price <= %s"]
    params = [budget]
    if season:
        where.append("s.selling_season LIKE %s")
        params.append(f"%{season}%")
    rows = select_all(
        f"""
        SELECT s.product_id, s.crop_id, s.name, s.image_url, s.description, s.selling_season,
               c.growth_time_single, c.growth_time_multiple, s.seed_buy_price,
               c.name as mature_crop_name, c.sell_price as mature_crop_price, c.harvest_type,
               s.is_available, s.seed_sell_price
        FROM seeds s
        LEFT JOIN crops c ON s.crop_id = c.crop_id
        WHERE {' AND '.join(where)}
        ORDER BY s.seed_buy_price ASC, s.name ASC
        """,
        params,
        seed_columns(),
    )

    # 计算每种候选种子的预期收益
    candidates = []
    for row in rows:
        seed = normalize_seed(row)
        harvests = expected_harvests(seed, days)   # 根据天数计算预期收获次数
        revenue = harvests * seed["mature_crop_price"]  # 预期收入 = 收获次数 × 作物售价
        profit = revenue - seed["seed_buy_price"]        # 预期利润 = 收入 - 种子成本
        # 只保留有正收益的种子
        if harvests > 0 and profit > 0:
            seed["harvests"] = harvests
            seed["expected_revenue"] = round(revenue, 2)
            seed["expected_profit"] = round(profit, 2)
            candidates.append(seed)

    # 用贪心算法优化购买方案（按利润/成本比排序，尽量花完预算）
    plan = optimize_plan(candidates, budget)
    return jsonify({"ok": True, "days": days, "budget": budget, "plan": plan, "candidates": candidates})


# SQL 示例 API
# 前端调用：用于展示项目中常用的 SQL 语句示例（教学/演示用途）
#   GET /api/sql-examples → 返回一组 SQL 示例语句
@main_bp.route("/api/sql-examples")
@login_required
def sql_examples():
    return jsonify(
        {
            "ok": True,
            "examples": [
                "SELECT * FROM seeds WHERE is_available = 1 ORDER BY FIELD(selling_season,'春季','夏季','秋季'), name;",
                "UPDATE users SET coins = coins - ? WHERE user_id = ?;",
                "INSERT INTO inventory (user_id, product_id, quantity) VALUES (?, ?, ?);",
                "UPDATE seeds SET is_available = ? WHERE product_id = ?;",
                "DELETE FROM seeds WHERE product_id = ?;",
            ],
        }
    )


# 更新用户金币 API
# 前端调用：base.html 中的金币编辑功能
#   POST /api/update-coins { user_id, coins } → 直接设置用户的金币数额
# 权限控制：皮埃尔可以修改任意用户的金币，玩家只能修改自己的
@main_bp.route("/api/update-coins", methods=["POST"])
@login_required
def update_coins():
    from app.models.user import public_user
    user = current_user()
    data = request.get_json(force=True)
    target_user_id = int_value(data.get("user_id"))   # 目标用户ID
    new_coins = int_value(data.get("coins"))           # 新的金币数额

    # 权限检查：只有皮埃尔可以修改任意用户，玩家只能修改自己
    if user["role"] != "owner" and target_user_id != user["user_id"]:
        return api_error("没有权限修改该用户的金币。", 403)

    # 校验金币不能为负数
    if new_coins < 0:
        return api_error("金币不能为负数。")

    # 直接设置金币数额（注意：这不是加减操作，是直接覆盖）
    execute("UPDATE users SET coins = %s WHERE user_id = %s", [new_coins, target_user_id])
    updated_user = select_one(
        "SELECT user_id, username, role, coins FROM users WHERE user_id = %s",
        [target_user_id],
        ["user_id", "username", "role", "coins"],
    )
    # 返回更新后的用户信息
    return jsonify({"ok": True, "message": "金币更新成功。", "user": public_user(updated_user)})


# ─── 管理员 API ──────────────────────────────────────────

# 添加新种子 API
# 前端调用：app.js → bindAdminActions() 中的表单提交
#   表单隐藏字段 product_id 为空时 → POST /api/admin/seeds → 新增种子
# 业务流程：校验数据 → 先插入 crops 表 → 获取 crop_id → 再插入 seeds 表
# 注意：必须先插 crops 再插 seeds，因为 seeds.crop_id 是外键引用 crops.crop_id
@main_bp.route("/api/admin/seeds", methods=["POST"])
@owner_required
def add_seed():
    data = request.get_json(force=True)

    # validate_seed_payload 将请求数据拆分为 seed_data 和 crop_data，并校验字段合法性
    seed_data, crop_data, error = validate_seed_payload(data)
    if error:
        return api_error(error)

    # 第1步：先插入作物数据到 crops 表
    execute(
        """
        INSERT INTO crops (name, sell_price, harvest_type, growth_time_single, growth_time_multiple)
        VALUES (%s, %s, %s, %s, %s)
        """,
        [
            crop_data["name"],
            crop_data["sell_price"],
            crop_data["harvest_type"],
            crop_data["growth_time_single"],
            crop_data["growth_time_multiple"],
        ],
    )
    # 第2步：获取刚插入的作物自增ID，用于关联到 seeds 表
    conn = get_connection()
    crop_id = conn.insert_id()

    # 第3步：插入种子数据到 seeds 表，通过 crop_id 关联作物
    execute(
        """
        INSERT INTO seeds
        (name, image_url, description, selling_season, seed_buy_price, is_available, seed_sell_price, crop_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            seed_data["name"],
            seed_data["image_url"],
            seed_data["description"],
            seed_data["selling_season"],
            seed_data["seed_buy_price"],
            seed_data["is_available"],
            seed_data["seed_sell_price"],
            crop_id,   # 外键关联到 crops 表
        ],
    )
    return jsonify({"ok": True, "message": "新种子已上架。"})


# 编辑种子信息 API
# 前端调用：app.js → bindAdminActions() 中的表单提交
#   点击卡片「编辑」按钮 → fillSeedForm(seed) 填充表单（含隐藏 product_id）→ 修改后提交
#   表单 product_id 有值 → PUT /api/admin/seeds/{product_id} → 编辑种子
# 业务流程：查原种子 → 校验数据 → 更新 crops 表 → 更新 seeds 表
@main_bp.route("/api/admin/seeds/<int:product_id>", methods=["PUT"])
@owner_required
def edit_seed(product_id):
    seed = get_seed(product_id)
    if not seed:
        return api_error("商品不存在。", 404)
    # validate_seed_payload 将请求数据拆分为 seed_data 和 crop_data，并校验字段合法性
    seed_data, crop_data, error = validate_seed_payload(request.get_json(force=True))
    if error:
        return api_error(error)

    # 第1步：更新作物数据（通过原种子的 crop_id 关联定位）
    if seed.get("crop_id"):
        execute(
            """
            UPDATE crops
            SET name = %s, sell_price = %s, harvest_type = %s,
                growth_time_single = %s, growth_time_multiple = %s
            WHERE crop_id = %s
            """,
            [
                crop_data["name"],
                crop_data["sell_price"],
                crop_data["harvest_type"],
                crop_data["growth_time_single"],
                crop_data["growth_time_multiple"],
                seed["crop_id"],   # 用原种子的 crop_id 定位作物记录
            ],
        )

    # 第2步：更新种子数据
    execute(
        """
        UPDATE seeds
        SET name = %s, image_url = %s, description = %s, selling_season = %s,
            seed_buy_price = %s, is_available = %s, seed_sell_price = %s
        WHERE product_id = %s
        """,
        [
            seed_data["name"],
            seed_data["image_url"],
            seed_data["description"],
            seed_data["selling_season"],
            seed_data["seed_buy_price"],
            seed_data["is_available"],
            seed_data["seed_sell_price"],
            product_id,   # 用 URL 中的 product_id 定位种子记录
        ],
    )
    return jsonify({"ok": True, "message": "商品信息已更新。"})


# 上架/下架切换 API
# 前端调用：app.js → bindAdminActions()
#   点击卡片上的「下架」/「上架」按钮 → POST /api/admin/seeds/{id}/toggle
# 逻辑：读取当前 is_available 状态 → 取反 → 写回
@main_bp.route("/api/admin/seeds/<int:product_id>/toggle", methods=["POST"])
@owner_required
def toggle_seed(product_id):
    seed = get_seed(product_id)
    if not seed:
        return api_error("商品不存在。", 404)
    
    # 当前上架(1) → 下架(0)，当前下架(0) → 上架(1)
    next_state = 0 if int_value(seed["is_available"]) else 1

    execute("UPDATE seeds SET is_available = %s WHERE product_id = %s", [next_state, product_id])

    return jsonify({"ok": True, "message": "已更新上下架状态。"})


# 删除种子 API
# 前端调用：app.js → bindAdminActions()
#   点击卡片上的「删除」按钮 → confirm 确认 → DELETE /api/admin/seeds/{id}
# 删除顺序至关重要，因为外键约束：
#   ① 先删 inventory（引用 seeds）
#   ② 再删 logs（引用 seeds）
#   ③ 再删 crops（被 seeds 引用，但也要清理）
#   ④ 最后删 seeds（主表）
@main_bp.route("/api/admin/seeds/<int:product_id>", methods=["DELETE"])
@owner_required
def delete_seed(product_id):
    seed = get_seed(product_id)
    if not seed:
        return api_error("商品不存在。", 404)

    # 第1步：删除库存记录（inventory.product_id 引用 seeds.product_id）
    execute("DELETE FROM inventory WHERE product_id = %s", [product_id])
    # 第2步：删除日志记录（logs.product_id 引用 seeds.product_id）
    execute("DELETE FROM logs WHERE product_id = %s", [product_id])

    # 第3步：删除关联的作物记录（seeds.crop_id 引用 crops.crop_id）
    if seed.get("crop_id"):
        execute("DELETE FROM crops WHERE crop_id = %s", [seed["crop_id"]])

    # 第4步：最后删除种子记录本身
    execute("DELETE FROM seeds WHERE product_id = %s", [product_id])
    return jsonify({"ok": True, "message": "商品已删除。"})
