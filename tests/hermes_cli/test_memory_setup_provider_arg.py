"""Tests for `hermes memory setup [provider]` routing.

HermesUltimate keeps memory vault-only. Provider arguments remain accepted for
CLI compatibility, but they must not activate, install, or import external
memory provider plugins.
"""

from types import SimpleNamespace
from unittest.mock import patch

from hermes_cli import memory_setup


class TestMemorySetupProviderRouting:
    def test_setup_with_provider_arg_skips_picker(self):
        """`memory setup NAME` routes straight to the compatibility handler."""
        args = SimpleNamespace(memory_command="setup", provider="honcho")
        with patch.object(memory_setup, "cmd_setup_provider") as direct, \
             patch.object(memory_setup, "cmd_setup") as picker:
            memory_setup.memory_command(args)
        direct.assert_called_once_with("honcho")
        picker.assert_not_called()

    def test_setup_without_provider_runs_setup(self):
        """`memory setup` confirms vault-only mode."""
        args = SimpleNamespace(memory_command="setup", provider=None)
        with patch.object(memory_setup, "cmd_setup_provider") as direct, \
             patch.object(memory_setup, "cmd_setup") as setup:
            memory_setup.memory_command(args)
        setup.assert_called_once_with(args)
        direct.assert_not_called()

    def test_setup_with_missing_provider_attr_runs_setup(self):
        """A SimpleNamespace lacking `provider` must not crash."""
        args = SimpleNamespace(memory_command="setup")
        with patch.object(memory_setup, "cmd_setup_provider") as direct, \
             patch.object(memory_setup, "cmd_setup") as setup:
            memory_setup.memory_command(args)
        setup.assert_called_once_with(args)
        direct.assert_not_called()

    def test_provider_arg_reports_disabled(self, capsys):
        """Provider args report disabled external memory and keep vault-only mode."""
        memory_setup.cmd_setup_provider("notaprovider")
        out = capsys.readouterr().out
        assert "disabled in HermesUltimate" in out
        assert "vault-only" in out


class TestExternalProviderHardening:
    """External provider helpers are inert compatibility shims."""

    def test_install_dependencies_is_noop(self):
        with patch("subprocess.run") as run:
            memory_setup._install_dependencies("x")
        run.assert_not_called()

    def test_available_providers_is_empty(self):
        assert memory_setup._get_available_providers() == []
