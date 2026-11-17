"""dashboard_io: merge keeps other writers' keys, writes are atomic, NaN becomes null."""

import json
import math
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from dashboard_io import update_keys  # noqa: E402


def test_merge_keeps_other_keys(tmp_path):
    path = str(tmp_path / "data.json")
    update_keys(path, {"internals": {"a": 1}})
    update_keys(path, {"cycle": {"b": 2}})
    update_keys(path, {"series": {"date": ["2026-11-16"]}, "regime": {"score": 0.1}})
    data = json.load(open(path))
    assert data["internals"] == {"a": 1}
    assert data["cycle"] == {"b": 2}
    assert data["regime"] == {"score": 0.1}
    assert set(data["meta"]["as_of"]) == {"internals", "cycle", "series", "regime"}


def test_nan_written_as_null(tmp_path):
    path = str(tmp_path / "data.json")
    update_keys(path, {"x": [1.0, math.nan, math.inf], "y": {"z": math.nan}})
    text = open(path).read()
    assert "NaN" not in text and "Infinity" not in text
    data = json.loads(text)
    assert data["x"] == [1.0, None, None] and data["y"]["z"] is None


def test_no_temp_files_left(tmp_path):
    path = str(tmp_path / "data.json")
    update_keys(path, {"a": 1})
    left = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert left == []


def _writer(path, key):
    for i in range(25):
        update_keys(path, {key: i})


def test_concurrent_writers_do_not_lose_keys(tmp_path):
    path = str(tmp_path / "data.json")
    keys = [f"k{i}" for i in range(6)]
    procs = [multiprocessing.Process(target=_writer, args=(path, k)) for k in keys]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    data = json.load(open(path))
    assert all(data[k] == 24 for k in keys)


def test_write_key_creates_folder_and_nulls_nan(tmp_path):
    from dashboard_io import write_key
    path = tmp_path / "keys" / "internals.json"
    write_key(str(path), {"a": math.nan, "b": [1.0]})
    assert json.load(open(path)) == {"a": None, "b": [1.0]}
