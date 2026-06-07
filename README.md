# 皮埃尔商店数据库系统设计

这是一个基于 MySQL 的像素风多页面网页系统，主题来自《星露谷物语》皮埃尔商店。项目包含用户登录注册、种子选购、仓库展示、皮埃尔商品管理、智能选购推荐、网页数据爬取和 Excel 生成。

## 运行环境

- Python 3.10+
- MySQL 8.0+
- 已存在数据库：`pierres_store`
- 默认连接：`localhost:3306 / sunmingtao`

如需覆盖数据库连接，可设置环境变量：

```powershell
$env:PIERRES_DB_HOST="localhost"
$env:PIERRES_DB_PORT="3306"
$env:PIERRES_DB_NAME="pierres_store"
$env:PIERRES_DB_USER="sunmingtao"
$env:PIERRES_DB_PASSWORD="你的密码"
```

## 快速启动

```powershell
python scripts/scrape_seed_data.py
python scripts/import_seed_data.py --demo-users
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

演示账号：

| 用户名 | 密码 | 类型 |
| --- | --- | --- |
| 皮埃尔 | pierre123 | 皮埃尔 |
| 农场主 | player123 | 玩家 |

## 功能说明

1. 登录注册  
   注册时可选择“玩家”或“皮埃尔”。后端会检查用户名、密码长度、用户类型是否合法。

2. 商店选购  
   商店页面显示当前金币数，种子按季节分类并按名称排序。玩家可以购买种子，系统会检查数量、商品上下架状态和金币余额。

3. 独立仓库  
   仓库页面展示当前用户拥有的种子，支持按季节筛选和名称搜索。玩家可按种子卖价出售仓库中的种子。

4. 皮埃尔管理  
   皮埃尔账号可以新增、编辑、上架、下架、删除种子商品。玩家账号不能进入管理页面，也不能调用管理接口。

5. 智能选购  
   用户输入剩余天数、预算和季节后，后端根据作物首次成熟天数、后续生长周期、最高售价和购买价计算预期利润，并使用动态规划给出预算内利润最高的组合。

6. 数据爬取与 Excel  
   `scripts/scrape_seed_data.py` 优先访问灰机 Wiki 指定页面；若页面被 Cloudflare 拦截，则回退到 B 站中文百科的 MediaWiki raw 页面。脚本会解析皮埃尔商店春季、夏季、秋季库存，并继续访问种子/作物详情页，提取生长周期、种子卖价、作物名称和作物售价，最后生成 `data/pierres_seed_data.xlsx`。

## 数据库表

- `users`：用户、角色、金币
- `seeds`：种子商品、季节、生长周期、价格、上下架状态
- `inventory`：用户仓库库存
- `logs`：购买和出售记录

建表 SQL 见 `schema.sql`。

## 课程展示中的 SQL 功能

后端数据库访问集中在 `db.py` 和 `app.py`。页面操作对应的典型 SQL 包括：

```sql
SELECT product_id, name, selling_season, seed_buy_price
FROM seeds
WHERE is_available = 1
ORDER BY FIELD(selling_season, '春季', '夏季', '秋季', '全年', '冬季'), name;
```

```sql
UPDATE users
SET coins = coins - ?
WHERE user_id = ?;
```

```sql
INSERT INTO inventory (user_id, product_id, quantity)
VALUES (?, ?, ?);
```

```sql
UPDATE seeds
SET is_available = ?
WHERE product_id = ?;
```

```sql
DELETE FROM seeds
WHERE product_id = ?;
```

系统还提供 `/api/sql-examples` 接口，方便在网页调试或答辩时展示核心 SQL。

## 文件结构

```text
app.py                         Flask 路由、权限、业务逻辑
db.py                          MySQL 命令行访问封装
config.py                      数据库连接配置
schema.sql                     建表 SQL
templates/                     多页面 HTML 模板
static/styles.css              像素风样式
static/app.js                  前端交互逻辑
scripts/scrape_seed_data.py    爬虫与 xlsx 生成
scripts/import_seed_data.py    xlsx 导入 MySQL
data/pierres_seed_data.xlsx    爬虫生成的数据文件
```

