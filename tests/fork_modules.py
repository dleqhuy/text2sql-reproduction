"""Test-only inspection of fork parsers and cache; production uses native CLIs."""

import importlib.util
import sys

import pytest

from scripts.common.io import ROOT


def load_fork_module(folder, filename="reproduction_adapter.py"):
    path = ROOT / "third_party" / folder / filename
    if not path.is_file():
        pytest.skip("Initialize fork submodules first", allow_module_level=True)
    name = "fork_test_" + folder.replace("-", "_") + "_" + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
