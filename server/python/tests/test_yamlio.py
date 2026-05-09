from pathlib import Path

from ling_server import yamlio


def test_load_dump_roundtrip(tmp_path: Path):
    src = tmp_path / "tasks.yaml"
    src.write_text(
        "- id: a\n"
        "  title: 任务A\n"
        "  status: todo\n"
        "  deadline: 2026-05-11T10:00:00+08:00\n"
        "- id: b\n"
        "  title: 任务B\n"
        "  status: done\n",
        encoding="utf-8",
    )

    items = yamlio.load_tasks(src)
    assert [i["id"] for i in items] == ["a", "b"]
    assert items[0]["title"] == "任务A"

    out = tmp_path / "out.yaml"
    yamlio.dump_tasks(out, items)
    text = out.read_text(encoding="utf-8")
    assert "id: a" in text and "id: b" in text
    assert "任务A" in text


def test_update_task_modifies_only_target(tmp_path: Path):
    src = tmp_path / "tasks.yaml"
    src.write_text(
        "- id: a\n  title: A\n  status: todo\n"
        "- id: b\n  title: B\n  status: todo\n",
        encoding="utf-8",
    )
    found = yamlio.update_task(src, "a", {"status": "done"})
    assert found is not None and found["status"] == "done"

    items = yamlio.load_tasks(src)
    assert items[0]["status"] == "done"
    assert items[1]["status"] == "todo"


def test_update_task_unknown_returns_none(tmp_path: Path):
    src = tmp_path / "tasks.yaml"
    src.write_text("- id: a\n  title: A\n  status: todo\n", encoding="utf-8")
    assert yamlio.update_task(src, "nope", {"status": "done"}) is None


def test_append_capture_creates_and_appends(tmp_path: Path):
    p = tmp_path / "inbox" / "capture.md"
    yamlio.append_capture(p, "first 中文")
    assert p.read_text(encoding="utf-8").endswith("- first 中文\n")

    yamlio.append_capture(p, "second")
    text = p.read_text(encoding="utf-8")
    assert "- first 中文" in text and "- second" in text


def test_append_capture_ignores_blank(tmp_path: Path):
    p = tmp_path / "inbox" / "capture.md"
    yamlio.append_capture(p, "   ")
    assert not p.exists()
