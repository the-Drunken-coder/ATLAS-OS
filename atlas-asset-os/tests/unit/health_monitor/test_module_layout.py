from pathlib import Path


def test_health_monitor_module_scaffold():
    root = Path(__file__).resolve().parents[3]
    module_dir = root / "modules" / "health_monitor"

    assert module_dir.is_dir()
    assert (module_dir / "PLAN.md").is_file()
