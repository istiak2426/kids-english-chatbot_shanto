import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import curriculum as cur, llm, store
from .modes import detect_mode, extract_name, LEARNING, CONVERSATION, ENGAGEMENT, SUPPORT

app = FastAPI(title="Buddy - English for Kids")
STATIC = Path(__file__).parent.parent / "static"


class ChatIn(BaseModel):
    child_id: str = Field(min_length=1, max_length=64)
    message: str = Field(max_length=300)


SEL_TIPS = {
    "sad": "Acknowledge the feeling kindly ('It's okay to feel sad'). Offer a hug emoji. Do NOT teach. Name the feeling in English (sad).",
    "scared": "Reassure gently, say they are safe, suggest telling a grown-up they trust. Do NOT teach. Name the feeling (scared).",
    "angry": "Validate the feeling, suggest 3 slow deep breaths together. Do NOT teach. Name the feeling (angry).",
    "frustrated": "Say learning can be hard and mistakes are how we grow. Make it easier. Encourage ('You can do it!').",
    "tired": "Be soft and calm. Suggest a rest or a tiny easy word. Do NOT push.",
}
FALLBACKS = {
    "sad": "It's okay to feel sad. 🤗 I'm here with you. Can you take a deep breath?",
    "scared": "You are safe. 💛 Tell a grown-up you trust. Let's breathe slowly together.",
    "angry": "It's okay to feel angry. 🌬️ Let's breathe in... and out. Ready?",
    "frustrated": "It's okay, this is hard! 💪 Mistakes help us grow. Let's try an easy one!",
    "tired": "You look sleepy. 😴 Let's go slow. Want one easy word?",
}


def _directive(mode, state, emotion, item, feedback):
    word, emoji, hint = item
    if mode == SUPPORT:
        return "SUPPORT mode. " + SEL_TIPS.get(emotion, "Be kind and calm.")
    if mode == ENGAGEMENT:
        return (f"ENGAGEMENT mode. Child wants fun or is bored. Play a tiny game, sing a 1-line rhyme, or tell a "
                f"1-sentence joke using the word '{word}'. Keep it silly and playful. No drilling.")
    if mode == CONVERSATION:
        who = f"The child's name is {state.name}. " if state.name else "You don't know the child's name yet; ask it kindly. "
        return (f"CONVERSATION mode. {who}Chat naturally, answer their question simply, show curiosity about "
                f"them. Do NOT quiz. Optionally invite: 'Want to learn a new word?'")
    return (f"LEARNING mode, level {state.level}. FEEDBACK on last answer: {feedback}. "
            f"Now teach/ask ONE item: '{word}' ({hint}) {emoji}. Say it, ask the child to repeat it. "
            f"Use the child's name {state.name or ''} sometimes to build confidence.")


def _fallback(mode, state, emotion, item, feedback):
    word, emoji, _ = item
    n = f" {state.name}" if state.name else ""
    if mode == SUPPORT: return FALLBACKS.get(emotion, "I'm here for you. 🤗")
    if mode == ENGAGEMENT: return f"Let's play! 🎉 Can you shout '{word}' like a lion? Roar! 🦁"
    if mode == CONVERSATION:
        return (f"Hi{n}! 😊 Nice to talk to you. Want to learn a new word?" if state.name
                else "Hello! I'm Buddy. 🧸 What is your name?")
    return f"{feedback} Say after me: '{word}' {emoji}. Your turn!"


@app.post("/chat")
async def chat(body: ChatIn):
    t0 = time.perf_counter()
    state = store.load(body.child_id)
    msg = body.message.strip()

    if (nm := extract_name(msg)): state.name = nm
    mode, emotion = detect_mode(msg, state)
    state.last_emotion = emotion

    feedback, leveled = "Let's start!", False
    if mode == LEARNING:
        if state.pending:
            ok = cur.is_correct(msg, state.pending)
            leveled, _ = cur.record_answer(state, ok)
            feedback = "Correct! Celebrate!" if ok else "Nice try, not quite. Model the right answer."
            if leveled: feedback += f" Child just reached LEVEL {state.level}! Celebrate big."
        state.streak_learning += 1
    else:
        state.streak_learning = 0  # any non-learning turn is a break

    item = cur.next_item(state)
    state.pending = item[0] if mode == LEARNING else ""

    directive = _directive(mode, state, emotion, item, feedback)
    reply = await llm.generate(directive, state.history, msg)
    used_llm = reply is not None
    if not reply: reply = _fallback(mode, state, emotion, item, feedback.split(".")[0] + "!")

    state.history += [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}]
    state.history = state.history[-12:]
    store.save(state)

    return {
        "reply": reply, "mode": mode, "emotion": emotion, "level": state.level, "stars": state.stars,
        "mastered": len(cur.mastered(state)), "level_size": len(cur.items(state.level)),
        "leveled_up": leveled, "target": state.pending, "used_llm": used_llm,
        "latency_ms": round((time.perf_counter() - t0) * 1000),
    }


@app.get("/health")
def health(): return {"ok": True}


@app.get("/")
def index(): return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
