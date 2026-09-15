# telegram-notify

One-shot Telegram notifications for coding agents. When a long task finishes, a deploy fails or an
agent needs a decision, it sends **one** self-contained message to your phone through your own bot.

Three ways in, one message format:

| | For | Needs |
| --- | --- | --- |
| `telegram-notify` CLI | any agent or script with a shell | `python3` (stdlib only) |
| `telegram-notify-mcp` server | any MCP client: Claude Code, Cursor, Codex, Gemini CLI… | `uv` |
| Claude Code skill | Claude Code, so it knows when and how to notify | the CLI on PATH |

[GUIDELINES.md](GUIDELINES.md) says what a good message looks like; the skill and the MCP tool
carry the same rules, so every agent writes the same kind of message:

```
✅ turtletrips 1.7.0 desplegado
📁 turtletrips · 🖥️ ginnugagap

Imagen ghcr.io/zurdi15/turtletrips:1.7.0 desplegada en el clúster.
Argo: turtletrips Synced/Healthy. Health: HTTP 200.

Novedades 1.7.0:
- Moneda secundaria por viaje (p. ej. VND), elegible junto a la base en el formulario del viaje.
- En el gasto, la moneda se elige con principal · secundaria · otra.
```

## 1. Bot and chat (once)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Send it any message from the chat that should receive the notifications (your user, or a group
   the bot is in).
3. Find that chat's id: `telegram-notify-setup --token <token> --find-chat` (or open
   `https://api.telegram.org/bot<token>/getUpdates` and look for `"chat":{"id":…}`).

The same bot can serve as many machines and agents as you like.

## 2. Install on a machine

### With uv (recommended)

```bash
uv tool install "telegram-notify[mcp] @ git+https://github.com/zurdi15/telegram-notify"
telegram-notify-setup --token <token> --chat-id <chat_id> --test
```

`setup` writes `~/.config/telegram-notify/notify.env` (mode 600), installs the Claude Code skill
into `~/.claude/skills/telegram-notify/` and sends a test message. Drop `[mcp]` if you only want
the CLI. Upgrade later with `uv tool upgrade telegram-notify`.

### Without uv

The CLI is a single stdlib file, so it can be dropped anywhere with a `python3`:

```bash
curl -fsSL https://raw.githubusercontent.com/zurdi15/telegram-notify/main/telegram_notify/cli.py -o ~/.local/bin/telegram-notify
chmod +x ~/.local/bin/telegram-notify
mkdir -p ~/.config/telegram-notify && printf 'TELEGRAM_BOT_TOKEN=%s\nTELEGRAM_CHAT_ID=%s\n' <token> <chat_id> > ~/.config/telegram-notify/notify.env && chmod 600 ~/.config/telegram-notify/notify.env
```

`pip install git+https://github.com/zurdi15/telegram-notify` works too.

### Credentials

Resolved in this order; the first complete pair wins. They are never written anywhere else, never
logged and never printed.

1. `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the environment.
2. The file named by `TELEGRAM_NOTIFY_ENV`.
3. `~/.config/telegram-notify/notify.env` (what `setup` writes).
4. `~/.config/claude-telegram/notify.env` (legacy path, still read).

File format: `KEY=VALUE`, one per line. In CI, put the two variables in the job's secrets.

## 3. Use it

### CLI

```bash
telegram-notify -s ok -t "immich 1.140 desplegado" -H ginnugagap "Imagen desplegada. Argo Synced/Healthy. Health: HTTP 200."
pytest -q 2>&1 | tail -20 | telegram-notify -s fail -t "Tests rotos en bifrost"     # body from stdin
telegram-notify -s ask -t "Necesito confirmación" "¿Borro el PVC antiguo de immich (40 GB)?"
telegram-notify --dry-run -t "Prueba" "Imprime el mensaje sin enviarlo"
```

| Flag | Meaning |
| --- | --- |
| `-s, --status` | `ok` ✅ · `fail` ❌ · `warn` ⚠️ · `info` ℹ️ · `ask` ❓ — picks the icon and the default title. Default `ok`. |
| `-t, --title` | Headline, first line of the message. |
| `-p, --project` | Project shown in the context line (default: git repo or cwd name). |
| `-H, --host` | Host shown in the context line (default: this machine). Use the deploy target when that is what matters. |
| `--no-context` | Drop the `📁 project · 🖥️ host` line. |
| `--dry-run` | Print the message instead of sending it. |

Exit code `0` means delivered; anything else prints the reason on stderr. Messages are plain text,
capped at Telegram's 4096 characters.

### MCP server

One tool, `notify(title, body, status="ok", project=None, host=None, dry_run=False)`, whose
description and the server instructions carry the message guidelines. Register it once per machine,
user-wide:

```bash
# Claude Code
claude mcp add --scope user telegram-notify -- telegram-notify-mcp
```

Any other MCP client takes the same command in its own config (Cursor `~/.cursor/mcp.json`, Codex
`~/.codex/config.toml`, Gemini CLI `~/.gemini/settings.json`…). Without the tool install, `uvx`
runs it straight from this repository:

```json
{
  "mcpServers": {
    "telegram-notify": {
      "command": "uvx",
      "args": ["--from", "telegram-notify[mcp] @ git+https://github.com/zurdi15/telegram-notify", "telegram-notify-mcp"]
    }
  }
}
```

The server reads the credentials from the same places as the CLI. If your client cannot see your
shell environment, add `"env": {"TELEGRAM_BOT_TOKEN": "…", "TELEGRAM_CHAT_ID": "…"}` there, or
rely on the config file. Pin a revision with `…/telegram-notify@v0.1.0` for reproducible installs.

### Claude Code skill

`telegram-notify-setup` copies [`telegram_notify/SKILL.md`](telegram_notify/SKILL.md) to
`~/.claude/skills/telegram-notify/SKILL.md`. From then on any session, in any project, knows the
tool exists, when to use it and how to write the message. Check with:

```bash
claude -p "Lista los nombres de tus skills disponibles"
```

Other agents that read skill files (or an `AGENTS.md`) can point at the same file: the rules are the
ones in `GUIDELINES.md`.

### Always notify when a turn ends (optional)

A Claude Code `Stop` hook in `~/.claude/settings.json` fires on every turn, trivial ones included;
the skill (the agent decides when it is worth it) is usually better:

```json
{ "hooks": { "Stop": [ { "hooks": [ { "type": "command", "command": "telegram-notify -s ok -t 'Claude ha terminado' 'Turno completado'" } ] } ] } }
```

## Development

```bash
python3 -m unittest discover -s tests     # stdlib only; pytest works too
uv run --extra mcp telegram-notify-mcp    # run the server locally
```

`telegram_notify/cli.py` must stay dependency-free and importable on its own: that is what makes the
curl install and the copy-the-file fallback possible.
