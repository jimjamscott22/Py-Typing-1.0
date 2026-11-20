"""Python snippets (each one must pass `ast.parse`)."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "Python"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Comprehension with a filter", code(r"""
numbers = [1, 2, 3, 4, 5, 6]
evens = [n * n for n in numbers if n % 2 == 0]
print(f"Even squares: {evens}")
""")),
    Snippet(_L, "Junior", "Read non-empty lines", code(r"""
with open("notes.txt", encoding="utf-8") as handle:
    lines = [ln.strip() for ln in handle if ln.strip()]
print(f"{len(lines)} non-empty lines")
""")),
    Snippet(_L, "Junior", "Count words with a dict", code(r"""
counts = {}
for word in text.split():
    counts[word] = counts.get(word, 0) + 1
print(sorted(counts.items(), key=lambda item: -item[1])[:3])
""")),
    Snippet(_L, "Mid", "Dataclass with defaults", code(r"""
from dataclasses import dataclass, field

@dataclass
class Order:
    id: int
    items: list[str] = field(default_factory=list)
    paid: bool = False
""")),
    Snippet(_L, "Mid", "Chunked file generator", code(r"""
def read_chunks(path, size=1024):
    with open(path, "rb") as handle:
        while chunk := handle.read(size):
            yield chunk
""")),
    Snippet(_L, "Mid", "Call-counting decorator", code(r"""
def counted(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return fn(*args, **kwargs)
    wrapper.calls = 0
    return wrapper
""")),
    Snippet(_L, "Senior", "Gather with a timeout", code(r"""
async def fetch_all(urls):
    async with asyncio.timeout(10):
        res = await asyncio.gather(
            *map(fetch, urls), return_exceptions=True
        )
    return [r for r in res if not isinstance(r, Exception)]
""")),
    Snippet(_L, "Senior", "Protocol with a generic function", code(r"""
from typing import Protocol

class Comparable(Protocol):
    def __lt__(self, other, /) -> bool: ...

def largest[T: Comparable](items: list[T]) -> T:
    return max(items)
""")),
    Snippet(_L, "Senior", "Regex named groups", code(r"""
import re

RE = re.compile(r"(?P<ip>[\d.]+) \[(?P<ts>[^\]]+)\]")

def parse(line: str) -> dict[str, str] | None:
    match = RE.search(line)
    return match.groupdict() if match else None
""")),
)
