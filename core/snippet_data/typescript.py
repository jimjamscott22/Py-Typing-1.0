"""TypeScript snippets."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "TypeScript"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Filter and map users", code(r"""
const activeNames = users
  .filter((user) => user.isActive && user.age >= 18)
  .map((user) => user.name.trim());
""")),
    Snippet(_L, "Junior", "Async fetch helper", code(r"""
async function loadUser(id: string): Promise<User | null> {
  const res = await fetch(`/api/users/${id}`);
  if (!res.ok) return null;
  return (await res.json()) as User;
}
""")),
    Snippet(_L, "Junior", "Interface and distance", code(r"""
interface Point {
  x: number;
  y: number;
}
const distance = (a: Point, b: Point): number =>
  Math.hypot(a.x - b.x, a.y - b.y);
""")),
    Snippet(_L, "Mid", "Debounce function", code(r"""
function debounce(fn: (...a: unknown[]) => void, ms = 300) {
  let id: ReturnType<typeof setTimeout>;
  return (...args: unknown[]) => {
    clearTimeout(id);
    id = setTimeout(() => fn(...args), ms);
  };
}
""")),
    Snippet(_L, "Mid", "Discriminated union", code(r"""
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "rect"; width: number; height: number };

const area = (s: Shape) =>
  s.kind === "circle" ? Math.PI * s.radius ** 2
    : s.width * s.height;
""")),
    Snippet(_L, "Mid", "Parallel loading with Promise.all", code(r"""
async function loadDashboard(id: string) {
  const [user, orders] = await Promise.all([
    fetchUser(id), fetchOrders(id),
  ]);
  const total = orders.reduce((s, o) => s + o.amount, 0);
  return { user, total };
}
""")),
    Snippet(_L, "Senior", "Deep readonly mapped type", code(r"""
type DeepReadonly<T> = {
  readonly [K in keyof T]: T[K] extends object
    ? DeepReadonly<T[K]>
    : T[K];
};

type Config = DeepReadonly<{ db: { host: string } }>;
""")),
    Snippet(_L, "Senior", "Key type guard", code(r"""
function hasKey<T extends object>(
  obj: T,
  key: PropertyKey,
): key is keyof T {
  return key in obj;
}
""")),
    Snippet(_L, "Senior", "Generic pick helper", code(r"""
function pick<T, K extends keyof T>(obj: T, keys: K[]) {
  const entries = keys.map((k) => [k, obj[k]] as const);
  return Object.fromEntries(entries) as Pick<T, K>;
}
""")),
)
