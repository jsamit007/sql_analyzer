-- Complex JOIN queries for testing the JOIN diagnostic analyzer
-- Usage: python sql_analyzer.py --file db/test_join.sql --db sqlite --sqlite-path db/database.db

-- 1. 5-table JOIN — full order report with employee who placed it
--    (0 rows: WHERE filters out all statuses)
SELECT u.full_name AS customer,
       e.position AS employee_role,
       d.name AS department,
       o.order_date,
       o.status,
       p.name AS product,
       oi.quantity,
       oi.subtotal
FROM orders o
JOIN users u ON u.id = o.user_id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
JOIN employees e ON e.user_id = o.user_id
JOIN departments d ON d.id = e.department_id
WHERE o.status = 'nonexistent_status';

-- 2. 4-table JOIN with impossible date range
--    (0 rows: future date filter)
SELECT u.username,
       u.email,
       o.id AS order_id,
       o.total_amount,
       p.name AS product,
       p.category,
       oi.quantity,
       oi.unit_price
FROM users u
JOIN orders o ON o.user_id = u.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.order_date > '2099-01-01'
  AND p.category = 'Electronics';

-- 3. LEFT JOIN chain — employees with audit trail
--    (0 rows: nonexistent department name)
SELECT u.full_name,
       e.position,
       d.name AS department,
       al.action,
       al.table_name AS audited_table,
       al.performed_at
FROM employees e
JOIN users u ON u.id = e.user_id
JOIN departments d ON d.id = e.department_id
LEFT JOIN audit_log al ON al.performed_by = e.user_id
WHERE al.action = 'DELETE'
  AND d.name = 'NonexistentDepartment';

-- 4. Self-referencing pattern — managers vs non-managers salary comparison
--    (0 rows: impossible budget filter)
SELECT mgr_u.full_name AS manager,
       emp_u.full_name AS employee,
       d.name AS department,
       mgr.salary AS manager_salary,
       emp.salary AS employee_salary,
       (mgr.salary - emp.salary) AS salary_gap
FROM employees mgr
JOIN users mgr_u ON mgr_u.id = mgr.user_id
JOIN departments d ON d.id = mgr.department_id
JOIN employees emp ON emp.department_id = mgr.department_id AND emp.is_manager = 0
JOIN users emp_u ON emp_u.id = emp.user_id
WHERE mgr.is_manager = 1
  AND mgr.salary < emp.salary
  AND d.budget > 99999999;

-- 5. Aggregate over 6-table JOIN — revenue per department
--    (0 rows: impossible budget threshold)
SELECT d.name AS department,
       COUNT(DISTINCT o.id) AS total_orders,
       SUM(oi.subtotal) AS total_revenue,
       AVG(p.price) AS avg_product_price,
       COUNT(DISTINCT u.id) AS unique_customers
FROM departments d
JOIN employees e ON e.department_id = d.id
JOIN users u ON u.id = e.user_id
JOIN orders o ON o.user_id = u.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE d.budget > 99999999
GROUP BY d.name
HAVING total_revenue > 1000
ORDER BY total_revenue DESC;