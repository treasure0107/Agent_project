-- 在 Navicat（SSH 已通的阿里云 MySQL）中执行
USE medical_assistant;

-- 1) 允许外网应用连接（本机跑后端需要）
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'Root@123456';
ALTER USER 'root'@'%' IDENTIFIED BY 'Root@123456';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;

-- 2) 演示账号：demo / Demo@123456
INSERT INTO users (username, email, password_hash)
VALUES (
  'demo',
  'demo@example.com',
  '$2b$12$CGDGinQJt7Z8Ovv77RNCq.RcV1TdWdBKLksvT5mPh2tnMmuFv7ZsO'
)
ON DUPLICATE KEY UPDATE
  password_hash = VALUES(password_hash),
  email = VALUES(email);
