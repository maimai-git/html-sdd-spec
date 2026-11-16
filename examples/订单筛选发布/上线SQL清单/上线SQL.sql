-- 上线 SQL 清单
-- 本文件用于演示提单格式。执行顺序为先建索引，再开启配置。

-- ===== 01 Orders API / orders_demo =====
-- 目标环境：演示测试
-- 数据库类型：PostgreSQL
-- 目标实例：orders-demo-test
-- 数据库：orders_demo
-- Schema：public
-- 前置条件：确认 public.orders 已有 status 和 id 两列，同名索引未创建。
-- 跨库依赖：无。
-- 验收：检查索引有效，并用 EXPLAIN 核对按状态筛选和按 id 倒序的查询计划。
-- 发布时在事务块之外执行。
CREATE INDEX CONCURRENTLY idx_orders_status_id
    ON public.orders (status, id DESC);
