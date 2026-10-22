# bandit-x-relay

Posts every new @banditdotbot post on X into the Bandit Telegram group. Part of $BANDIT (planning hub `~/bandit`).

- `relay.py`: Python, no dependencies. Reads X API v2 (pay-per-use, ~$0.005 per post read) and sends through the @banditdotbot Telegram bot.
- `.github/workflows/relay.yml`: runs every 5 min (GitHub fires late, so expect 5–15 min). Commits `state.json` back to the repo after each run.
- `state.json`: X user id + last relayed post id. Delete `last_id` to re-baseline. The first run posts nothing.
- Replies and retweets are skipped. Quote posts go through.
- Test: `python3 test_relay.py`

## Secrets (GitHub repo → Settings → Secrets and variables → Actions)
- `X_BEARER_TOKEN`: console.x.com → app → Keys and tokens → Bearer Token. Ed pastes it, never in chat.
- `TG_BOT_TOKEN`: from Ed's @BotFather chat. Ed pastes it, never in chat.
- `TG_CHAT_ID`: group id, `-100…`. From a message link `t.me/c/<N>/<topic>/<msg>` → `-100<N>`.
- `TG_THREAD_ID`: topic id (the `<topic>` part). Blank = General.

## Gotchas
- @banditdotbot must be a group admin to post (Rose locks links + bots for non-admins). Closed topics also need admin.
- Repo is public so Actions minutes are free; private repos get 2,000 min/mo, and this needs ~8,600. Code holds no secrets.
- GitHub pauses scheduled jobs after 60 days with no commits. A quiet X account (no new posts → no state commits) will trip this; re-enable under the Actions tab.
- If the state push fails, the next run can re-send that post (rare).

## Status 2026-10-21
- Repo public: https://github.com/bongle404/bandit-x-relay . Workflow DISABLED until secrets are set (`gh workflow enable relay.yml`).
- Set: TG_CHAT_ID = -1004354910101 (group "Bandit's Garage"), TG_THREAD_ID = 21 (topic "X Posts", created 10-21).
- 10-22: bot admin DONE (Ed). X dev account exists ("Bandit", app on Pay Per Use, $0 balance, no card on file; X matches first purchase up to $20). Ed to do: buy credits, copy bearer token, set X_BEARER_TOKEN + TG_BOT_TOKEN.
- 10-22: LIVE + verified (tweet landed in X Posts). Topic rules (Ed): Announcements + X Posts closed (admins only, reactions OK); Build Log closed, engineer posts as admin; Content (thread 4) visual-only, enforced by `sweep()` each run (deletes text/links/files/polls from non-admins, 5–15 min lag); General = the only open chat. Bot needs "Delete messages" admin right for the sweep.
