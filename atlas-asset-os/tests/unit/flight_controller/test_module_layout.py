from pathlib import Path


def test_flight_controller_module_scaffold():
    root = Path(__file__).resolve().parents[3]
    module_dir = root / "modules" / "flight_controller"

    assert module_dir.is_dir()
    assert (module_dir / "PLAN.md").is_file()
