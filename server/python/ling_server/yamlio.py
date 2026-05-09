"""tasks.yaml 写回工具。

要求：
- 保留与 memory_repo_template/tasks.yaml 一致的列表-of-mappings 风格
- 不破坏字符串里的中文与时区信息
- 修改时不改动 id 顺序
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml


class _IndentedDumper(yaml.SafeDumper):
    """让列表项缩进更清晰，输出贴近模板风格。"""


def _str_presenter(dumper: yaml.Dumper, data: str):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_IndentedDumper.add_representer(str, _str_presenter)


def load_tasks(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError("tasks.yaml top-level must be a list")
    return data


def dump_tasks(path: Path, items: List[Dict[str, Any]]) -> None:
    text = yaml.dump(
        items,
        Dumper=_IndentedDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def update_task(path: Path, task_id: str, patch: Dict[str, Any]) -> Dict[str, Any] | None:
    items = load_tasks(path)
    found = None
    for item in items:
        if str(item.get("id")) == str(task_id):
            for k, v in patch.items():
                if v is None:
                    item.pop(k, None)
                else:
                    item[k] = v
            found = item
            break
    if found is not None:
        dump_tasks(path, items)
    return found


def append_capture(capture_path: Path, line: str) -> None:
    capture_path.parent.mkdir(parents=True, exist_ok=True)
    text = line.strip()
    if not text:
        return
    if capture_path.exists():
        existing = capture_path.read_text(encoding="utf-8")
        if not existing.endswith("\n"):
            existing += "\n"
    else:
        existing = "## capture\n\n"
    new_line = f"- {text}\n"
    capture_path.write_text(existing + new_line, encoding="utf-8")
