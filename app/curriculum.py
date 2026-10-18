"""Progressive curriculum (L1-L3) + mastery tracking. No LLM needed: zero latency."""
import re
from dataclasses import dataclass, field, asdict

# Each item: (target text, emoji, teaching hint)
LEVELS = {
    1: [  # single words
        ("apple", "🍎", "a red fruit"), ("cat", "🐱", "says meow"),
        ("dog", "🐶", "says woof"), ("red", "🔴", "the color of an apple"),
        ("blue", "🔵", "the color of the sky"), ("ball", "⚽", "we kick it"),
    ],
    2: [  # short phrases
        ("I see a cat", "🐱", "say what you see"), ("I like apples", "🍎", "say what you like"),
        ("this is red", "🔴", "name a color"), ("I have a ball", "⚽", "say what you have"),
        ("it is big", "🐘", "describe size"), ("I am happy", "😊", "say how you feel"),
    ],
    3: [  # simple sentences / questions
        ("what is your name", "🧒", "ask a friend's name"), ("I can jump high", "🦘", "say what you can do"),
        ("where is the dog", "🐶", "ask where something is"), ("I like to play", "🎈", "say what you like to do"),
        ("the sun is hot", "☀️", "describe the weather"), ("how are you today", "👋", "ask how a friend feels"),
    ],
}
MASTER_AT = 2      # correct answers needed to master an item
PROMOTE_AT = 4     # mastered items needed to unlock next level


@dataclass
class ChildState:
    child_id: str
    name: str = ""
    level: int = 1
    mastery: dict = field(default_factory=dict)      # item -> correct count
    attempts: dict = field(default_factory=dict)     # item -> tries
    pending: str = ""                                # item currently being asked
    streak_learning: int = 0                         # consecutive learning turns
    stars: int = 0
    last_emotion: str = "neutral"
    history: list = field(default_factory=list)      # [{"role","content"}], last 6 turns

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d): return cls(**d)


def _tokens(s): return re.findall(r"[a-z']+", s.lower())


def is_correct(answer: str, target: str) -> bool:
    """Lenient check for small children: all words (L1) or >=75% of target words (L2/L3)."""
    t, a = _tokens(target), set(_tokens(answer))
    if not t: return False
    hit = sum(1 for w in t if w in a or (w.endswith("s") and w[:-1] in a) or (w + "s") in a)
    return hit / len(t) >= (1.0 if len(t) == 1 else 0.75)


def items(level): return LEVELS[level]


def mastered(state: ChildState, level=None):
    lvl = level or state.level
    return [i for i, *_ in LEVELS[lvl] if state.mastery.get(i, 0) >= MASTER_AT]


def next_item(state: ChildState):
    """Pick the least-mastered item of the current level (spaced repetition-lite)."""
    pool = LEVELS[state.level]
    return min(pool, key=lambda it: (state.mastery.get(it[0], 0), state.attempts.get(it[0], 0)))


def record_answer(state: ChildState, correct: bool):
    """Update mastery for the pending item. Returns (leveled_up, mastered_now)."""
    item = state.pending
    if not item: return False, False
    state.attempts[item] = state.attempts.get(item, 0) + 1
    was = state.mastery.get(item, 0) >= MASTER_AT
    if correct:
        state.mastery[item] = state.mastery.get(item, 0) + 1
        state.stars += 1
    now = state.mastery.get(item, 0) >= MASTER_AT
    leveled = False
    if state.level < 3 and len(mastered(state)) >= PROMOTE_AT:
        state.level += 1
        leveled = True
    return leveled, (now and not was)
