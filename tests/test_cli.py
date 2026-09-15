"""Stdlib-only tests: python -m unittest discover -s tests (pytest also works)."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from telegram_notify import cli


class ComposeTests(unittest.TestCase):
    def test_shape_title_context_blank_body(self):
        text = cli.compose("Imagen desplegada.\nHealth: HTTP 200.", title="tt 1.7.0 desplegado", project="turtletrips", host="ginnugagap")
        self.assertEqual(
            text,
            "✅ tt 1.7.0 desplegado\n📁 turtletrips · 🖥️ ginnugagap\n\nImagen desplegada.\nHealth: HTTP 200.",
        )

    def test_status_icon_and_default_title(self):
        self.assertTrue(cli.compose("x", status="fail", context=False).startswith("❌ Tarea fallida"))
        self.assertTrue(cli.compose("x", status="ask", context=False).startswith("❓ Necesito tu respuesta"))
        # estado desconocido: icono de info, no un KeyError
        self.assertTrue(cli.compose("x", status="nope", context=False).startswith("ℹ️"))

    def test_no_body_no_blank_line(self):
        self.assertEqual(cli.compose("   ", title="Solo titular", context=False), "✅ Solo titular")

    def test_truncates_to_telegram_limit(self):
        text = cli.compose("x" * 5000, title="t", context=False)
        self.assertLessEqual(len(text), cli.MAX_MSG_LEN)
        self.assertTrue(text.endswith("… (truncado)"))

    def test_context_defaults_to_git_project_and_hostname(self):
        with mock.patch.object(cli, "project_name", return_value="repo"), mock.patch.object(cli.socket, "gethostname", return_value="box"):
            self.assertIn("📁 repo · 🖥️ box", cli.compose("b"))


class ConfigTests(unittest.TestCase):
    def test_env_wins(self):
        env = {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}
        self.assertEqual(cli.load_config(env), ("t", "c"))

    def test_env_file_pointed_by_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notify.env"
            path.write_text('# comentario\nTELEGRAM_BOT_TOKEN="123:abc"\nTELEGRAM_CHAT_ID = 42\n')
            self.assertEqual(cli.load_config({"TELEGRAM_NOTIFY_ENV": str(path)}), ("123:abc", "42"))

    def test_missing_is_a_notify_error_naming_the_variables(self):
        # sin ficheros de configuración a la vista, aunque esta máquina los tenga
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(cli, "CONFIG_CANDIDATES", (None, f"{tmp}/none.env")):
            with self.assertRaises(cli.NotifyError) as ctx:
                cli.load_config({"TELEGRAM_BOT_TOKEN": "only-token"})
            self.assertIn("TELEGRAM_CHAT_ID", str(ctx.exception))
            self.assertNotIn("only-token", str(ctx.exception))


class MainTests(unittest.TestCase):
    def run_main(self, argv, stdin=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            if stdin is not None:
                with mock.patch.object(cli.sys, "stdin", io.StringIO(stdin)):
                    code = cli.main(argv)
            else:
                code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_dry_run_prints_and_does_not_send(self):
        with mock.patch.object(cli, "send") as send:
            code, out, _ = self.run_main(["--dry-run", "-t", "tt 1.8.0 desplegado", "-p", "tt", "-H", "node", "cuerpo"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "✅ tt 1.8.0 desplegado\n📁 tt · 🖥️ node\n\ncuerpo\n")
        send.assert_not_called()

    def test_body_from_stdin(self):
        code, out, _ = self.run_main(["--dry-run", "--no-context", "-t", "t"], stdin="línea 1\nlínea 2\n")
        self.assertEqual(code, 0)
        self.assertEqual(out, "✅ t\n\nlínea 1\nlínea 2\n")

    def test_nothing_to_send(self):
        code, _, err = self.run_main(["--dry-run"], stdin="")
        self.assertEqual(code, 2)
        self.assertIn("nothing to send", err)

    def test_send_path_uses_config(self):
        with mock.patch.object(cli, "load_config", return_value=("tok", "chat")), mock.patch.object(cli, "send") as send:
            code, out, _ = self.run_main(["--no-context", "-t", "t", "b"])
        self.assertEqual(code, 0)
        self.assertIn("sent", out)
        send.assert_called_once_with("tok", "chat", "✅ t\n\nb")

    def test_missing_config_is_exit_1_with_reason(self):
        with mock.patch.object(cli, "load_config", side_effect=cli.NotifyError("missing X")):
            code, _, err = self.run_main(["--no-context", "-t", "t", "b"])
        self.assertEqual(code, 1)
        self.assertIn("missing X", err)


if __name__ == "__main__":
    unittest.main()
