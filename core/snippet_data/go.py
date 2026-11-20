"""Go snippets (indented with spaces, not tabs, so they are typeable)."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "Go"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Sum a slice", code(r"""
nums := []int{3, 1, 4, 1, 5}
sum := 0
for _, n := range nums {
    sum += n
}
fmt.Println("sum:", sum)
""")),
    Snippet(_L, "Junior", "Count words in a map", code(r"""
counts := make(map[string]int)
for _, word := range strings.Fields(text) {
    counts[word]++
}
fmt.Println(counts["go"])
""")),
    Snippet(_L, "Junior", "Multiple return values", code(r"""
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("divide by zero")
    }
    return a / b, nil
}
""")),
    Snippet(_L, "Mid", "Struct with a method", code(r"""
type Account struct {
    Owner   string
    Balance float64
}

func (a *Account) Deposit(amount float64) {
    a.Balance += amount
}
""")),
    Snippet(_L, "Mid", "Wrapping errors", code(r"""
func load(path string) ([]byte, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("load %s: %w", path, err)
    }
    return data, nil
}
""")),
    Snippet(_L, "Mid", "Defer and a scanner", code(r"""
f, err := os.Open("data.txt")
if err != nil {
    log.Fatal(err)
}
defer f.Close()
scanner := bufio.NewScanner(f)
""")),
    Snippet(_L, "Senior", "Goroutines with a WaitGroup", code(r"""
var wg sync.WaitGroup
for _, url := range urls {
    wg.Add(1)
    go func() { defer wg.Done(); fetch(url) }()
}
wg.Wait()
""")),
    Snippet(_L, "Senior", "Select with a timeout", code(r"""
select {
case msg := <-messages:
    fmt.Println("received", msg)
case <-time.After(time.Second):
    fmt.Println("timeout")
}
""")),
    Snippet(_L, "Senior", "Generic Map function", code(r"""
func Map[T, U any](items []T, fn func(T) U) []U {
    out := make([]U, 0, len(items))
    for _, item := range items {
        out = append(out, fn(item))
    }
    return out
}
""")),
)
