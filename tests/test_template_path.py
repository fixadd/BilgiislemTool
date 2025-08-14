import sys
import importlib
from pathlib import Path


def test_templates_resolve_from_any_cwd(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    monkeypatch.chdir(tmp_path)
    sys.modules.pop("utils", None)
    utils = importlib.import_module("utils")
    assert utils.templates.env.get_template("login.html") is not None
    sys.path.remove(str(project_root))
