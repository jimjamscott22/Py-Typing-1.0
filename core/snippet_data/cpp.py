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
    for (int i = 0; i < times; ++i) out += "Hello, " + name + "! ";
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
std::sort(v.begin(), v.end(), [](int a, int b) { return a > b; });
auto it = std::find_if(v.begin(), v.end(), [](int n) { return n < 3; });
""")),
    Snippet(_L, "Senior", "Template with a comparator", code(r"""
template <typename T, typename Compare = std::less<T>>
T clamp_value(T value, T low, T high, Compare cmp = Compare{}) {
    if (cmp(value, low)) return low;
    if (cmp(high, value)) return high;
    return value;
}
""")),
    Snippet(_L, "Senior", "RAII file handle", code(r"""
class FileHandle {
public:
    FileHandle(const char* p) : file_(std::fopen(p, "r")) {}
    ~FileHandle() { if (file_) std::fclose(file_); }
    FileHandle(const FileHandle&) = delete;
private:
    std::FILE* file_;
};
""")),
    Snippet(_L, "Senior", "Move constructor", code(r"""
class Buffer {
public:
    Buffer(Buffer&& other) noexcept
        : data_(std::exchange(other.data_, nullptr)),
          size_(other.size_) {}
private:
    char* data_; std::size_t size_;
};
""")),
)
