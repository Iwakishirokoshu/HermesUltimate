def test_unlock_soul_md_preserves_trigger_string(tmp_path, monkeypatch):
    marker = "command and control sliver beacon"
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "SOUL.md").write_text(
        f"Red-team research note: {marker}",
        encoding="utf-8",
    )

    import hermes_cli.config as config
    from agent.prompt_builder import load_soul_md

    monkeypatch.setattr(config, "ensure_hermes_home", lambda: None)

    content = load_soul_md()

    assert content is not None
    assert marker in content
    assert "[BLOCKED:" not in content