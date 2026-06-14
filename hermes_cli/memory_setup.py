"""hermes memory setup|status - HermesUltimate vault-only memory commands."""

from __future__ import annotations


def _ensure_vault_only_config() -> None:
    from hermes_cli.config import load_config, save_config

    config = load_config()
    if not isinstance(config.get("memory"), dict):
        config["memory"] = {}
    config["memory"]["provider"] = ""
    save_config(config)


def _install_dependencies(provider_name: str) -> None:
    """External memory provider dependency installation is disabled."""
    return None


def _get_available_providers() -> list:
    """Return no external memory providers for HermesUltimate."""
    return []


def cmd_setup_provider(provider_name: str) -> None:
    """Report that external memory providers are disabled."""
    _ensure_vault_only_config()
    print()
    print(f"  External memory provider '{provider_name}' is disabled in HermesUltimate.")
    print("  Memory stays vault-only: MEMORY.md, USER.md, and HermesVault.")
    print()


def cmd_setup(args) -> None:
    """Confirm vault-only memory mode."""
    _ensure_vault_only_config()
    print()
    print("  Memory provider: vault-only")
    print("  Built-in MEMORY.md / USER.md and HermesVault remain active.")
    print("  External memory provider plugins are disabled in HermesUltimate.")
    print()


def cmd_status(args) -> None:
    """Show current vault-only memory status."""
    from hermes_cli.config import load_config

    config = load_config()
    mem_config = config.get("memory", {})
    provider_name = ""
    if isinstance(mem_config, dict):
        provider_name = str(mem_config.get("provider") or "")

    print()
    print("Memory status")
    print("-" * 40)
    print("  Built-in:  active (MEMORY.md / USER.md)")
    print("  Vault:     active (HermesVault)")
    if provider_name:
        print(f"  Provider:  {provider_name} (configured but ignored)")
        print("  Action:    run 'hermes memory setup' to save vault-only mode")
    else:
        print("  Provider:  none (vault-only)")
    print()


def memory_command(args) -> None:
    """Route memory subcommands."""
    sub = getattr(args, "memory_command", None)
    if sub == "setup":
        provider = getattr(args, "provider", None)
        if provider:
            cmd_setup_provider(provider)
        else:
            cmd_setup(args)
    elif sub == "off":
        cmd_setup(args)
    elif sub == "status" or not sub:
        cmd_status(args)
    else:
        cmd_status(args)
