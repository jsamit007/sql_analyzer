-- Sample queries for testing sql_analyzer against the demo SQLite database
-- Usage: python sql_analyzer.py --file sample.sql --db sqlite --sqlite-path db/database.db

-- 1. SELECT * anti-pattern — fetches all users
SELECT * FROM users;

-- 2. Filtered query on non-indexed column (age)
SELECT username, email, full_name FROM users WHERE age > 30;

-- 3. Join: employees with department names
SELECT e.position, e.salary, d.name AS department, u.full_name
FROM employees e
JOIN departments d ON d.id = e.department_id
JOIN users u ON u.id = e.user_id
ORDER BY e.salary DESC;

-- 4. Aggregate: total revenue per product category
SELECT p.category, COUNT(oi.id) AS items_sold, SUM(oi.subtotal) AS revenue
FROM order_items oi
JOIN products p ON p.id = oi.product_id
GROUP BY p.category
ORDER BY revenue DESC;

-- 5. Subquery: users who have placed more than one order
SELECT u.username, u.email, sub.order_count
FROM users u
JOIN (
    SELECT user_id, COUNT(*) AS order_count
    FROM orders
    GROUP BY user_id
    HAVING COUNT(*) > 1
) sub ON sub.user_id = u.id;

-- 6. Full table scan on audit_log (no indexes)
SELECT * FROM audit_log WHERE table_name = 'orders' AND action = 'UPDATE';

-- 7. Large result without LIMIT
SELECT id, username, email, full_name, age FROM users ORDER BY created_at DESC;

-- 8. UPDATE without WHERE — dangerous
UPDATE products SET updated_at = CURRENT_TIMESTAMP;

-- 9. Conditional update with WHERE
UPDATE users SET is_active = 0 WHERE age > 50;

-- 10. Insert a new order
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address)
VALUES (4, '2025-04-01 09:00:00', 'pending', 129.98, '321 Elm St, Seattle, WA');

-- 11. Delete cancelled orders
DELETE FROM orders WHERE status = 'cancelled';

-- 12. Complex join: order details report
SELECT o.id AS order_id, u.full_name, o.status, o.order_date,
       p.name AS product, oi.quantity, oi.unit_price, oi.subtotal
FROM orders o
JOIN users u ON u.id = o.user_id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.status IN ('pending', 'processing')
ORDER BY o.order_date;
