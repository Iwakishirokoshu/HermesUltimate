from pathlib import Path

from agent.prompt_builder import _collect_vault_load_files
from hermes_cli.soul_router import SoulRouter


def test_soul_router_switches_default_to_red(tmp_path: Path):
    router = SoulRouter(db_path=tmp_path / "soul_state.db")
    chat_id = "smoke-chat"

    default = router.get_active_soul(chat_id)
    assert default.name == "default"
    assert default.backend == "hermes"

    red = router.set_active_soul(chat_id, "red")
    assert red.name == "red"
    assert red.backend == "decepticon"

    active = router.get_active_soul(chat_id)
    assert active.name == "red"


def test_red_soul_vault_load_resolves_expected_paths(tmp_path: Path):
    router = SoulRouter(db_path=tmp_path / "soul_state.db")
    red = router.set_active_soul("vault-smoke", "red")

    vault_root = tmp_path / "HermesVault"
    (vault_root / "Engagements" / "demo").mkdir(parents=True)
    (vault_root / "Wiki" / "Findings").mkdir(parents=True)
    (vault_root / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (vault_root / "Engagements" / "demo" / "scope.md").write_text(
        "# Scope\n",
        encoding="utf-8",
    )
    (vault_root / "Wiki" / "Findings" / "host.md").write_text(
        "# Finding\n",
        encoding="utf-8",
    )

    files = _collect_vault_load_files(
        red.vault_load,
        current_slug="demo",
        vault_root=vault_root,
    )
    paths = [path.relative_to(vault_root).as_posix() for path in files]

    assert paths == [
        "INDEX.md",
        "Engagements/demo/scope.md",
        "Wiki/Findings/host.md",
    ]
