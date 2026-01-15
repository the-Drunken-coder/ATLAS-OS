from pathlib import Path


def test_operations_module_layout():
    root = Path(__file__).resolve().parents[3]
    module_dir = root / "modules" / "operations"

    assert module_dir.is_dir()
    assert (module_dir / "manager.py").is_file()
