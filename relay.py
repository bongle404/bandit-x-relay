#!/usr/bin/env python3
"""Relay new @banditdotbot posts on X into the Bandit Telegram group.

Runs every few minutes on GitHub Actions. Remembers the last relayed post in
state.json so each post is sent once. Replies and retweets are skipped.
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

HANDLE = os.environ.get("X_HANDLE", "banditdotbot")
STATE = Path(__file__).with_name("state.json")
X_API = "https://api.x.com/2"


def x_get(path, params=None):
    url = f"{X_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ['X_BEARER_TOKEN']}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def tg_send(text):
    data = {"chat_id": os.environ["TG_CHAT_ID"], "text": text}
    if os.environ.get("TG_THREAD_ID"):
        data["message_thread_id"] = os.environ["TG_THREAD_ID"]
    url = f"https://api.telegram.org/bot{os.environ['TG_BOT_TOKEN']}/sendMessage"
    with urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(data).encode()), timeout=20) as r:
        r.read()


def format_post(post):
    # Telegram caps messages at 4096 chars; long X posts get cut, the link has the rest.
    text = post["text"] if len(post["text"]) <= 3500 else post["text"][:3500] + "…"
    return f"{text}\n\nhttps://x.com/{HANDLE}/status/{post['id']}"


def relay(state, fetch, send):
    """Send posts newer than state['last_id'], oldest first. Mutates state as it goes."""
    if "user_id" not in state:
        # Profile lookups cost more than post reads, so do it once and keep it.
        state["user_id"] = fetch(f"/users/by/username/{HANDLE}")["data"]["id"]

    params = {"exclude": "replies,retweets", "max_results": 5 if "last_id" not in state else 100}
    if "last_id" in state:
        params["since_id"] = state["last_id"]
    posts = fetch(f"/users/{state['user_id']}/tweets", params).get("data", [])

    if "last_id" not in state:
        # First run: mark where we are, don't dump old posts into the group.
        if posts:
            state["last_id"] = max(posts, key=lambda p: int(p["id"]))["id"]
        return 0

    sent = 0
    for post in sorted(posts, key=lambda p: int(p["id"])):
        send(format_post(post))
        state["last_id"] = post["id"]  # saved per post so a mid-run failure never double-posts
        sent += 1
    return sent


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    try:
        sent = relay(state, x_get, tg_send)
        print(f"relayed {sent} post(s)")
    finally:
        STATE.write_text(json.dumps(state, indent=2) + "\n")


if __name__ == "__main__":
    main()
