import random
from typing import List

# Expanded common-words list for random drills (~200 words)
_COMMON_WORDS: List[str] = [
    # Articles, pronouns, conjunctions
    "the", "a", "an", "and", "or", "but", "if", "when", "where", "why", "how",
    "I", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "her", "its", "our", "their", "this", "that", "these", "those",
    
    # Common verbs
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might", "can",
    "go", "goes", "went", "gone", "get", "gets", "got", "make", "makes", "made",
    "see", "saw", "seen", "come", "came", "take", "took", "taken", "know", "knew",
    "think", "thought", "say", "said", "tell", "told", "give", "gave", "given",
    "find", "found", "use", "used", "work", "worked", "call", "called", "try", "tried",
    "ask", "asked", "need", "needed", "feel", "felt", "become", "became", "leave", "left",
    "put", "keep", "kept", "begin", "began", "seem", "seemed", "help", "helped",
    "talk", "talked", "turn", "turned", "start", "started", "show", "showed", "shown",
    "hear", "heard", "play", "played", "run", "ran", "move", "moved", "live", "lived",
    "believe", "believed", "bring", "brought", "happen", "happened", "write", "wrote",
    "sit", "sat", "stand", "stood", "lose", "lost", "pay", "paid", "meet", "met",
    
    # Common nouns
    "time", "year", "people", "way", "day", "man", "thing", "woman", "life", "child",
    "world", "school", "state", "family", "student", "group", "country", "problem",
    "hand", "part", "place", "case", "week", "company", "system", "program", "question",
    "work", "government", "number", "night", "point", "home", "water", "room", "mother",
    "area", "money", "story", "fact", "month", "lot", "right", "study", "book", "eye",
    "job", "word", "business", "issue", "side", "kind", "head", "house", "service",
    "friend", "father", "power", "hour", "game", "line", "end", "member", "law", "car",
    "city", "community", "name", "president", "team", "minute", "idea", "kid", "body",
    "information", "back", "parent", "face", "others", "level", "office", "door",
    
    # Common adjectives & adverbs
    "good", "new", "first", "last", "long", "great", "little", "own", "other", "old",
    "right", "big", "high", "different", "small", "large", "next", "early", "young",
    "important", "few", "public", "bad", "same", "able", "best", "better", "sure",
    "clear", "major", "likely", "possible", "available", "free", "real", "hard",
    "easy", "full", "quick", "fast", "slow", "strong", "happy", "sad", "ready",
    
    # Prepositions & others
    "in", "on", "at", "to", "for", "with", "from", "by", "about", "as", "into",
    "through", "during", "before", "after", "above", "below", "between", "under",
    "over", "up", "down", "out", "off", "of", "not", "so", "than", "too", "very",
    "just", "now", "then", "here", "there", "more", "most", "all", "each", "every",
    "both", "some", "many", "much", "any", "no", "only", "also", "well", "back",
]


def generate_text(word_count: int = 25) -> str:
    """Return a random sequence of common words joined by spaces.

    Args:
        word_count: Number of words to generate.

    Returns:
        A single string containing `word_count` words separated by spaces.
    """
    if word_count <= 0:
        return ""
    return " ".join(random.choice(_COMMON_WORDS) for _ in range(word_count))
