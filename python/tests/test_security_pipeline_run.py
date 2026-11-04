"""run_pipeline 发布语义：校验失败不发布、不删历史，成功才清理旧快照。"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "naming-pipeline"))
from pipeline import run as run_mod  # noqa: E402

SEEDS = [{"name": "字节跳动"}, {"name": "阿里巴巴集团"}]


def _seed_file(tmp_path):
    path = tmp_path / "seeds.json"
    path.write_text(json.dumps(SEEDS, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _history(tmp_path, count):
    out = tmp_path / "out"
    hist = out / "history"
    hist.mkdir(parents=True, exist_ok=True)
    for i in range(1, count + 1):
        (hist / f"2026.01.01-{i:03d}.json").write_text("{}", encoding="utf-8")
    return out, hist


def test_validation_failure_keeps_previous_output_and_history(tmp_path, monkeypatch):
    out, hist = _history(tmp_path, 35)
    previous = out / "naming_patterns.v1.json"
    previous.write_text('{"previous": true}', encoding="utf-8")
    before = sorted(p.name for p in hist.iterdir())

    monkeypatch.setattr(run_mod, "validate_output",
                        lambda path: {"ok": False, "errors": ["boom"]})
    with pytest.raises(RuntimeError, match="schema 校验未通过"):
        run_mod.run_pipeline(data_dir=str(tmp_path / "data"), output_dir=str(out),
                             seeds_path=_seed_file(tmp_path), offline=True)

    assert json.loads(previous.read_text(encoding="utf-8")) == {"previous": True}
    # 失败运行不得顺手删掉旧快照（旧实现的 _prune_history 在校验前执行）
    assert sorted(p.name for p in hist.iterdir()) == before
    assert not list(out.glob("*.tmp"))
    # 状态不推进
    assert not (tmp_path / "data" / "state.json").exists()


def test_successful_run_prunes_history_after_publish(tmp_path):
    out, hist = _history(tmp_path, 35)
    record = run_mod.run_pipeline(data_dir=str(tmp_path / "data"), output_dir=str(out),
                                  seeds_path=_seed_file(tmp_path), offline=True)
    assert record["validation"]["ok"] is True
    assert len(list(hist.glob("*.json"))) == run_mod.HISTORY_KEEP
    assert (hist / f"{record['version']}.json").is_file()   # 本次快照保留
    assert not list(out.glob("*.tmp"))


def test_corpus_rebuild_validated_before_replace(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    corpus = data / "corpus.jsonl"
    corpus.write_text(json.dumps({"record_id": "1", "source": "curated_seed",
                                  "kind": "famous_brand", "name_raw": "阿里巴巴集团",
                                  "name_clean": "旧值"}, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    before = corpus.read_text(encoding="utf-8")

    real_dump = json.dumps

    def broken_dump(obj, *args, **kwargs):
        if isinstance(obj, dict) and obj.get("record_id") == "1":
            return "{not json"
        return real_dump(obj, *args, **kwargs)

    monkeypatch.setattr(run_mod.json, "dumps", broken_dump)
    with pytest.raises(ValueError):
        run_mod.run_pipeline(data_dir=str(data), output_dir=str(tmp_path / "out"),
                             rebuild_stats=True)
    assert corpus.read_text(encoding="utf-8") == before      # 语料未被半截覆写
