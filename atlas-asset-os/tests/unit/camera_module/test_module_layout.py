from pathlib import Path


def test_camera_module_scaffold():
    root = Path(__file__).resolve().parents[3]
    module_dir = root / "modules" / "camera_module"

    assert module_dir.is_dir()
    assert (module_dir / "PLAN.md").is_file()
