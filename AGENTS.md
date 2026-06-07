我现在正在完成数据库系统作业。我的作业内容是做一个皮埃尔商店网页，灵感来源于星露谷物语。

以下是目前数据库的操作代码：

```sql
use pierres_store;

CREATE TABLE seeds (
    product_id INT AUTO_INCREMENT PRIMARY KEY, # AUTO_INCREMENT 自动增长
    name VARCHAR(100) NOT NULL,
    image_url VARCHAR(255),
    description TEXT, # TEXT 长度可变，可以存放几 KB 的文本。比 VARCHAR 大，适合描述文字较多的场景
    selling_season VARCHAR(50),
    growth_time_single INT,
    growth_time_multiple INT,
    price DECIMAL(10,2) NOT NULL,
    mature_crop_name VARCHAR(100),
    mature_crop_price DECIMAL(10,2),
    harvest_type ENUM('single', 'multiple') NOT NULL DEFAULT 'single'
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('owner','player') NOT NULL DEFAULT 'player',
    coins INT DEFAULT 0 COMMENT '玩家金币余额，皮埃尔不使用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE seeds
    ADD COLUMN is_available TINYINT(1) NOT NULL DEFAULT 1 COMMENT '商店上架状态，1=上架，0=下架';

CREATE TABLE logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '操作用户ID',
    product_id INT NOT NULL COMMENT '种子ID',
    action ENUM('buy','sell') NOT NULL COMMENT '操作类型：购买或卖出',
    quantity INT NOT NULL COMMENT '数量',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '当时单价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES seeds(product_id)
) COMMENT='购买和卖出记录表';

ALTER TABLE seeds
    ADD COLUMN seed_price DECIMAL(10,2) NOT NULL COMMENT '种子售价';

CREATE TABLE inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES seeds(product_id)
);

ALTER TABLE inventory
    ADD CONSTRAINT uk_user_seed UNIQUE (user_id, product_id); # 给库存表加一个联合唯一约束，保证 同一个用户，不能重复拥有同一种商品。
    # uk = Unique Key（唯一键）

ALTER TABLE seeds
    CHANGE COLUMN price seed_buy_price DECIMAL(10,2) NOT NULL,
    CHANGE COLUMN seed_price seed_sell_price DECIMAL(10,2) NOT NULL COMMENT '种子卖出价格';

DELIMITER $$ # 把结束语句从分号改成钱钱

# 购入作物操作
CREATE TRIGGER trg_inventory_after_insert
AFTER INSERT ON inventory
FOR EACH ROW
BEGIN
    INSERT INTO logs (user_id, product_id, action, quantity, unit_price)
    SELECT NEW.user_id, NEW.product_id, 'buy', NEW.quantity, s.seed_buy_price
    FROM seeds s WHERE s.product_id = NEW.product_id;
end$$

# 增加或卖出部分
CREATE TRIGGER trg_inventory_after_update
AFTER UPDATE ON inventory
FOR EACH ROW
BEGIN
    # 再次购入
    if NEW.quantity > OLD.quantity THEN

        INSERT INTO logs (user_id, product_id, action, quantity, unit_price)
        SELECT NEW.user_id, NEW.product_id, 'buy', NEW.quantity-OLD.quantity, s.seed_buy_price
        FROM seeds s WHERE s.product_id = NEW.product_id;

    # 部分卖出
    ELSEIF NEW.quantity < OLD.quantity THEN

        INSERT INTO logs (user_id, product_id, action, quantity, unit_price)
        SELECT NEW.user_id, NEW.product_id, 'sell', OLD.quantity-NEW.quantity, s.seed_sell_price
        FROM seeds s WHERE s.product_id = NEW.product_id;

    end if;
end $$

# 全部卖出
CREATE TRIGGER trg_inventory_after_delete
AFTER DELETE ON inventory
FOR EACH ROW
BEGIN
    INSERT INTO logs(user_id, product_id, action, quantity, unit_price)
    SELECT OLD.user_id, OLD.product_id, 'sell', OLD.quantity, s.seed_sell_price
    FROM seeds s WHERE s.product_id = OLD.product_id;
end $$

DELIMITER ;
```



```sql
use pierres_store;

CREATE TABLE seeds (
    product_id INT AUTO_INCREMENT PRIMARY KEY, # AUTO_INCREMENT 自动增长
    name VARCHAR(100) NOT NULL,
    image_url VARCHAR(255),
    description TEXT, # TEXT 长度可变，可以存放几 KB 的文本。比 VARCHAR 大，适合描述文字较多的场景
    selling_season VARCHAR(50),
    growth_time_single INT,
    growth_time_multiple INT,
    price DECIMAL(10,2) NOT NULL,
    mature_crop_name VARCHAR(100),
    mature_crop_price DECIMAL(10,2),
    harvest_type ENUM('single', 'multiple') NOT NULL DEFAULT 'single'
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('owner','player') NOT NULL DEFAULT 'player',
    coins INT DEFAULT 0 COMMENT '玩家金币余额，皮埃尔不使用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE seeds
    ADD COLUMN is_available TINYINT(1) NOT NULL DEFAULT 1 COMMENT '商店上架状态，1=上架，0=下架';

CREATE TABLE logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '操作用户ID',
    product_id INT NOT NULL COMMENT '种子ID',
    action ENUM('buy','sell') NOT NULL COMMENT '操作类型：购买或卖出',
    quantity INT NOT NULL COMMENT '数量',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '当时单价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES seeds(product_id)
) COMMENT='购买和卖出记录表';

ALTER TABLE seeds
    ADD COLUMN seed_price DECIMAL(10,2) NOT NULL COMMENT '种子售价';

CREATE TABLE inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES seeds(product_id)
);

ALTER TABLE inventory
    ADD CONSTRAINT uk_user_seed UNIQUE (user_id, product_id); # 给库存表加一个联合唯一约束，保证 同一个用户，不能重复拥有同一种商品。
    # uk = Unique Key（唯一键）

ALTER TABLE seeds
    CHANGE COLUMN price seed_buy_price DECIMAL(10,2) NOT NULL,
    CHANGE COLUMN seed_price seed_sell_price DECIMAL(10,2) NOT NULL COMMENT '种子卖出价格';

DELIMITER $$ # 把结束语句从分号改成钱钱

# 购入作物操作
CREATE TRIGGER trg_inventory_after_insert
AFTER INSERT ON inventory
FOR EACH ROW
BEGIN
    INSERT INTO logs (user_id, product_id, action, quantity, unit_price)
    SELECT NEW.user_id, NEW.product_id, 'buy', NEW.quantity, s.seed_buy_price
    FROM seeds s WHERE s.product_id = NEW.product_id;
end$$

# 增加或卖出部分
CREATE TRIGGER trg_inventory_after_update
AFTER UPDATE ON inventory
FOR EACH ROW
BEGIN
    # 再次购入
    if NEW.quantity > OLD.quantity THEN

        INSERT INTO logs (user_id, product_id, action, quantity, unit_price)
        SELECT NEW.user_id, NEW.product_id, 'buy', NEW.quantity-OLD.quantity, s.seed_buy_price
        FROM seeds s WHERE s.product_id = NEW.product_id;

    # 部分卖出
    ELSEIF NEW.quantity < OLD.quantity THEN

        INSERT INTO logs (user_id, product_id, action, quantity, unit_price)
        SELECT NEW.user_id, NEW.product_id, 'sell', OLD.quantity-NEW.quantity, s.seed_sell_price
        FROM seeds s WHERE s.product_id = NEW.product_id;

    end if;
end $$

# 全部卖出
CREATE TRIGGER trg_inventory_after_delete
AFTER DELETE ON inventory
FOR EACH ROW
BEGIN
    INSERT INTO logs(user_id, product_id, action, quantity, unit_price)
    SELECT OLD.user_id, OLD.product_id, 'sell', OLD.quantity, s.seed_sell_price
    FROM seeds s WHERE s.product_id = OLD.product_id;
end $$

DELIMITER ;

-- mysqldump -u root -p pierres_store > beifen.sql;
-- ls beifen.sql

CREATE TABLE crops (
    crop_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '成熟作物名称',
    sell_price DECIMAL(10,2) COMMENT '成熟作物售价',
    harvest_type ENUM('single','multiple') NOT NULL DEFAULT 'single' COMMENT '收获类型',
    growth_time_single INT COMMENT '单季作物生长时间',
    growth_time_multiple INT COMMENT '多季作物生长时间'
);

ALTER TABLE seeds
    ADD COLUMN crop_id INT COMMENT '对应成熟作物ID',
    ADD CONSTRAINT fk_seed_crop FOREIGN KEY (crop_id) REFERENCES crops(crop_id);

INSERT INTO crops (name, sell_price, harvest_type, growth_time_single, growth_time_multiple)
SELECT mature_crop_name, mature_crop_price, harvest_type, growth_time_single, growth_time_multiple
FROM seeds;

UPDATE seeds s
    JOIN crops c
    ON s.mature_crop_name = c.name
        AND (s.mature_crop_price = c.sell_price OR s.mature_crop_price IS NULL AND c.sell_price IS NULL)
SET s.crop_id = c.crop_id;

ALTER TABLE seeds
    DROP COLUMN mature_crop_name,
    DROP COLUMN mature_crop_price,
    DROP COLUMN harvest_type,
    DROP COLUMN growth_time_single,
    DROP COLUMN growth_time_multiple;

-- mysqldump -u root -p pierres_store > beifen2.sql;
-- ls beifen2.sql

ALTER TABLE seeds
    DROP COLUMN mature_crop_name,
    DROP COLUMN mature_crop_price,
    DROP COLUMN harvest_type,
    DROP COLUMN growth_time_single,
    DROP COLUMN growth_time_multiple;
```

