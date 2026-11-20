"""JavaScript snippets."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "JavaScript"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Loop with template literal", code(r"""
const names = ["Ada", "Linus", "Grace"];
for (const name of names) {
  console.log(`Hello, ${name}!`);
}
""")),
    Snippet(_L, "Junior", "Object entries", code(r"""
const user = { name: "Ada", role: "admin", active: true };
for (const [key, value] of Object.entries(user)) {
  console.log(`${key}: ${value}`);
}
""")),
    Snippet(_L, "Junior", "Sum with reduce", code(r"""
const prices = [4.5, 12, 3.25];
const total = prices.reduce((sum, price) => sum + price, 0);
console.log(`Total: ${total.toFixed(2)}`);
""")),
    Snippet(_L, "Mid", "Destructuring with defaults", code(r"""
function connect({ host = "localhost", port = 5432, ...rest } = {}) {
  const url = `postgres://${host}:${port}`;
  return { url, options: rest };
}
""")),
    Snippet(_L, "Mid", "Optional chaining and nullish", code(r"""
const city = user?.address?.city ?? "Unknown";
const port = Number(process.env.PORT ?? 3000);
const first = items?.[0]?.name ?? "none";
console.log(city, port, first);
""")),
    Snippet(_L, "Mid", "Group by role", code(r"""
const byRole = users.reduce((groups, user) => {
  (groups[user.role] ??= []).push(user.name);
  return groups;
}, {});
""")),
    Snippet(_L, "Senior", "Memoize with a closure", code(r"""
function memoize(fn) {
  const cache = new Map();
  return (...args) => {
    const key = JSON.stringify(args);
    if (!cache.has(key)) cache.set(key, fn(...args));
    return cache.get(key);
  };
}
""")),
    Snippet(_L, "Senior", "Generator take", code(r"""
function* take(iterable, n) {
  let i = 0;
  for (const item of iterable) {
    if (i++ >= n) return;
    yield item;
  }
}
""")),
    Snippet(_L, "Senior", "Concurrency-limited runner", code(r"""
async function runLimited(items, limit, fn) {
  let next = 0;
  const worker = async () => {
    while (next < items.length) await fn(items[next++]);
  };
  await Promise.all(Array.from({ length: limit }, worker));
}
""")),
)
