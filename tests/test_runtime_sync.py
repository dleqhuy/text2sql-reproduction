import subprocess

import pytest

from scripts.sync_runtime import synchronize


def test_sync_checks_drift_and_preserves_uncommitted_fork_edits(tmp_path):
    source = tmp_path / "runtime"
    relative = "reproduction/io.py"
    (source / "reproduction").mkdir(parents=True)
    (source / relative).write_text("# updated runtime\n")
    targets = [tmp_path / name for name in ("din", "mac")]
    for target in targets:
        (target / "reproduction").mkdir(parents=True)
        (target / relative).write_text("# previous runtime\n")
        for args in [
            ["init"],
            ["config", "user.name", "Fixture"],
            ["config", "user.email", "fixture@example.invalid"],
            ["add", "."],
            ["commit", "-m", "runtime baseline"],
        ]:
            subprocess.run(["git", "-C", str(target), *args], check=True, capture_output=True)
    assert len(synchronize(source, targets)) == 2
    assert (targets[0] / relative).read_text() == "# previous runtime\n"
    (targets[1] / relative).write_text("# local fix\n")
    with pytest.raises(ValueError, match="local runtime edits"):
        synchronize(source, targets, write=True)
    assert (targets[0] / relative).read_text() == "# previous runtime\n"
    assert (targets[1] / relative).read_text() == "# local fix\n"
    (targets[1] / relative).write_text("# previous runtime\n")
    assert len(synchronize(source, targets, write=True)) == 2
    assert synchronize(source, targets) == []
    assert synchronize(source, targets, write=True) == []
