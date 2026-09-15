"""telegram-notify-mcp — servidor MCP (stdio) con una sola herramienta: `notify`.

Para cualquier cliente MCP (Claude Code, Cursor, Codex, Gemini CLI…):

    uvx --from "telegram-notify[mcp] @ git+https://github.com/zurdi15/telegram-notify" telegram-notify-mcp

Las credenciales salen del entorno (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) o de
~/.config/telegram-notify/notify.env; el servidor nunca las expone.
"""

from __future__ import annotations

import sys

from .cli import NotifyError, compose, load_config, send

INSTRUCTIONS = (
    "Avisa al usuario por Telegram con `notify` cuando una tarea larga termina, un "
    "build/deploy/test falla o necesitas su decisión y puede no estar delante de la "
    "terminal. UN mensaje por tarea, al acabar o bloquearte; sin pings de progreso. "
    "Mensaje en español, texto plano (sin Markdown), autocontenido y corto: titular "
    "`proyecto versión verbo`, qué se hizo con sus identificadores (imagen, tag, "
    "commit), cómo se verificó y, en releases, `Novedades X.Y.Z:` con una línea por "
    "cambio contada para quien usa la app. Nunca incluyas secretos. Las credenciales "
    "ya están configuradas: no las pidas."
)


def _server():
    try:
        try:  # mcp 2.x renombró FastMCP → MCPServer; 1.x sigue con FastMCP
            from mcp.server.mcpserver import MCPServer as Server
        except ImportError:
            from mcp.server.fastmcp import FastMCP as Server
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "telegram-notify-mcp: falta el paquete `mcp`. Instala el extra: "
            'uv tool install "telegram-notify[mcp] @ git+https://github.com/zurdi15/telegram-notify"'
        ) from exc

    mcp = Server("telegram-notify", instructions=INSTRUCTIONS)

    @mcp.tool()
    def notify(
        title: str,
        body: str,
        status: str = "ok",
        project: str | None = None,
        host: str | None = None,
        dry_run: bool = False,
    ) -> str:
        """Envía un aviso por Telegram al usuario (una tarea terminada o bloqueada).

        title: titular corto `proyecto versión verbo` (p. ej. "turtletrips 1.7.0 desplegado"), sin icono: lo pone `status`.
        body: qué se hizo (con imagen/tag/commit), cómo se verificó y, en releases, "Novedades X.Y.Z:" con una línea "- " por cambio. Texto plano en español, sin Markdown ni secretos.
        status: ok ✅ | fail ❌ | warn ⚠️ | info ℹ️ | ask ❓.
        project: nombre del proyecto para la línea de contexto (por defecto, el repo git del cwd).
        host: host de la línea de contexto (por defecto esta máquina; pasa el destino del despliegue si es lo relevante).
        dry_run: devuelve el mensaje compuesto sin enviarlo.
        """
        if status not in ("ok", "fail", "warn", "info", "ask"):
            return f"error: status inválido {status!r} (ok|fail|warn|info|ask)"
        text = compose(body, status=status, title=title, project=project, host=host)
        if dry_run:
            return text
        try:
            token, chat_id = load_config()
            send(token, chat_id, text)
        except NotifyError as exc:
            return f"error: {exc}"
        return "sent:\n" + text

    return mcp


def main() -> None:
    _server().run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
