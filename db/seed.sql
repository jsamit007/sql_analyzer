-- Seed data for SQL Analyzer demo database

-- ============================================================
-- Users
-- ============================================================
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('alice',    'alice@example.com',    'Alice Johnson',    30, 1);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('bob',      'bob@example.com',      'Bob Smith',        25, 1);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('charlie',  'charlie@example.com',  'Charlie Brown',    35, 1);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('diana',    'diana@example.com',    'Diana Prince',     28, 1);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('edward',   'edward@example.com',   'Edward Norton',    42, 1);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('fiona',    'fiona@example.com',    'Fiona Apple',      31, 0);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('george',   'george@example.com',   'George Lucas',     55, 1);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('hannah',   'hannah@example.com',   'Hannah Montana',   22, 1);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('ivan',     'ivan@example.com',     'Ivan Drago',       38, 1);
INSERT INTO users (username, email, full_name, age, is_active) VALUES
    ('julia',    'julia@example.com',    'Julia Roberts',    45, 0);

-- ============================================================
-- Departments
-- ============================================================
INSERT INTO departments (name, description, budget) VALUES
    ('Engineering',  'Software development and infrastructure', 500000.00);
INSERT INTO departments (name, description, budget) VALUES
    ('Marketing',    'Brand management and advertising',        250000.00);
INSERT INTO departments (name, description, budget) VALUES
    ('Sales',        'Revenue generation and client relations', 300000.00);
INSERT INTO departments (name, description, budget) VALUES
    ('HR',           'Human resources and talent acquisition',  150000.00);
INSERT INTO departments (name, description, budget) VALUES
    ('Finance',      'Accounting and financial planning',       200000.00);

-- ============================================================
-- Employees
-- ============================================================
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (1, 1, 'Senior Software Engineer', 120000.00, '2020-03-15', 0);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (2, 1, 'Junior Developer',          75000.00, '2023-01-10', 0);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (3, 1, 'Engineering Manager',      145000.00, '2018-06-01', 1);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (4, 2, 'Marketing Specialist',      85000.00, '2021-09-20', 0);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (5, 3, 'Sales Director',           130000.00, '2019-02-14', 1);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (6, 2, 'Content Writer',            65000.00, '2022-07-05', 0);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (7, 4, 'HR Manager',              110000.00, '2017-11-30', 1);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (8, 3, 'Sales Representative',      60000.00, '2024-04-01', 0);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (9, 5, 'Financial Analyst',         95000.00, '2020-08-22', 0);
INSERT INTO employees (user_id, department_id, position, salary, hire_date, is_manager) VALUES
    (10, 5, 'CFO',                     180000.00, '2016-01-15', 1);

-- ============================================================
-- Products
-- ============================================================
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Wireless Mouse',          'ELEC-001', 'Electronics',    29.99,  150, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Mechanical Keyboard',     'ELEC-002', 'Electronics',    89.99,   75, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('USB-C Hub',               'ELEC-003', 'Electronics',    49.99,  200, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Standing Desk',           'FURN-001', 'Furniture',     399.99,   30, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Ergonomic Chair',         'FURN-002', 'Furniture',     549.99,   20, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Monitor 27"',             'ELEC-004', 'Electronics',   349.99,   45, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Webcam HD',               'ELEC-005', 'Electronics',    79.99,  100, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Notebook A5',             'STAT-001', 'Stationery',      5.99, 500, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Whiteboard Markers (12)', 'STAT-002', 'Stationery',     12.99, 300, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Noise-Cancelling Headphones', 'ELEC-006', 'Electronics', 199.99, 60, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Desk Lamp LED',           'FURN-003', 'Furniture',      39.99,  80, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Cable Management Kit',    'ACCS-001', 'Accessories',    19.99, 250, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Laptop Stand',            'ACCS-002', 'Accessories',    44.99, 120, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Wireless Charger',        'ELEC-007', 'Electronics',    34.99, 180, 1);
INSERT INTO products (name, sku, category, price, stock_quantity, is_available) VALUES
    ('Discontinued Widget',     'DISC-001', 'Misc',           9.99,    0, 0);

-- ============================================================
-- Orders
-- ============================================================
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address, notes) VALUES
    (1, '2025-01-05 10:30:00', 'delivered',   169.97, '123 Main St, Springfield, IL',   NULL);
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address, notes) VALUES
    (2, '2025-01-12 14:15:00', 'delivered',    89.99, '456 Oak Ave, Portland, OR',      'Gift wrap please');
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address, notes) VALUES
    (3, '2025-02-01 09:00:00', 'shipped',     949.98, '789 Pine Rd, Austin, TX',        NULL);
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address, notes) VALUES
    (1, '2025-02-14 16:45:00', 'processing',  399.98, '123 Main St, Springfield, IL',   'Valentine order');
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address, notes) VALUES
    (4, '2025-02-20 11:30:00', 'pending',      79.99, '321 Elm St, Seattle, WA',        NULL);
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address, notes) VALUES
    (5, '2025-03-01 08:00:00', 'cancelled',   549.99, '654 Birch Ln, Denver, CO',       'Changed mind');
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address, notes) VALUES
    (8, '2025-03-10 13:20:00', 'pending',      64.98, '987 Cedar Dr, Miami, FL',        NULL);
INSERT INTO orders (user_id, order_date, status, total_amount, shipping_address, notes) VALUES
    (3, '2025-03-15 17:00:00', 'processing',  234.98, '789 Pine Rd, Austin, TX',        'Rush delivery');

-- ============================================================
-- Order Items
-- ============================================================
-- Order 1: Wireless Mouse + Mechanical Keyboard + USB-C Hub
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (1, 1, 1, 29.99);
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (1, 2, 1, 89.99);
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (1, 3, 1, 49.99);

-- Order 2: Mechanical Keyboard
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (2, 2, 1, 89.99);

-- Order 3: Standing Desk + Ergonomic Chair
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (3, 4, 1, 399.99);
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (3, 5, 1, 549.99);

-- Order 4: Noise-Cancelling Headphones x2
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (4, 10, 2, 199.99);

-- Order 5: Webcam HD
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (5, 7, 1, 79.99);

-- Order 6: Ergonomic Chair (cancelled)
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (6, 5, 1, 549.99);

-- Order 7: Notebook + Whiteboard Markers
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (7, 8, 5, 5.99);
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (7, 9, 1, 12.99);

-- Order 8: Wireless Charger + Laptop Stand
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (8, 14, 1, 34.99);
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (8, 13, 1, 44.99);

-- ============================================================
-- Audit Log (sample entries — no indexes on purpose)
-- ============================================================
INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, performed_by, performed_at) VALUES
    ('users', 1, 'INSERT', NULL, '{"username":"alice","email":"alice@example.com"}', NULL, '2025-01-01 08:00:00');
INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, performed_by, performed_at) VALUES
    ('orders', 1, 'INSERT', NULL, '{"user_id":1,"status":"pending"}', 1, '2025-01-05 10:30:00');
INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, performed_by, performed_at) VALUES
    ('orders', 1, 'UPDATE', '{"status":"pending"}', '{"status":"processing"}', 1, '2025-01-05 12:00:00');
INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, performed_by, performed_at) VALUES
    ('orders', 1, 'UPDATE', '{"status":"processing"}', '{"status":"shipped"}', 1, '2025-01-06 09:00:00');
INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, performed_by, performed_at) VALUES
    ('orders', 1, 'UPDATE', '{"status":"shipped"}', '{"status":"delivered"}', 1, '2025-01-08 14:00:00');
INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, performed_by, performed_at) VALUES
    ('users', 6, 'UPDATE', '{"is_active":1}', '{"is_active":0}', 7, '2025-02-01 10:00:00');
INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, performed_by, performed_at) VALUES
    ('orders', 6, 'UPDATE', '{"status":"pending"}', '{"status":"cancelled"}', 5, '2025-03-02 08:00:00');
INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, performed_by, performed_at) VALUES
    ('products', 15, 'UPDATE', '{"is_available":1}', '{"is_available":0}', NULL, '2025-03-05 11:00:00');
