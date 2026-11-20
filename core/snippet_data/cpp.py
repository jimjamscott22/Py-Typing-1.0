"""C++ snippets."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "C++"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Range-for over a vector", code(r"""
std::vector<int> nums{3, 1, 4, 1, 5};
int sum = 0;
for (int n : nums) {
    sum += n;
}
std::cout << "sum: " << sum << '\n';
""")),
    Snippet(_L, "Junior", "Function with a default argument", code(r"""
std::string greet(const std::string& name, int times = 1) {
    std::string out;
    for (int i = 0; i < times; ++i) out += "Hi " + name;
    return out;
}
""")),
    Snippet(_L, "Junior", "Struct in a map", code(r"""
struct Point { int x; int y; };

std::map<std::string, Point> places;
places["home"] = {0, 0};
places["work"] = {3, 4};
""")),
    Snippet(_L, "Mid", "Class with a constructor", code(r"""
class Counter {
public:
    explicit Counter(int start) : value_(start) {}
    int next() { return ++value_; }
private:
    int value_;
};
""")),
    Snippet(_L, "Mid", "unique_ptr ownership", code(r"""
auto widget = std::make_unique<Widget>("main");
widget->show();
std::vector<std::unique_ptr<Widget>> panels;
panels.push_back(std::move(widget));
""")),
    Snippet(_L, "Mid", "Lambdas with algorithms", code(r"""
std::vector<int> v{5, 2, 9, 1};
auto desc = [](int a, int b) { return a > b; };
std::sort(v.begin(), v.end(), desc);
auto small = [](int n) { return n < 3; };
auto it = std::find_if(v.begin(), v.end(), small);
""")),
    Snippet(_L, "Senior", "Template with a comparator", code(r"""
template <typename T, typename Compare = std::less<T>>
T clamp_to(T v, T lo, T hi, Compare cmp = Compare{}) {
    if (cmp(v, lo)) return lo;
    if (cmp(hi, v)) return hi;
    return v;
}
""")),
    Snippet(_L, "Senior", "RAII file handle", code(r"""
struct FileHandle {
    std::FILE* f;
    FileHandle(const char* p) : f(std::fopen(p, "r")) {}
    ~FileHandle() { if (f) std::fclose(f); }
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;
};
""")),
    Snippet(_L, "Senior", "Move constructor", code(r"""
struct Buffer {
    char* data_;
    std::size_t size_;
    Buffer(Buffer&& o) noexcept
        : data_(std::exchange(o.data_, nullptr)),
          size_(o.size_) {}
};
""")),
)
