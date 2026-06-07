"""种子模型模块

封装种子相关的数据库查询、数据标准化、表单校验、SQL动态构建和种植收益计算。
数据库表关系：seeds LEFT JOIN crops（种子通过 crop_id 关联成熟作物）。
"""

from flask import request

from app.db import select_one, select_all, execute, get_connection, int_value, float_value


# 季节列表，顺序也用于排序（春季→夏季→秋季→全年→冬季）
SEASONS = ["春季", "夏季", "秋季", "全年", "冬季"]


def seed_columns():
    """
    种子查询结果的标准列名列表，用于将数据库原始字段映射为字典键名。
    """
    return [
        "product_id",          # 种子商品ID
        "crop_id",             # 关联的成熟作物ID
        "name",                # 种子名称
        "image_url",           # 种子图片链接
        "description",         # 种子描述
        "selling_season",      # 售卖季节
        "growth_time_single",  # 首次成熟天数
        "growth_time_multiple",# 后续再成熟天数
        "seed_buy_price",      # 种子购买价格
        "mature_crop_name",    # 成熟作物名称
        "mature_crop_price",   # 成熟作物售价
        "harvest_type",        # 收获类型："single"单次 / "multiple"多次
        "is_available",        # 是否上架：1=上架 0=下架
        "seed_sell_price",     # 种子卖出价格
    ]


def get_seed(product_id):
    """根据商品ID查询单个种子的完整信息（含关联的成熟作物信息）。

    通过 seeds LEFT JOIN crops 获取种子及对应成熟作物的数据。
    使用 LEFT JOIN 确保即使没有关联作物也能返回种子信息。

    Args:
        product_id: 种子的商品ID

    Returns:
        dict | None: 种子信息字典，未找到返回 None
    """
    return select_one(
        """
        SELECT s.product_id, s.name, s.image_url, s.description, s.selling_season,
               c.crop_id, c.growth_time_single, c.growth_time_multiple, s.seed_buy_price,
               c.name as mature_crop_name, c.sell_price as mature_crop_price, c.harvest_type,
               s.is_available, s.seed_sell_price
        FROM seeds s
        LEFT JOIN crops c ON s.crop_id = c.crop_id
        WHERE s.product_id = %s
        """,
        [product_id],
        seed_columns() + ["crop_id"], # 在标准列名列表末尾追加 "crop_id"
    )


def normalize_seed(row):
    """将数据库查询的种子原始行数据标准化为前端友好的格式。

    处理内容：数值类型转换（避免Decimal）、空值填充默认值、确保JSON可序列化。

    Args:
        row: 数据库查询返回的原始字典

    Returns:
        dict: 标准化后的种子信息字典
    """
    return {
        "product_id": int_value(row["product_id"]),           # 转为int
        "crop_id": int_value(row.get("crop_id")),             # 转为int，可能为None
        "name": row["name"],                                  # 种子名称
        "image_url": row["image_url"] or "",                  # 空值默认空字符串
        "description": row["description"] or "",              # 空值默认空字符串
        "selling_season": row["selling_season"] or "全年",     # 空值默认"全年"
        "growth_time_single": int_value(row["growth_time_single"]),   # 首次成熟天数
        "growth_time_multiple": int_value(row["growth_time_multiple"]), # 后续再成熟天数
        "seed_buy_price": float_value(row["seed_buy_price"]),         # 转为float
        "mature_crop_name": row["mature_crop_name"] or "",            # 空值默认空字符串
        "mature_crop_price": float_value(row["mature_crop_price"]),   # 转为float
        "harvest_type": row["harvest_type"] or "single",              # 默认"single"
        "is_available": int_value(row["is_available"]),               # 转为int (1/0)
        "seed_sell_price": float_value(row["seed_sell_price"]),       # 转为float
    }


def validate_seed_payload(data):
    """校验并解析种子/作物的表单提交数据，拆分为 seeds 表和 crops 表的写入格式。

    校验规则：种子名称和作物名称不能为空、收获类型必须合法、
    价格不能为负数、首次成熟天数必须>0、多次收获必须填写后续周期。

    Args:
        data: 前端提交的 JSON 字典

    Returns:
        tuple: (seed_data, crop_data, error)
            校验失败 → (None, None, "错误信息")
            校验成功 → (seed_data字典, crop_data字典, None)
    """
    # 提取并清洗字段
    name = (data.get("name") or "").strip()                              # 种子名称
    season = (data.get("selling_season") or "全年").strip()              # 售卖季节，默认"全年"
    harvest_type = data.get("harvest_type") or "single"                 # 收获类型，默认"single"
    buy_price = float_value(data.get("seed_buy_price"), -1)             # 种子购买价，转换失败返回-1
    sell_price = float_value(data.get("seed_sell_price"), -1)           # 种子卖出价
    crop_name = (data.get("mature_crop_name") or "").strip()            # 成熟作物名称
    crop_price = float_value(data.get("mature_crop_price"), -1)         # 成熟作物售价
    growth = int_value(data.get("growth_time_single"), -1)              # 首次成熟天数
    regrowth = int_value(data.get("growth_time_multiple"), 0)           # 后续再成熟天数，默认0

    # 逐项业务校验
    if not name:
        return None, None, "种子名称不能为空。"
    if not crop_name:
        return None, None, "成熟作物名称不能为空。"
    if harvest_type not in {"single", "multiple"}:
        return None, None, "收获类型不合法。"
    if buy_price < 0 or sell_price < 0 or crop_price < 0:
        return None, None, "价格不能为负数。"
    if growth <= 0:
        return None, None, "首次成熟天数必须大于 0。"
    if harvest_type == "multiple" and regrowth <= 0:
        return None, None, "多次收获作物必须填写后续生长周期。"

    # 校验通过，组装 seeds 表和 crops 表的写入数据
    seed_data = {
        "name": name,
        "image_url": (data.get("image_url") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "selling_season": season,
        "seed_buy_price": buy_price,
        "is_available": 1 if int_value(data.get("is_available"), 1) else 0,  # 转为1/0
        "seed_sell_price": sell_price,
    }
    crop_data = {
        "name": crop_name,
        "sell_price": crop_price,
        "harvest_type": harvest_type,
        "growth_time_single": growth,
        "growth_time_multiple": regrowth if harvest_type == "multiple" else 0,  # 单次收获时强制为0
    }
    return seed_data, crop_data, None


# 动态构建一个SQL查询语句，用于从数据库中查询“种子”及其对应的“成熟农作物”的信息。
def seed_select_sql(include_unavailable=True):
    where = ["1 = 1"] # 加入 1 = 1 这个永远成立的条件。这是一个经典的SQL拼接技巧，目的是让后续添加的条件都可以直接以 AND 开头，而不需要担心某个条件是否第一个条件前面是否需要加 AND。
    params = []
    if not include_unavailable:
        where.append("s.is_available = 1") # 如果不包含不可用的种子，则添加一个条件，要求 s.is_available 必须等于 1（即只查询已上架的种子）。

    # 当 Flask 应用接收到一个 HTTP 请求时，Flask 框架会自动创建一个 Request 对象，并将其绑定到当前线程/协程的上下文中。
    season = request.args.get("season", "")
    q = (request.args.get("q") or "").strip()
    #  request.args 获取的是 URL 中的 查询字符串参数（即 ? 后面的部分）。例如用户访问 /seeds?season=春季&q=南瓜，那么 request.args.get("season") 就会得到 "春季"，request.args.get("q") 就会得到 "南瓜"。

    if season:
        where.append("s.selling_season LIKE %s")
        params.append(f"%{season}%") # 花括号 {} 的作用是提取变量 season 的值放进去。例如如果 season 是 "春季"，那么 f"%{season}%" 就会被解析为 "%春季%"，这个字符串可以用在 SQL 的 LIKE 语句中，表示匹配任何包含 "春季" 的 selling_season。

    if q:
        where.append("(s.name LIKE %s OR c.name LIKE %s OR s.description LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like])

    sql = f"""
        SELECT s.product_id, s.crop_id, s.name, s.image_url, s.description, s.selling_season,
               c.growth_time_single, c.growth_time_multiple, s.seed_buy_price,
               c.name as mature_crop_name, c.sell_price as mature_crop_price, c.harvest_type,
               s.is_available, s.seed_sell_price
        FROM seeds s
        LEFT JOIN crops c ON s.crop_id = c.crop_id
        WHERE {' AND '.join(where)}
        ORDER BY FIELD(s.selling_season, '春季', '夏季', '秋季', '全年', '冬季'), s.name
    """
    return sql, params


def expected_harvests(seed, days):
    first = seed["growth_time_single"]
    if days < first:
        return 0
    if seed["harvest_type"] != "multiple" or seed["growth_time_multiple"] <= 0:
        return 1
    return 1 + (days - first) // seed["growth_time_multiple"]


def optimize_plan(candidates, budget):
    max_budget = int(budget)
    dp = [(0.0, []) for _ in range(max_budget + 1)]
    for coin in range(max_budget + 1):
        best_profit, best_items = dp[coin]
        for seed in candidates:
            cost = int(seed["seed_buy_price"])
            if cost <= 0 or cost > coin:
                continue
            prev_profit, prev_items = dp[coin - cost]
            profit = prev_profit + seed["expected_profit"]
            if profit > best_profit:
                dp[coin] = (profit, prev_items + [seed])
                best_profit, best_items = dp[coin]
    best_profit, items = max(dp, key=lambda entry: entry[0])
    grouped = {}
    for seed in items:
        pid = seed["product_id"]
        grouped.setdefault(pid, {**seed, "quantity": 0, "total_cost": 0.0, "total_profit": 0.0, "total_revenue": 0.0})
        grouped[pid]["quantity"] += 1
        grouped[pid]["total_cost"] += seed["seed_buy_price"]
        grouped[pid]["total_profit"] += seed["expected_profit"]
        grouped[pid]["total_revenue"] += seed["expected_revenue"]
    result = list(grouped.values())
    for item in result:
        item["total_cost"] = round(item["total_cost"], 2)
        item["total_profit"] = round(item["total_profit"], 2)
        item["total_revenue"] = round(item["total_revenue"], 2)
    return {
        "items": result,
        "total_cost": round(sum(item["total_cost"] for item in result), 2),
        "total_revenue": round(sum(item["total_revenue"] for item in result), 2),
        "total_profit": round(sum(item["total_profit"] for item in result), 2),
    }