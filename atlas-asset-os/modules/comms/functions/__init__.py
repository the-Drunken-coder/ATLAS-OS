from .echo import echo as test_echo
from .health_check import health_check
from .list_entities import list_entities
from .list_tasks import list_tasks
from .get_entity import get_entity
from .get_entity_by_alias import get_entity_by_alias
from .create_entity import create_entity
from .update_entity import update_entity
from .delete_entity import delete_entity
from .checkin_entity import checkin_entity
from .update_telemetry import update_telemetry
from .get_task import get_task
from .get_tasks_by_entity import get_tasks_by_entity
from .create_task import create_task
from .update_task import update_task
from .delete_task import delete_task
from .transition_task_status import transition_task_status
from .start_task import start_task
from .complete_task import complete_task
from .fail_task import fail_task
from .list_objects import list_objects
from .get_object import get_object
from .get_objects_by_entity import get_objects_by_entity
from .get_objects_by_task import get_objects_by_task
from .update_object import update_object
from .delete_object import delete_object
from .add_object_reference import add_object_reference
from .remove_object_reference import remove_object_reference
from .find_orphaned_objects import find_orphaned_objects
from .get_object_references import get_object_references
from .validate_object_references import validate_object_references
from .cleanup_object_references import cleanup_object_references
from .create_object import create_object
from .get_changed_since import get_changed_since
from .get_full_dataset import get_full_dataset

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
