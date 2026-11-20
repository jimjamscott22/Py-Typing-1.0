"""Per-language snippet data modules, collected into `ALL`.

Each language module exports `SNIPPETS: tuple[Snippet, ...]`. Import them
statically here (PyInstaller cannot see dynamic imports) and add them to `ALL`.
"""

from core.models import Snippet

ALL: tuple[Snippet, ...] = ()
