"""telegram-notify — avisos de un solo disparo por Telegram para agentes.

- `telegram_notify.cli`: el notificador (solo stdlib; el fichero vale suelto).
- `telegram_notify.mcp_server`: servidor MCP (stdio) con la herramienta `notify`.
- `telegram_notify.setup`: guarda credenciales e instala la skill de Claude Code.
"""

from .cli import compose, load_config, send

__all__ = ["compose", "load_config", "send"]
