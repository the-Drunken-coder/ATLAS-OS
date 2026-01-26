import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    """Walk up parents to locate the repo root (directory containing .git)."""
    for ancestor in [start] + list(start.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return start


# Ensure local Meshtastic bridge source is importable for command wrappers.
_ROOT = _find_repo_root(Path(__file__).resolve().parent)
_BRIDGE_SRC = (
    _ROOT
    / "Atlas_Client_SDKs"
    / "connection_packages"
    / "atlas_meshtastic_bridge"
    / "src"
)
if str(_BRIDGE_SRC) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_SRC))

from .echo import echo as test_echo  # noqa: E402
from .health_check import health_check  # noqa: E402
from .list_entities import list_entities  # noqa: E402
from .list_tasks import list_tasks  # noqa: E402
from .get_entity import get_entity  # noqa: E402
from .get_entity_by_alias import get_entity_by_alias  # noqa: E402
from .create_entity import create_entity  # noqa: E402
from .update_entity import update_entity  # noqa: E402
from .delete_entity import delete_entity  # noqa: E402
from .checkin_entity import checkin_entity  # noqa: E402
from .update_telemetry import update_telemetry  # noqa: E402
from .get_task import get_task  # noqa: E402
from .get_tasks_by_entity import get_tasks_by_entity  # noqa: E402
from .create_task import create_task  # noqa: E402
from .update_task import update_task  # noqa: E402
from .delete_task import delete_task  # noqa: E402
from .transition_task_status import transition_task_status  # noqa: E402
from .start_task import start_task  # noqa: E402
from .complete_task import complete_task  # noqa: E402
from .fail_task import fail_task  # noqa: E402
from .list_objects import list_objects  # noqa: E402
from .get_object import get_object  # noqa: E402
from .get_objects_by_entity import get_objects_by_entity  # noqa: E402
from .get_objects_by_task import get_objects_by_task  # noqa: E402
from .update_object import update_object  # noqa: E402
from .delete_object import delete_object  # noqa: E402
from .add_object_reference import add_object_reference  # noqa: E402
from .remove_object_reference import remove_object_reference  # noqa: E402
from .find_orphaned_objects import find_orphaned_objects  # noqa: E402
from .get_object_references import get_object_references  # noqa: E402
from .validate_object_references import validate_object_references  # noqa: E402
from .cleanup_object_references import cleanup_object_references  # noqa: E402
from .create_object import create_object  # noqa: E402
from .get_changed_since import get_changed_since  # noqa: E402
from .get_full_dataset import get_full_dataset  # noqa: E402

FUNCTION_REGISTRY = {
    "test_echo": test_echo,
    "health_check": health_check,
    "list_entities": list_entities,
    "list_tasks": list_tasks,
    "get_entity": get_entity,
    "get_entity_by_alias": get_entity_by_alias,
    "create_entity": create_entity,
    "update_entity": update_entity,
    "delete_entity": delete_entity,
    "checkin_entity": checkin_entity,
    "update_telemetry": update_telemetry,
    "get_task": get_task,
    "get_tasks_by_entity": get_tasks_by_entity,
    "create_task": create_task,
    "update_task": update_task,
    "delete_task": delete_task,
    "transition_task_status": transition_task_status,
    "start_task": start_task,
    "complete_task": complete_task,
    "fail_task": fail_task,
    "list_objects": list_objects,
    "get_object": get_object,
    "get_objects_by_entity": get_objects_by_entity,
    "get_objects_by_task": get_objects_by_task,
    "update_object": update_object,
    "delete_object": delete_object,
    "add_object_reference": add_object_reference,
    "remove_object_reference": remove_object_reference,
    "find_orphaned_objects": find_orphaned_objects,
    "get_object_references": get_object_references,
    "validate_object_references": validate_object_references,
    "cleanup_object_references": cleanup_object_references,
    "create_object": create_object,
    "get_changed_since": get_changed_since,
    "get_full_dataset": get_full_dataset,
}

__all__ = list(FUNCTION_REGISTRY.keys())
