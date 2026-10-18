import os
os.environ["DB_PATH"] = ":memory:"
os.environ["GROQ_API_KEY"] = ""          # force fallback path -> deterministic tests
from fastapi.testclient import TestClient
from app.main import app
from app.modes import detect_mode, extract_name
from app.curriculum import ChildState, is_correct

c = TestClient(app)

def test_name(): assert extract_name("my name is shanto") == "Shanto"
def test_support_mode(): assert detect_mode("I am sad", ChildState("x"))[0] == "SUPPORT"
def test_engagement_mode(): assert detect_mode("I am bored", ChildState("x"))[0] == "ENGAGEMENT"
def test_conversation_mode(): assert detect_mode("hello", ChildState("x"))[0] == "CONVERSATION"
def test_correct(): assert is_correct("it is a cat!", "cat") and not is_correct("dog", "cat")
def test_plural_phrase(): assert is_correct("i like apple", "I like apples")

def test_flow_and_level_up():
    r = c.post("/chat", json={"child_id": "t1", "message": "my name is shanto"}).json()
    assert r["mode"] == "CONVERSATION" and r["latency_ms"] < 2000
    r = c.post("/chat", json={"child_id": "t1", "message": "teach me"}).json()
    assert r["mode"] == "LEARNING" and r["target"]
    r = c.post("/chat", json={"child_id": "t1", "message": "i am scared"}).json()
    assert r["mode"] == "SUPPORT" and r["target"] == ""      # no teaching during support
    for _ in range(40):                                        # answer correctly until leveled
        t = c.post("/chat", json={"child_id": "t1", "message": "teach me"}).json()["target"]
        r = c.post("/chat", json={"child_id": "t1", "message": t}).json()
        if r["leveled_up"]: break
        c.post("/chat", json={"child_id": "t1", "message": "hello"})  # break resets drill streak
    assert r["level"] == 2
