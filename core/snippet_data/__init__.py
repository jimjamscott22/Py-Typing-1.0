"""Per-language snippet data modules, collected into `ALL`.

Each language module exports `SNIPPETS: tuple[Snippet, ...]`. Import them
statically here (PyInstaller cannot see dynamic imports) and add them to `ALL`.
Order does not matter: `core.snippets` groups by language and tier.
"""

from core.models import Snippet
from core.snippet_data import cpp, go, javascript, python, rust, typescript

ALL: tuple[Snippet, ...] = (
    *typescript.SNIPPETS,
    *javascript.SNIPPETS,
    *python.SNIPPETS,
    *rust.SNIPPETS,
    *go.SNIPPETS,
    *cpp.SNIPPETS,
)
