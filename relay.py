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
STATE = Path(__file__).with_name(os.environ.get("STATE_FILE", "state.json"))
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
        user = fetch(f"/users/by/username/{HANDLE}")["data"]
        print(f"watching @{user['username']} ({user['name']}), id {user['id']}")
        state["user_id"] = user["id"]
        state["username"] = user["username"]

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


VISUAL = {"photo", "video", "animation", "sticker", "video_note"}
NON_VISUAL = {"text", "poll", "voice", "audio", "document", "contact", "location", "venue", "dice", "game"}


def is_visual(msg):
    doc = msg.get("document")
    if doc and doc.get("mime_type", "").startswith(("image/", "video/")):
        return True
    return bool(VISUAL & msg.keys()) or not (NON_VISUAL & msg.keys())  # service messages count as fine


def sweep(state, call, chat_id, thread_id):
    """Delete non-visual member messages in the visual-only topic. Returns count deleted."""
    params = {"allowed_updates": json.dumps(["message"]), "timeout": 0}
    if "tg_offset" in state:
        params["offset"] = state["tg_offset"]
    updates = call("getUpdates", params)
    if updates:
        state["tg_offset"] = updates[-1]["update_id"] + 1
    bad = [u["message"] for u in updates if "message" in u
           and str(u["message"]["chat"]["id"]) == str(chat_id)
           and str(u["message"].get("message_thread_id")) == str(thread_id)
           and not is_visual(u["message"])]
    if not bad:
        return 0
    admins = {a["user"]["id"] for a in call("getChatAdministrators", {"chat_id": chat_id})}
    deleted = 0
    for m in bad:
        if m.get("from", {}).get("id") in admins or "sender_chat" in m:  # admins and anonymous admins may post anything
            continue
        call("deleteMessage", {"chat_id": chat_id, "message_id": m["message_id"]})
        deleted += 1
    return deleted


def tg_call(method, params):
    url = f"https://api.telegram.org/bot{os.environ['TG_BOT_TOKEN']}/{method}"
    with urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(params).encode()), timeout=20) as r:
        return json.load(r)["result"]


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    try:
        sent = relay(state, x_get, tg_send)
        print(f"relayed {sent} post(s)")
        if os.environ.get("TG_VISUAL_THREAD_ID"):
            me = tg_call("getChatMember", {"chat_id": os.environ["TG_CHAT_ID"], "user_id": tg_call("getMe", {})["id"]})
            print(f"bot status: {me['status']}, can delete: {me.get('can_delete_messages', False)}")
            # ponytail: runs on the 5-15 min schedule, so text sits there until the next run; a webhook makes it instant
            print(f"deleted {sweep(state, tg_call, os.environ['TG_CHAT_ID'], os.environ['TG_VISUAL_THREAD_ID'])} non-visual message(s)")
    finally:
        STATE.write_text(json.dumps(state, indent=2) + "\n")


if __name__ == "__main__":
    main()
