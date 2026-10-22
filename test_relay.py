"""Run: python3 test_relay.py"""
from relay import relay

USER = {"data": {"id": "42", "username": "banditdotbot", "name": "Bandit"}}


def fake_x(timeline):
    calls = []

    def fetch(path, params=None):
        calls.append((path, params))
        return USER if "by/username" in path else {"data": timeline} if timeline else {"meta": {"result_count": 0}}

    return fetch, calls


# First run: sets a baseline, sends nothing.
state, sent = {}, []
fetch, _ = fake_x([{"id": "300", "text": "c"}, {"id": "200", "text": "b"}])
assert relay(state, fetch, sent.append) == 0 and sent == []
assert state == {"user_id": "42", "username": "banditdotbot", "last_id": "300"}

# New posts arrive newest-first from X; they go out oldest-first.
fetch, calls = fake_x([{"id": "1000", "text": "new2"}, {"id": "900", "text": "new1"}])
assert relay(state, fetch, sent.append) == 2
assert sent[0].startswith("new1") and sent[1].startswith("new2")
assert sent[0].endswith("https://x.com/banditdotbot/status/900")
assert state["last_id"] == "1000"
assert calls == [("/users/42/tweets", {"exclude": "replies,retweets", "max_results": 100, "since_id": "300"})]  # no repeat profile lookup

# Nothing new: nothing sent, state unchanged.
fetch, _ = fake_x([])
assert relay(state, fetch, sent.append) == 0 and state["last_id"] == "1000"

# Send fails on the 2nd post: last_id stops at the 1st, so it isn't re-sent next run.
def flaky(text, n=[0]):
    n[0] += 1
    if n[0] == 2:
        raise OSError("telegram down")

fetch, _ = fake_x([{"id": "1200", "text": "y"}, {"id": "1100", "text": "x"}])
try:
    relay(state, fetch, flaky)
except OSError:
    pass
assert state["last_id"] == "1100"

# Very long post gets trimmed under Telegram's limit.
fetch, _ = fake_x([{"id": "1300", "text": "a" * 5000}])
relay(state, fetch, sent.append)
assert len(sent[-1]) < 4096

# Visual-only topic sweep.
from relay import sweep


def msg(uid, thread, user, **content):
    return {"update_id": uid, "message": {"message_id": uid, "chat": {"id": -100}, "message_thread_id": thread, "from": {"id": user}, **content}}


updates = [
    msg(1, 4, 7, text="gm"),                                        # text in Content -> delete
    msg(2, 4, 7, photo=[{}], caption="look"),                       # photo -> keep
    msg(3, 4, 7, document={"mime_type": "application/pdf"}),        # pdf -> delete
    msg(4, 4, 7, document={"mime_type": "video/mp4"}),              # video file -> keep
    msg(5, 4, 99, text="admin note"),                               # admin -> keep
    msg(6, 1, 7, text="hi"),                                        # other topic -> keep
    msg(7, 4, 7, sticker={}),                                       # sticker -> keep
    msg(8, 4, 7, forum_topic_edited={}),                            # service msg -> keep
]
deleted, st = [], {}


def call(method, params):
    if method == "getUpdates":
        return updates
    if method == "getChatAdministrators":
        return [{"user": {"id": 99}}]
    deleted.append(params["message_id"])


assert sweep(st, call, -100, 4) == 2 and deleted == [1, 3]
assert st["tg_offset"] == 9

print("ok")
