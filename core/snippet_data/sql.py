"""SQL snippets (PostgreSQL flavour where dialects differ)."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "SQL"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Select with a filter", code(r"""
SELECT name, email
FROM users
WHERE active = TRUE AND created_at >= '2025-01-01'
ORDER BY name ASC
LIMIT 20;
""")),
    Snippet(_L, "Junior", "Insert, update and delete", code(r"""
INSERT INTO products (name, price) VALUES ('Desk', 199.00);
UPDATE products SET price = price * 0.9 WHERE name = 'Desk';
DELETE FROM products WHERE price < 5;
""")),
    Snippet(_L, "Junior", "Count by status", code(r"""
SELECT status, COUNT(*) AS total
FROM orders
GROUP BY status
ORDER BY total DESC;
""")),
    Snippet(_L, "Mid", "Join with an aggregate", code(r"""
SELECT c.name, COUNT(o.id) AS orders, SUM(o.total) AS revenue
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.name
HAVING SUM(o.total) > 1000;
""")),
    Snippet(_L, "Mid", "Left join for missing rows", code(r"""
SELECT u.id, u.email
FROM users u
LEFT JOIN logins l ON l.user_id = u.id
WHERE l.user_id IS NULL;
""")),
    Snippet(_L, "Mid", "Subquery with IN", code(r"""
SELECT name
FROM products
WHERE category_id IN (
  SELECT id FROM categories WHERE archived = FALSE
);
""")),
    Snippet(_L, "Senior", "Common table expression", code(r"""
WITH recent AS (
  SELECT customer_id, SUM(total) AS spent
  FROM orders
  WHERE created_at > NOW() - INTERVAL '30 days'
  GROUP BY customer_id
)
SELECT * FROM recent WHERE spent > 500;
""")),
    Snippet(_L, "Senior", "Window function rank", code(r"""
SELECT department, name, salary,
  RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rnk
FROM employees
ORDER BY department, rnk;
""")),
    Snippet(_L, "Senior", "Upsert with ON CONFLICT", code(r"""
INSERT INTO counters (name, hits)
VALUES ('home', 1)
ON CONFLICT (name)
DO UPDATE SET hits = counters.hits + 1;
""")),
)
