"""telegram-notify-setup — deja el notificador listo en esta máquina.

    telegram-notify-setup --token 123:abc --chat-id 42      # guarda credenciales
    telegram-notify-setup --token 123:abc --find-chat       # lista los chats que han escrito al bot
    telegram-notify-setup --test                            # manda un mensaje de prueba

Escribe ~/.config/telegram-notify/notify.env (solo lectura para el usuario),
instala la skill de Claude Code en ~/.claude/skills/telegram-notify/ y enseña
cómo registrar el servidor MCP. Nunca imprime el token.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .cli import CONFIG_FILE, NotifyError, compose, load_config, parse_env_file, send

SOURCE = "git+https://github.com/zurdi15/telegram-notify"
SKILL_DIR = Path("~/.claude/skills/telegram-notify").expanduser()


def write_config(token: str, chat_id: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = parse_env_file(path) if path.is_file() else {}
    existing.update({"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_CHAT_ID": chat_id})
    body = "\n".join(f"{key}={value}" for key, value in existing.items()) + "\n"
    path.write_text(body, encoding="utf-8")
    os.chmod(path, 0o600)


def find_chats(token: str) -> list[tuple[str, str]]:
    """(chat_id, nombre) de las conversaciones recientes con el bot (getUpdates)."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise NotifyError(f"Telegram API error {exc.code}: ¿token correcto?") from exc
    chats: dict[str, str] = {}
    for update in data.get("result", []):
        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat")
        if chat:
            name = chat.get("title") or " ".join(
                part for part in (chat.get("first_name"), chat.get("last_name")) if part
            ) or chat.get("username") or chat.get("type", "")
            chats[str(chat["id"])] = name
    return list(chats.items())


def install_skill() -> Path:
    source = Path(__file__).with_name("SKILL.md")
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    target = SKILL_DIR / "SKILL.md"
    shutil.copyfile(source, target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="telegram-notify-setup", description=__doc__.split("\n\n")[0])
    parser.add_argument("--token", help="token del bot (de @BotFather)")
    parser.add_argument("--chat-id", help="chat destino (tu usuario o un grupo)")
    parser.add_argument("--find-chat", action="store_true", help="lista los chats que han escrito al bot y sale")
    parser.add_argument("--config", default=CONFIG_FILE, help=f"fichero de credenciales (por defecto {CONFIG_FILE})")
    parser.add_argument("--no-skill", action="store_true", help="no instalar la skill de Claude Code")
    parser.add_argument("--test", action="store_true", help="enviar un mensaje de prueba al terminar")
    args = parser.parse_args(argv)

    if args.find_chat:
        if not args.token:
            parser.error("--find-chat necesita --token")
        try:
            chats = find_chats(args.token)
        except NotifyError as exc:
            print(f"telegram-notify-setup: {exc}", file=sys.stderr)
            return 1
        if not chats:
            print("Ningún chat todavía: escribe cualquier cosa al bot en Telegram y vuelve a probar.")
            return 1
        for chat_id, name in chats:
            print(f"{chat_id}\t{name}")
        return 0

    config = Path(args.config).expanduser()
    if args.token or args.chat_id:
        if not (args.token and args.chat_id):
            parser.error("--token y --chat-id van juntos (o usa --find-chat para averiguar el chat)")
        write_config(args.token, args.chat_id, config)
        print(f"Credenciales guardadas en {config} (modo 600).")
    else:
        try:
            load_config()
        except NotifyError:
            print(
                "Sin credenciales: pasa --token y --chat-id (o exporta TELEGRAM_BOT_TOKEN y "
                "TELEGRAM_CHAT_ID). Para saber el chat: --token … --find-chat",
                file=sys.stderr,
            )
            return 1
        print("Credenciales ya presentes.")

    if not args.no_skill:
        target = install_skill()
        print(f"Skill de Claude Code instalada en {target}")

    print(
        "\nServidor MCP (opcional, para que el agente avise por sí mismo):\n"
        "  claude mcp add --scope user telegram-notify -- telegram-notify-mcp\n"
        "  (o en cualquier cliente MCP: command uvx, args --from "
        f'"telegram-notify[mcp] @ {SOURCE}" telegram-notify-mcp)'
    )

    if args.test:
        try:
            token, chat_id = load_config()
            send(token, chat_id, compose("Si lees esto, telegram-notify funciona en esta máquina.", title="Prueba de telegram-notify", project="telegram-notify"))
        except NotifyError as exc:
            print(f"telegram-notify-setup: {exc}", file=sys.stderr)
            return 1
        print("Mensaje de prueba enviado.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
