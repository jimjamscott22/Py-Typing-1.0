"""HTML and CSS snippets."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "HTML/CSS"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Semantic page skeleton", code(r"""
<main>
  <h1>Typing Practice</h1>
  <p>Type the text below.</p>
  <button type="button">Start</button>
</main>
""")),
    Snippet(_L, "Junior", "Card rule", code(r"""
.card {
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 8px;
}
""")),
    Snippet(_L, "Junior", "Link hover style", code(r"""
a {
  color: #0366d6;
  text-decoration: none;
}
a:hover { text-decoration: underline; }
""")),
    Snippet(_L, "Mid", "Flexbox toolbar", code(r"""
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
""")),
    Snippet(_L, "Mid", "Form with attributes", code(r"""
<form action="/signup" method="post">
  <label for="email">Email</label>
  <input id="email" name="email" type="email" required>
  <button type="submit">Join</button>
</form>
""")),
    Snippet(_L, "Mid", "Responsive media query", code(r"""
.layout { display: grid; gap: 1rem; }

@media (min-width: 768px) {
  .layout { grid-template-columns: 1fr 2fr; }
}
""")),
    Snippet(_L, "Senior", "Grid template areas", code(r"""
.page {
  display: grid;
  grid-template-areas:
    "header header"
    "nav    main";
  grid-template-columns: 200px 1fr;
}
""")),
    Snippet(_L, "Senior", "Custom properties and selectors", code(r"""
:root {
  --accent: #3b82f6;
  --radius: 0.5rem;
}
.btn:is(:hover, :focus-visible):not(:disabled) {
  background: color-mix(in srgb, var(--accent) 85%, black);
}
""")),
    Snippet(_L, "Senior", "Keyframes animation", code(r"""
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
.badge { animation: pulse 2s ease-in-out infinite; }
""")),
)
