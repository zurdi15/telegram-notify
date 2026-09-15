#!/usr/bin/env python3
"""telegram-notify — send a one-off Telegram message from any agent or script.

Standalone: only the Python standard library, so this single file can be
copied anywhere and run with the system ``python3``. Credentials come from the
environment or from a ``KEY=VALUE`` file (see :func:`load_config`).

Message shape (see GUIDELINES.md in the repo)::

    ✅ turtletrips 1.7.0 desplegado
    📁 turtletrips · 🖥️ ginnugagap

    <body: what happened, how it was verified, what is new>
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MSG_LEN = 4096
SEND_ATTEMPTS = 2
TIMEOUT = 15

STATUS_ICONS = {
    "ok": "✅",
    "fail": "❌",
    "warn": "⚠️",
    "info": "ℹ️",
    "ask": "❓",
}

DEFAULT_TITLES = {
    "ok": "Tarea completada",
    "fail": "Tarea fallida",
    "warn": "Aviso",
    "info": "Info",
    "ask": "Necesito tu respuesta",
}

CONFIG_FILE = "~/.config/telegram-notify/notify.env"
# orden de búsqueda: variable de entorno explícita, fichero canónico y el
# antiguo de claude-telegram (por no romper máquinas ya configuradas)
CONFIG_CANDIDATES = (
    os.environ.get("TELEGRAM_NOTIFY_ENV"),
    CONFIG_FILE,
    "~/.config/claude-telegram/notify.env",
)


class NotifyError(Exception):
    """Anything that stops the message from going out; the text is user-facing."""


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("\"'")
    return values


def load_config(env: dict[str, str] | None = None) -> tuple[str, str]:
    """Return ``(token, chat_id)`` from the environment or the first config file that has them."""
    env = os.environ if env is None else env
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if token and chat_id:
        return token, chat_id

    candidates = (env.get("TELEGRAM_NOTIFY_ENV"),) + CONFIG_CANDIDATES[1:]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if not path.is_file():
            continue
        values = parse_env_file(path)
        token = token or values.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = chat_id or values.get("TELEGRAM_CHAT_ID", "")
        if token and chat_id:
            return token, chat_id

    missing = ", ".join(
        name
        for name, value in (("TELEGRAM_BOT_TOKEN", token), ("TELEGRAM_CHAT_ID", chat_id))
        if not value
    )
    searched = " | ".join(c for c in candidates if c)
    raise NotifyError(
        f"missing {missing}. Run `telegram-notify-setup`, export the variables, "
        f"or write them in one of: {searched}"
    )


def project_name() -> str:
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=3
        )
        if root.returncode == 0 and root.stdout.strip():
            return Path(root.stdout.strip()).name
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.cwd().name


def compose(
    body: str,
    status: str = "ok",
    title: str | None = None,
    project: str | None = None,
    host: str | None = None,
    context: bool = True,
) -> str:
    """Build the final text: headline, context line, blank line, body. Truncated to Telegram's limit."""
    icon = STATUS_ICONS.get(status, STATUS_ICONS["info"])
    lines = [f"{icon} {title or DEFAULT_TITLES.get(status, 'Notificación')}"]
    if context:
        lines.append(f"📁 {project or project_name()} · 🖥️ {host or socket.gethostname()}")
    body = body.strip()
    if body:
        lines.append("")
        lines.append(body)

    text = "\n".join(lines)
    if len(text) > MAX_MSG_LEN:
        marker = "\n… (truncado)"
        text = text[: MAX_MSG_LEN - len(marker)] + marker
    return text


def send(token: str, chat_id: str, text: str) -> dict:
    """POST *text* to Telegram's sendMessage as plain text, retrying once on network errors."""
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode()
    request = urllib.request.Request(
        API_URL.format(token=token),
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    last_error: Exception | None = None
    for attempt in range(SEND_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise NotifyError(f"Telegram API error {exc.code}: {detail}") from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < SEND_ATTEMPTS:
                time.sleep(2)
            continue
        if not result.get("ok"):
            raise NotifyError(f"Telegram rejected the message: {result}")
        return result
    raise NotifyError(f"network error talking to Telegram: {last_error}")


def notify(
    body: str,
    status: str = "ok",
    title: str | None = None,
    project: str | None = None,
    host: str | None = None,
    context: bool = True,
) -> str:
    """Compose and send; returns the text that went out. Raises NotifyError."""
    text = compose(body, status=status, title=title, project=project, host=host, context=context)
    token, chat_id = load_config()
    send(token, chat_id, text)
    return text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="telegram-notify",
        description="Send a Telegram message (used by agents to report task results).",
        epilog='example: telegram-notify -s ok -t "immich 1.140 desplegado" "Imagen desplegada. Health: HTTP 200."',
    )
    parser.add_argument("message", nargs="*", help="message body; omit it (or pass '-') to read from stdin")
    parser.add_argument(
        "-s", "--status", choices=sorted(STATUS_ICONS), default="ok",
        help="result of the task; picks the icon and default title (default: ok)",
    )
    parser.add_argument("-t", "--title", help="short headline, first line of the message")
    parser.add_argument("-p", "--project", help="project name (default: git repo or cwd name)")
    parser.add_argument("-H", "--host", help="host shown in the context line (default: this machine; use the deploy target if that is what matters)")
    parser.add_argument("--no-context", action="store_true", help="omit the project · host line")
    parser.add_argument("--dry-run", action="store_true", help="print the message instead of sending it")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.message or args.message == ["-"]:
        body = "" if sys.stdin.isatty() else sys.stdin.read()
    else:
        body = " ".join(args.message)

    if not body.strip() and not args.title:
        print("telegram-notify: nothing to send (give a message, stdin or --title)", file=sys.stderr)
        return 2

    text = compose(
        body, status=args.status, title=args.title, project=args.project, host=args.host,
        context=not args.no_context,
    )
    if args.dry_run:
        print(text)
        return 0

    try:
        token, chat_id = load_config()
        send(token, chat_id, text)
    except NotifyError as exc:
        print(f"telegram-notify: {exc}", file=sys.stderr)
        return 1
    print("telegram-notify: sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
