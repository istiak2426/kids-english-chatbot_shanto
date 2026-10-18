"""Child mode + emotion detection. Rule-based on purpose: ~0 ms, deterministic, explainable."""
import re
from .curriculum import ChildState

LEARNING, CONVERSATION, ENGAGEMENT, SUPPORT = "LEARNING", "CONVERSATION", "ENGAGEMENT", "SUPPORT"
MAX_LEARNING_STREAK = 3  # then give the child a fun break instead of drilling forever

EMOTIONS = {
    "sad": r"\b(sad|cry|crying|miss (my )?(mom|mommy|dad|daddy)|lonely|hurt)\b",
    "scared": r"\b(scared|afraid|fear|monster|nightmare)\b",
    "angry": r"\b(angry|mad|hate|stupid)\b",
    "frustrated": r"\b(i can'?t|too hard|don'?t know|dont know|difficult|no idea)\b",
    "tired": r"\b(tired|sleepy|sleep|yawn)\b",
    "bored": r"\b(bored|boring|enough)\b",
    "happy": r"\b(happy|yay|fun|love|great|awesome|good)\b",
}
GREETING = r"\b(hi|hello|hey|good (morning|afternoon|evening)|bye|goodbye|my name is|i am called|who are you|what'?s your name)\b"
PLAY = r"\b(play|game|song|sing|joke|story|dance|riddle)\b"
WANT_LEARN = r"\b(teach|learn|lesson|new word|quiz|practice|again)\b"
NAME = re.compile(r"(?:my name is|i am called|i'?m called|name is)\s+([a-zA-Z]+)", re.I)


def detect_emotion(msg: str) -> str:
    m = msg.lower()
    for emo, pat in EMOTIONS.items():
        if re.search(pat, m): return emo
    return "neutral"


def extract_name(msg: str) -> str:
    m = NAME.search(msg)
    return m.group(1).capitalize() if m else ""


def detect_mode(msg: str, state: ChildState):
    """Returns (mode, emotion). Priority: support > engagement > conversation > learning."""
    m, emo = msg.lower().strip(), detect_emotion(msg)
    if emo in ("sad", "scared", "angry", "frustrated", "tired"):
        return SUPPORT, emo
    if emo == "bored" or re.search(PLAY, m):
        return ENGAGEMENT, emo
    if re.search(WANT_LEARN, m):
        return LEARNING, emo
    if state.pending and not re.search(GREETING, m):
        # Child is replying to a question we asked -> keep learning,
        # unless they've been drilled too long -> offer a fun break.
        if state.streak_learning >= MAX_LEARNING_STREAK:
            return ENGAGEMENT, emo
        return LEARNING, emo
    if re.search(GREETING, m) or "?" in m or len(m.split()) > 6:
        return CONVERSATION, emo
    return (CONVERSATION if not state.history else LEARNING), emo
