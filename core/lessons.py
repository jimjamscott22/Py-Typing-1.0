from typing import List
from core.models import Lesson

def build_lessons() -> List[Lesson]:
    """Return the default ordered list of typing lessons."""
    return [
        Lesson(
            title="Home Row - Basic",
            description="Learn the home row keys: ASDF JKL;",
            texts=[
                "aaa sss ddd fff jjj kkk lll ;;;",
                "asdf jkl; asdf jkl; asdf jkl;",
                "sad lad fad jak ask fall",
                "a sad lass asks a lad",
            ],
        ),
        Lesson(
            title="Home Row - Words",
            description="Practice common words using home row",
            texts=[
                "fall fall sass sass flask flask",
                "a lass asks a lad",
                "a sad salad falls",
                "dad falls; a lass asks",
            ],
        ),
        Lesson(
            title="Top Row - Basic",
            description="Add top row: QWER UIOP",
            texts=[
                "qqq www eee rrr uuu iii ooo ppp",
                "qwer uiop qwer uiop",
                "ripe wire pier quip",
                "a wise old owl",
            ],
        ),
        Lesson(
            title="Top Row - Words",
            description="Practice with top and home row combined",
            texts=[
                "quiet quail ripe pepper",
                "power wire require",
                "a wise old owl sees all",
                "please lower your pier",
            ],
        ),
        Lesson(
            title="Bottom Row - Basic",
            description="Add bottom row: ZXCV BNM",
            texts=[
                "zzz xxx ccc vvv bbb nnn mmm",
                "zxcv bnm zxcv bnm",
                "cave maze calm",
                "a brave man",
            ],
        ),
        Lesson(
            title="All Rows Combined",
            description="Practice all letter keys together",
            texts=[
                "the quick brown fox jumps",
                "a brave knight conquers",
                "maximum velocity achieved",
                "complex problems require patience",
            ],
        ),
        Lesson(
            title="Common Words",
            description="Practice frequently used English words",
            texts=[
                "the and for are but not you all can her was one",
                "there would their which about time these people",
                "many then them write like other into first water",
                "could make than been call find long down day get",
            ],
        ),
        Lesson(
            title="Random Words",
            description="Practice with a generated stream of common words (randomized each time)",
            texts=["__RANDOM__"],
        ),
        Lesson(
            title="Sentences - Easy",
            description="Type complete sentences for fluency",
            texts=[
                "The cat sat on the mat.",
                "She can run very fast.",
                "I like to read books.",
                "The sun rises in the east.",
            ],
        ),
        Lesson(
            title="Sentences - Medium",
            description="More complex sentences with punctuation",
            texts=[
                "Practice makes perfect, so keep typing every day.",
                "Learning to type without looking takes time and patience.",
                "The quick brown fox jumps over the lazy dog.",
                "Technology has changed how we communicate with each other.",
            ],
        ),
        Lesson(
            title="Speed Challenge",
            description="Test your speed with longer passages",
            texts=[
                (
                    "Touch typing is a valuable skill that can significantly improve your productivity. "
                    "By learning to type without looking at the keyboard, you can focus more on your thoughts and less on finding keys."
                ),
                (
                    "The key to becoming a proficient typist is consistent practice. Start slowly, focusing on accuracy rather than speed. "
                    "As your muscle memory develops, your speed will naturally increase over time."
                ),
                (
                    "Many professional typists can type over one hundred words per minute. "
                    "While this may seem impressive, remember that everyone starts as a beginner. "
                    "With dedication and regular practice, you too can achieve high typing speeds."
                ),
            ],
        ),
    ]
