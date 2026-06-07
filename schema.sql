CREATE DATABASE IF NOT EXISTS pierres_store DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pierres_store;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('owner','player') NOT NULL DEFAULT 'player',
    coins INT DEFAULT 0 COMMENT '玩家金币余额,皮埃尔不使用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 作物表
CREATE TABLE IF NOT EXISTS crops (
    crop_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '成熟作物名称',
    sell_price DECIMAL(10,2) COMMENT '成熟作物售价',
    harvest_type ENUM('single','multiple') NOT NULL DEFAULT 'single' COMMENT '收获类型',
    growth_time_single INT COMMENT '单季作物生长时间',
    growth_time_multiple INT COMMENT '多季作物生长时间'
);

-- 种子表
CREATE TABLE IF NOT EXISTS seeds (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    image_url VARCHAR(255),
    description TEXT,
    selling_season VARCHAR(50),
    seed_buy_price DECIMAL(10,2) NOT NULL,
    seed_sell_price DECIMAL(10,2) NOT NULL COMMENT '种子卖出价格',
    is_available TINYINT(1) NOT NULL DEFAULT 1 COMMENT '商店上架状态,1=上架,0=下架',
    crop_id INT COMMENT '对应成熟作物ID',
    FOREIGN KEY (crop_id) REFERENCES crops(crop_id)
);

-- 库存表
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    CONSTRAINT uk_user_seed UNIQUE (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES seeds(product_id)
);

-- 日志表
CREATE TABLE IF NOT EXISTS logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '操作用户ID',
    product_id INT NOT NULL COMMENT '种子ID',
    action ENUM('buy','sell') NOT NULL COMMENT '操作类型:购买或卖出',
    quantity INT NOT NULL COMMENT '数量',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '当时单价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES seeds(product_id)
) COMMENT='购买和卖出记录表';

-- 触发器：库存新增时记录购买日志
DELIMITER $$

CREATE TRIGGER trg_inventory_after_insert 
AFTER INSERT ON inventory 
FOR EACH ROW 
BEGIN 
    INSERT INTO logs (user_id, product_id, action, quantity, unit_price) 
    SELECT NEW.user_id, NEW.product_id, 'buy', NEW.quantity, s.seed_buy_price 
    FROM seeds s 
    WHERE s.product_id = NEW.product_id;
END$$

-- 触发器：库存更新时记录购买或卖出日志
CREATE TRIGGER trg_inventory_after_update 
AFTER UPDATE ON inventory 
FOR EACH ROW 
BEGIN 
    -- 再次购入
    IF NEW.quantity > OLD.quantity THEN
        INSERT INTO logs (user_id, product_id, action, quantity, unit_price)
        SELECT NEW.user_id, NEW.product_id, 'buy', NEW.quantity - OLD.quantity, s.seed_buy_price
        FROM seeds s 
        WHERE s.product_id = NEW.product_id;
    -- 部分卖出
    ELSEIF NEW.quantity < OLD.quantity THEN
        INSERT INTO logs (user_id, product_id, action, quantity, unit_price)
        SELECT NEW.user_id, NEW.product_id, 'sell', OLD.quantity - NEW.quantity, s.seed_sell_price
        FROM seeds s 
        WHERE s.product_id = NEW.product_id;
    END IF;
END$$

-- 触发器：库存删除时记录卖出日志
CREATE TRIGGER trg_inventory_after_delete 
AFTER DELETE ON inventory 
FOR EACH ROW 
BEGIN 
    INSERT INTO logs (user_id, product_id, action, quantity, unit_price) 
    SELECT OLD.user_id, OLD.product_id, 'sell', OLD.quantity, s.seed_sell_price 
    FROM seeds s 
    WHERE s.product_id = OLD.product_id;
END$$

DELIMITER ;