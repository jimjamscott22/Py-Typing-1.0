"""Rust snippets."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "Rust"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Match on an Option", code(r"""
fn describe(n: Option<i32>) -> String {
    match n {
        Some(v) if v < 0 => format!("negative {v}"),
        Some(v) => format!("value {v}"),
        None => String::from("nothing"),
    }
}
""")),
    Snippet(_L, "Junior", "Average of a Vec", code(r"""
fn main() {
    let scores = vec![72, 85, 90];
    let total: i32 = scores.iter().sum();
    println!("Average: {}", total as f64 / scores.len() as f64);
}
""")),
    Snippet(_L, "Junior", "Mutable string and chars", code(r"""
let mut greeting = String::from("Hello");
greeting.push_str(", world");
for (i, ch) in greeting.chars().enumerate() {
    if i % 2 == 0 { print!("{ch}"); }
}
""")),
    Snippet(_L, "Mid", "Struct with impl", code(r"""
struct Rect { width: f64, height: f64 }

impl Rect {
    fn area(&self) -> f64 {
        self.width * self.height
    }
}
""")),
    Snippet(_L, "Mid", "Result and the ? operator", code(r"""
use std::fs;
use std::io;

fn read_port(path: &str) -> Result<u16, io::Error> {
    let text = fs::read_to_string(path)?;
    text.trim().parse().map_err(|e| io::Error::other(e))
}
""")),
    Snippet(_L, "Mid", "HashMap entry counting", code(r"""
use std::collections::HashMap;

let mut counts: HashMap<&str, usize> = HashMap::new();
for word in text.split_whitespace() {
    *counts.entry(word).or_insert(0) += 1;
}
""")),
    Snippet(_L, "Senior", "Lifetimes", code(r"""
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

struct Parser<'a> {
    input: &'a str,
}
""")),
    Snippet(_L, "Senior", "Generic trait bound", code(r"""
use std::fmt::Display;

fn print_all<T: Display, I: IntoIterator<Item = T>>(items: I) {
    for item in items {
        println!("{item}");
    }
}
""")),
    Snippet(_L, "Senior", "Arc and Mutex across threads", code(r"""
let counter = Arc::new(Mutex::new(0));
let handles: Vec<_> = (0..4).map(|_| {
    let counter = Arc::clone(&counter);
    thread::spawn(move || *counter.lock().unwrap() += 1)
}).collect();
for handle in handles { handle.join().unwrap(); }
""")),
)
