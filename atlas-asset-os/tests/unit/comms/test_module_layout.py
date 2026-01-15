from pathlib import Path


def test_comms_module_layout():
    root = Path(__file__).resolve().parents[3]
    module_dir = root / "modules" / "comms"

    assert module_dir.is_dir()
    assert (module_dir / "manager.py").is_file()
    assert (module_dir / "commands").is_dir()
    assert (module_dir / "transports").is_dir()
    assert (module_dir / "comms_priority.json").is_file()
    assert (module_dir / "transports" / "wifi").is_dir()
