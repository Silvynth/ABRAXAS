"""
❖ Tests automatizados para la capa Foundation y Modelos de Abraxas 2.0
"""

import unittest
from pathlib import Path
from core.paths import get_repo_root, get_active_config_path
from core.process import run_command, CommandResult
from core.semver import parse_semver, bump_semver, detect_project_semver
from core.config import load_config, save_config, AppConfig
from lumen.models.project import Project
from lumen.models.git import GitBranch, GitCommit

class TestFoundation(unittest.TestCase):
    def test_paths_resolution(self):
        root = get_repo_root()
        self.assertTrue(root.exists())
        self.assertTrue((root / "core").is_dir())
        self.assertTrue((root / "lumen").is_dir())
        self.assertTrue((root / "umbra").is_dir())
        
        cfg_path = get_active_config_path()
        self.assertTrue(cfg_path.name.endswith(".toml"))

    def test_run_command_success(self):
        res = run_command(["echo", "abraxas_test"])
        self.assertTrue(res.success)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.output, "abraxas_test")
        self.assertGreater(res.duration_ms, 0)

    def test_run_command_failure(self):
        res = run_command(["false"])
        self.assertFalse(res.success)
        self.assertEqual(res.returncode, 1)

    def test_run_command_not_found(self):
        res = run_command(["comando_inexistente_12345"])
        self.assertFalse(res.success)
        self.assertEqual(res.returncode, 127)

    def test_semver_operations(self):
        self.assertEqual(parse_semver("v1.2.3"), (1, 2, 3, ""))
        self.assertEqual(bump_semver("v1.2.3", "patch"), "v1.2.4")
        self.assertEqual(bump_semver("v1.2.3", "minor"), "v1.3.0")
        self.assertEqual(bump_semver("v1.2.3", "major"), "v2.0.0")
        self.assertEqual(bump_semver("v1.2.3", "ALPHA"), "v2.0.0")
        self.assertEqual(bump_semver("v1.2.3", "BETA"), "v1.3.0")
        self.assertEqual(bump_semver("v1.2.3", "GAMMA"), "v1.2.4")

    def test_config_engine(self):
        cfg = load_config()
        self.assertIsNotNone(cfg)
        self.assertIsInstance(cfg.paths.projects_dir, Path)
        self.assertIn(cfg.abraxas.theme, ["system_sync", "dark_cyberpunk", "noctalia"])
        
        # Test guardar y leer en temporal
        temp_cfg_path = Path("/tmp/abraxas_test_config.toml")
        try:
            cfg.git.user_name = "test_user"
            saved = save_config(cfg, temp_cfg_path)
            self.assertTrue(saved)
            self.assertTrue(temp_cfg_path.exists())
            
            reloaded = load_config(temp_cfg_path)
            self.assertEqual(reloaded.git.user_name, "test_user")
        finally:
            if temp_cfg_path.exists():
                temp_cfg_path.unlink()

    def test_project_model(self):
        p = Project(path=get_repo_root(), semver="2.0.0")
        self.assertEqual(p.name, "Abraxas")
        self.assertTrue(p.exists)

    def test_git_models(self):
        b = GitBranch(name="main", is_current=True)
        self.assertEqual(b.display_name, "● main")
        
        c = GitCommit(
            hash="1234567890abcdef",
            short_hash="1234567",
            author="Dev",
            date="2026-09-24",
            message="Feature: Nueva arquitectura\nDetalle extenso"
        )
        self.assertEqual(c.title, "Feature: Nueva arquitectura")

    def test_cyber_terminal(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from ui.terminal.cyber_terminal import CyberTerminal
        term = CyberTerminal(prompt="test-term@abraxas:~$")
        self.assertEqual(term.current_state, 1)
        term.set_terminal_state(0)
        self.assertEqual(term.current_state, 0)
        self.assertEqual(term.height(), 38)
        term.set_terminal_state(1)
        self.assertEqual(term.current_state, 1)
        term.append_log("Log line test")
        term.log_info("GIT", "Cloning repo")
        term.log_success("GIT", "Done")
        self.assertIn("Log line test", term.text_display.toPlainText())
        self.assertIn("Done", term.text_display.toPlainText())

if __name__ == "__main__":
    unittest.main()
