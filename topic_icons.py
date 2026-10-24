#!/usr/bin/env python3
"""One-off: set forum topic icons. TOPIC_ICONS="4=🎬,21=📰" (topic id = emoji from Telegram's free icon set)."""
import os
from relay import tg_call

icons = {s["emoji"].replace("️", ""): s["custom_emoji_id"] for s in tg_call("getForumTopicIconStickers", {})}
print("available:", " ".join(icons))
for pair in filter(None, os.environ.get("TOPIC_ICONS", "").split(",")):
    tid, emoji = pair.split("=")
    eid = icons.get(emoji.strip().replace("️", ""))
    if not eid:
        print(f"topic {tid}: {emoji} not in free set, skipped")
        continue
    try:
        tg_call("editForumTopic", {"chat_id": os.environ["TG_CHAT_ID"], "message_thread_id": tid.strip(), "icon_custom_emoji_id": eid})
        print(f"topic {tid}: set {emoji}")
    except Exception as e:
        print(f"topic {tid}: failed {e} {getattr(e, 'read', lambda: b'')().decode()}")
