import hashlib
import zipfile

import pytest

from scripts import fetch_spider
from scripts.common.io import read_json


def test_quota_page_rejected_before_extract(tmp_path):
    archive = tmp_path / "quota.zip"
    archive.write_text("<html>Quota exceeded</html>")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        fetch_spider.import_archive(archive, tmp_path / "dataset", tmp_path / "source.json")
    assert not (tmp_path / "dataset").exists()


def test_pinned_archive_import_scope_and_provenance(tmp_path, monkeypatch):
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        for name in fetch_spider.REQUIRED:
            zipped.writestr("spider_data/" + name, "[]")
        zipped.writestr("spider_data/database/mini/mini.sqlite", b"fixture")
        zipped.writestr("spider_data/test_database/test/test.sqlite", b"excluded")
        zipped.writestr("__MACOSX/spider_data/._dev.json", b"excluded")
    monkeypatch.setattr(
        fetch_spider, "ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    output, provenance = tmp_path / "dataset", tmp_path / "source.json"
    result = fetch_spider.import_archive(archive, output, provenance)
    assert result["sqlite_files"] == 1
    assert (output / "database/mini/mini.sqlite").is_file()
    assert not (output / "test_database").exists()
    assert read_json(provenance)["archive_sha256"] == result["archive_sha256"]
    with pytest.raises(ValueError, match="already exists"):
        fetch_spider.import_archive(archive, output, provenance)


def test_missing_assets_never_publish_partial_dataset(tmp_path, monkeypatch):
    archive = tmp_path / "incomplete.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("spider_data/dev.json", "[]")
    monkeypatch.setattr(
        fetch_spider, "ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    with pytest.raises(ValueError, match="required Spider"):
        fetch_spider.import_archive(archive, tmp_path / "dataset", tmp_path / "source.json")
    assert not (tmp_path / "dataset").exists()
