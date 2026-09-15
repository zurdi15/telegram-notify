---
name: telegram-notify
description: Send a Telegram message to the user from any project. Use when a long-running task finishes, a build/deploy/test run fails, or you need the user's decision while they may be away from the terminal. Triggers - "avísame por Telegram", "notify me on Telegram", "ping me when done", "mándame un mensaje cuando termines", "manda verificación".
allowed-tools: Bash(telegram-notify:*)
---

# Telegram notify

Sends a one-off message to the user's Telegram. Credentials are already on the machine
(`~/.config/telegram-notify/notify.env` or `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`): never ask for
them, never print them.

## Usage

```bash
telegram-notify -s ok -t "<proyecto versión verbo>" "<cuerpo>"
printf '%s\n' "<cuerpo multilínea>" | telegram-notify -s ok -t "<titular>"   # body from stdin
```

If `telegram-notify` is not on PATH: `uvx --from git+https://github.com/zurdi15/telegram-notify telegram-notify …`.
If the `telegram-notify` MCP server is available, its `notify` tool does the same without a shell.

| Flag | Meaning |
|---|---|
| `-s, --status` | `ok` ✅ · `fail` ❌ · `warn` ⚠️ · `info` ℹ️ · `ask` ❓ — icon and default title. Default `ok`. |
| `-t, --title` | Headline, first line. |
| `-p, --project` | Project name (default: git repo or cwd name). |
| `-H, --host` | Host in the context line (default: this machine). Pass the deploy target when that is what matters. |
| `--no-context` | Drop the `📁 project · 🖥️ host` line. |
| `--dry-run` | Print the message instead of sending it. |

## Message guidelines (full text: GUIDELINES.md in the repo)

Shape:

```
✅ turtletrips 1.7.0 desplegado
📁 turtletrips · 🖥️ ginnugagap

Imagen ghcr.io/zurdi15/turtletrips:1.7.0 desplegada en el clúster.
Argo: turtletrips Synced/Healthy. Health: HTTP 200.

Novedades 1.7.0:
- Moneda secundaria por viaje (p. ej. VND), elegible junto a la base en el formulario del viaje.
- En el gasto, la moneda se elige con principal · secundaria · otra.
```

- **Title**: `proyecto versión verbo`, past tense, no trailing period. The icon comes from `-s`.
- **Body**, in this order: what was done (with the identifiers to check it: image, tag, commit); how it
  was verified (Argo state, HTTP code, tests green — say it if something could not be verified); on a
  release, `Novedades X.Y.Z:` with one `- ` line per change written for the app's user, not the code
  reader; the next step or, with `ask`, the concrete question.
- Spanish (unless the user writes in another language). Plain text: no Markdown, no code blocks.
- Self-contained and short — it is read on a phone without the terminal. Hard cap 4096 characters.
- **One** message per task, when it is actually finished or blocked. No progress pings unless asked.
- No secrets, tokens or full file contents. `fail` carries the exact error and where.
- Exit `0` = delivered. Non-zero prints the reason on stderr: tell the user in the terminal, do not retry in a loop.
