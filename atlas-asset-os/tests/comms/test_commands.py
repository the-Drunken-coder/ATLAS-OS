"""Tests for comms command handlers.

All command handlers follow a similar pattern:
1. Check if client is None and raise RuntimeError if so
2. Call the corresponding client method with appropriate arguments
3. Return the result from the client method
"""

from unittest.mock import MagicMock
import pytest


class TestEchoCommand:
    """Tests for the echo command handler."""

    def test_echo_raises_when_client_none(self):
        """Test echo raises RuntimeError when client is None."""
        from modules.comms.commands.echo import echo

        with pytest.raises(RuntimeError, match="not initialized"):
            echo(None, "test")

    def test_echo_calls_client_test_echo(self):
        """Test echo calls client.test_echo with correct args."""
        from modules.comms.commands.echo import echo

        client = MagicMock()
        client.test_echo.return_value = {"echo": "test"}

        result = echo(client, "test", timeout=5.0, retries=3)

        client.test_echo.assert_called_once_with(message="test", timeout=5.0, max_retries=3)
        assert result == {"echo": "test"}

    def test_echo_default_message(self):
        """Test echo uses default message 'ping'."""
        from modules.comms.commands.echo import echo

        client = MagicMock()
        echo(client)

        client.test_echo.assert_called_once_with(message="ping", timeout=None, max_retries=None)


class TestHealthCheckCommand:
    """Tests for the health_check command handler."""

    def test_health_check_raises_when_client_none(self):
        """Test health_check raises RuntimeError when client is None."""
        from modules.comms.commands.health_check import health_check

        with pytest.raises(RuntimeError, match="not initialized"):
            health_check(None)

    def test_health_check_calls_client(self):
        """Test health_check calls client.health_check with correct args."""
        from modules.comms.commands.health_check import health_check

        client = MagicMock()
        client.health_check.return_value = {"status": "healthy"}

        result = health_check(client, timeout=10.0, retries=2)

        client.health_check.assert_called_once_with(timeout=10.0, max_retries=2)
        assert result == {"status": "healthy"}


class TestEntityCommands:
    """Tests for entity-related command handlers."""

    def test_list_entities_raises_when_client_none(self):
        """Test list_entities raises RuntimeError when client is None."""
        from modules.comms.commands.list_entities import list_entities

        with pytest.raises(RuntimeError, match="not initialized"):
            list_entities(None)

    def test_list_entities_calls_client(self):
        """Test list_entities calls client correctly."""
        from modules.comms.commands.list_entities import list_entities

        client = MagicMock()
        client.list_entities.return_value = [{"id": "entity-1"}]

        result = list_entities(client, timeout=5.0, retries=2)

        client.list_entities.assert_called_once_with(timeout=5.0, max_retries=2)
        assert result == [{"id": "entity-1"}]

    def test_get_entity_raises_when_client_none(self):
        """Test get_entity raises RuntimeError when client is None."""
        from modules.comms.commands.get_entity import get_entity

        with pytest.raises(RuntimeError, match="not initialized"):
            get_entity(None, "entity-1")

    def test_get_entity_calls_client(self):
        """Test get_entity calls client with correct args."""
        from modules.comms.commands.get_entity import get_entity

        client = MagicMock()
        client.get_entity.return_value = {"id": "entity-1", "alias": "Test"}

        result = get_entity(client, "entity-1", timeout=5.0, retries=2)

        client.get_entity.assert_called_once_with(entity_id="entity-1", timeout=5.0, max_retries=2)
        assert result["id"] == "entity-1"

    def test_get_entity_by_alias_raises_when_client_none(self):
        """Test get_entity_by_alias raises RuntimeError when client is None."""
        from modules.comms.commands.get_entity_by_alias import get_entity_by_alias

        with pytest.raises(RuntimeError, match="not initialized"):
            get_entity_by_alias(None, "TestAlias")

    def test_get_entity_by_alias_calls_client(self):
        """Test get_entity_by_alias calls client with correct args."""
        from modules.comms.commands.get_entity_by_alias import get_entity_by_alias

        client = MagicMock()
        client.get_entity_by_alias.return_value = {"id": "entity-1", "alias": "TestAlias"}

        result = get_entity_by_alias(client, "TestAlias", timeout=5.0, retries=2)

        client.get_entity_by_alias.assert_called_once_with(alias="TestAlias", timeout=5.0, max_retries=2)
        assert result["alias"] == "TestAlias"

    def test_create_entity_raises_when_client_none(self):
        """Test create_entity raises RuntimeError when client is None."""
        from modules.comms.commands.create_entity import create_entity

        with pytest.raises(RuntimeError, match="not initialized"):
            create_entity(None, "entity-1", "asset", "TestAlias", "drone")

    def test_create_entity_calls_client(self):
        """Test create_entity calls client with correct args."""
        from modules.comms.commands.create_entity import create_entity

        client = MagicMock()
        client.create_entity.return_value = {"id": "entity-1"}

        result = create_entity(
            client,
            "entity-1",
            "asset",
            "TestAlias",
            "drone",
            components={"telemetry": {}},
            timeout=5.0,
            retries=2,
        )

        client.create_entity.assert_called_once_with(
            entity_id="entity-1",
            entity_type="asset",
            alias="TestAlias",
            subtype="drone",
            components={"telemetry": {}},
            timeout=5.0,
            max_retries=2,
        )
        assert result["id"] == "entity-1"

    def test_update_entity_raises_when_client_none(self):
        """Test update_entity raises RuntimeError when client is None."""
        from modules.comms.commands.update_entity import update_entity

        with pytest.raises(RuntimeError, match="not initialized"):
            update_entity(None, "entity-1")

    def test_update_entity_calls_client(self):
        """Test update_entity calls client with correct args."""
        from modules.comms.commands.update_entity import update_entity

        client = MagicMock()
        client.update_entity.return_value = {"id": "entity-1", "subtype": "updated"}

        result = update_entity(
            client,
            "entity-1",
            subtype="updated",
            components={"status": "active"},
            timeout=5.0,
            retries=2,
        )

        client.update_entity.assert_called_once_with(
            entity_id="entity-1",
            subtype="updated",
            components={"status": "active"},
            timeout=5.0,
            max_retries=2,
        )
        assert result["subtype"] == "updated"

    def test_delete_entity_raises_when_client_none(self):
        """Test delete_entity raises RuntimeError when client is None."""
        from modules.comms.commands.delete_entity import delete_entity

        with pytest.raises(RuntimeError, match="not initialized"):
            delete_entity(None, "entity-1")

    def test_delete_entity_calls_client(self):
        """Test delete_entity calls client with correct args."""
        from modules.comms.commands.delete_entity import delete_entity

        client = MagicMock()
        client.delete_entity.return_value = {"deleted": True}

        result = delete_entity(client, "entity-1", timeout=5.0, retries=2)

        client.delete_entity.assert_called_once_with(
            entity_id="entity-1", timeout=5.0, max_retries=2
        )
        assert result["deleted"] is True

    def test_checkin_entity_raises_when_client_none(self):
        """Test checkin_entity raises RuntimeError when client is None."""
        from modules.comms.commands.checkin_entity import checkin_entity

        with pytest.raises(RuntimeError, match="not initialized"):
            checkin_entity(None, "entity-1")

    def test_checkin_entity_calls_client(self):
        """Test checkin_entity calls client with correct args."""
        from modules.comms.commands.checkin_entity import checkin_entity

        client = MagicMock()
        client.checkin_entity.return_value = {"id": "entity-1", "checked_in": True}

        result = checkin_entity(client, "entity-1", timeout=5.0, retries=2)

        client.checkin_entity.assert_called_once_with(
            entity_id="entity-1", timeout=5.0, max_retries=2
        )
        assert result["checked_in"] is True


class TestTelemetryCommands:
    """Tests for telemetry command handlers."""

    def test_update_telemetry_raises_when_client_none(self):
        """Test update_telemetry raises RuntimeError when client is None."""
        from modules.comms.commands.update_telemetry import update_telemetry

        with pytest.raises(RuntimeError, match="not initialized"):
            update_telemetry(None, entity_id="entity-1")

    def test_update_telemetry_calls_client(self):
        """Test update_telemetry calls client with correct args."""
        from modules.comms.commands.update_telemetry import update_telemetry

        client = MagicMock()
        client.update_telemetry.return_value = {"id": "entity-1", "updated": True}

        update_telemetry(
            client,
            entity_id="entity-1",
            latitude=40.7128,
            longitude=-74.0060,
            altitude_m=100.0,
            timeout=5.0,
            retries=2,
        )

        client.update_telemetry.assert_called_once()
        call_kwargs = client.update_telemetry.call_args[1]
        assert call_kwargs["entity_id"] == "entity-1"
        assert call_kwargs["latitude"] == 40.7128
        assert call_kwargs["longitude"] == -74.0060


class TestTaskCommands:
    """Tests for task-related command handlers."""

    def test_list_tasks_raises_when_client_none(self):
        """Test list_tasks raises RuntimeError when client is None."""
        from modules.comms.commands.list_tasks import list_tasks

        with pytest.raises(RuntimeError, match="not initialized"):
            list_tasks(None)

    def test_list_tasks_calls_client(self):
        """Test list_tasks calls client correctly."""
        from modules.comms.commands.list_tasks import list_tasks

        client = MagicMock()
        client.list_tasks.return_value = [{"id": "task-1"}]

        result = list_tasks(client, timeout=5.0, retries=2)

        client.list_tasks.assert_called_once_with(timeout=5.0, max_retries=2)
        assert result == [{"id": "task-1"}]

    def test_get_task_raises_when_client_none(self):
        """Test get_task raises RuntimeError when client is None."""
        from modules.comms.commands.get_task import get_task

        with pytest.raises(RuntimeError, match="not initialized"):
            get_task(None, "task-1")

    def test_get_task_calls_client(self):
        """Test get_task calls client with correct args."""
        from modules.comms.commands.get_task import get_task

        client = MagicMock()
        client.get_task.return_value = {"id": "task-1", "status": "pending"}

        result = get_task(client, "task-1", timeout=5.0, retries=2)

        client.get_task.assert_called_once_with(task_id="task-1", timeout=5.0, max_retries=2)
        assert result["id"] == "task-1"

    def test_get_tasks_by_entity_raises_when_client_none(self):
        """Test get_tasks_by_entity raises RuntimeError when client is None."""
        from modules.comms.commands.get_tasks_by_entity import get_tasks_by_entity

        with pytest.raises(RuntimeError, match="not initialized"):
            get_tasks_by_entity(None, "entity-1")

    def test_get_tasks_by_entity_calls_client(self):
        """Test get_tasks_by_entity calls client with correct args."""
        from modules.comms.commands.get_tasks_by_entity import get_tasks_by_entity

        client = MagicMock()
        client.get_tasks_by_entity.return_value = [{"id": "task-1"}]

        result = get_tasks_by_entity(client, "entity-1", timeout=5.0, retries=2)

        client.get_tasks_by_entity.assert_called_once_with(
            entity_id="entity-1", timeout=5.0, max_retries=2
        )
        assert result == [{"id": "task-1"}]

    def test_create_task_raises_when_client_none(self):
        """Test create_task raises RuntimeError when client is None."""
        from modules.comms.commands.create_task import create_task

        with pytest.raises(RuntimeError, match="not initialized"):
            create_task(None, "task-1")

    def test_create_task_calls_client(self):
        """Test create_task calls client with correct args."""
        from modules.comms.commands.create_task import create_task

        client = MagicMock()
        client.create_task.return_value = {"id": "task-1"}

        create_task(
            client,
            "task-1",
            status="pending",
            entity_id="entity-1",
            components={"waypoints": []},
            timeout=5.0,
            retries=2,
        )

        client.create_task.assert_called_once_with(
            task_id="task-1",
            status="pending",
            entity_id="entity-1",
            components={"waypoints": []},
            extra=None,
            timeout=5.0,
            max_retries=2,
        )

    def test_update_task_raises_when_client_none(self):
        """Test update_task raises RuntimeError when client is None."""
        from modules.comms.commands.update_task import update_task

        with pytest.raises(RuntimeError, match="not initialized"):
            update_task(None, "task-1")

    def test_update_task_calls_client(self):
        """Test update_task calls client with correct args."""
        from modules.comms.commands.update_task import update_task

        client = MagicMock()
        client.update_task.return_value = {"id": "task-1", "status": "running"}

        result = update_task(
            client,
            "task-1",
            status="running",
            components={"progress": 50},
            timeout=5.0,
            retries=2,
        )

        client.update_task.assert_called_once()
        assert result["status"] == "running"

    def test_delete_task_raises_when_client_none(self):
        """Test delete_task raises RuntimeError when client is None."""
        from modules.comms.commands.delete_task import delete_task

        with pytest.raises(RuntimeError, match="not initialized"):
            delete_task(None, "task-1")

    def test_delete_task_calls_client(self):
        """Test delete_task calls client with correct args."""
        from modules.comms.commands.delete_task import delete_task

        client = MagicMock()
        client.delete_task.return_value = {"deleted": True}

        delete_task(client, "task-1", timeout=5.0, retries=2)

        client.delete_task.assert_called_once_with(
            task_id="task-1", timeout=5.0, max_retries=2
        )

    def test_transition_task_status_raises_when_client_none(self):
        """Test transition_task_status raises RuntimeError when client is None."""
        from modules.comms.commands.transition_task_status import transition_task_status

        with pytest.raises(RuntimeError, match="not initialized"):
            transition_task_status(None, "task-1", "running")

    def test_transition_task_status_calls_client(self):
        """Test transition_task_status calls client with correct args."""
        from modules.comms.commands.transition_task_status import transition_task_status

        client = MagicMock()
        client.transition_task_status.return_value = {"id": "task-1", "status": "running"}

        transition_task_status(client, "task-1", "running", timeout=5.0, retries=2)

        client.transition_task_status.assert_called_once_with(
            task_id="task-1", status="running", timeout=5.0, max_retries=2
        )

    def test_acknowledge_task_raises_when_client_none(self):
        """Test acknowledge_task raises RuntimeError when client is None."""
        from modules.comms.commands.acknowledge_task import acknowledge_task

        with pytest.raises(RuntimeError, match="not initialized"):
            acknowledge_task(None, "task-1")

    def test_acknowledge_task_calls_client(self):
        """Test acknowledge_task calls client with correct args."""
        from modules.comms.commands.acknowledge_task import acknowledge_task

        client = MagicMock()
        client.acknowledge_task.return_value = {"id": "task-1", "status": "running"}

        acknowledge_task(client, "task-1", timeout=5.0, retries=2)

        client.acknowledge_task.assert_called_once_with(
            task_id="task-1", timeout=5.0, max_retries=2
        )

    def test_complete_task_raises_when_client_none(self):
        """Test complete_task raises RuntimeError when client is None."""
        from modules.comms.commands.complete_task import complete_task

        with pytest.raises(RuntimeError, match="not initialized"):
            complete_task(None, "task-1")

    def test_complete_task_calls_client(self):
        """Test complete_task calls client with correct args."""
        from modules.comms.commands.complete_task import complete_task

        client = MagicMock()
        client.complete_task.return_value = {"id": "task-1", "status": "completed"}

        complete_task(client, "task-1", timeout=5.0, retries=2)

        client.complete_task.assert_called_once_with(
            task_id="task-1", timeout=5.0, max_retries=2
        )

    def test_fail_task_raises_when_client_none(self):
        """Test fail_task raises RuntimeError when client is None."""
        from modules.comms.commands.fail_task import fail_task

        with pytest.raises(RuntimeError, match="not initialized"):
            fail_task(None, "task-1")

    def test_fail_task_calls_client(self):
        """Test fail_task calls client with correct args."""
        from modules.comms.commands.fail_task import fail_task

        client = MagicMock()
        client.fail_task.return_value = {"id": "task-1", "status": "failed"}

        fail_task(client, "task-1", error_message="Test failure", timeout=5.0, retries=2)

        client.fail_task.assert_called_once_with(
            task_id="task-1", error_message="Test failure", error_details=None, timeout=5.0, max_retries=2
        )


class TestObjectCommands:
    """Tests for object-related command handlers."""

    def test_list_objects_raises_when_client_none(self):
        """Test list_objects raises RuntimeError when client is None."""
        from modules.comms.commands.list_objects import list_objects

        with pytest.raises(RuntimeError, match="not initialized"):
            list_objects(None)

    def test_list_objects_calls_client(self):
        """Test list_objects calls client correctly."""
        from modules.comms.commands.list_objects import list_objects

        client = MagicMock()
        client.list_objects.return_value = [{"id": "object-1"}]

        result = list_objects(client, timeout=5.0, retries=2)

        client.list_objects.assert_called_once_with(timeout=5.0, max_retries=2)
        assert result == [{"id": "object-1"}]

    def test_get_object_raises_when_client_none(self):
        """Test get_object raises RuntimeError when client is None."""
        from modules.comms.commands.get_object import get_object

        with pytest.raises(RuntimeError, match="not initialized"):
            get_object(None, "object-1")

    def test_get_object_calls_client(self):
        """Test get_object calls client with correct args."""
        from modules.comms.commands.get_object import get_object

        client = MagicMock()
        client.get_object.return_value = {"id": "object-1", "type": "waypoint"}

        get_object(client, "object-1", timeout=5.0, retries=2)

        client.get_object.assert_called_once_with(
            object_id="object-1", timeout=5.0, max_retries=2
        )

    def test_create_object_raises_when_client_none(self):
        """Test create_object raises RuntimeError when client is None."""
        from modules.comms.commands.create_object import create_object

        with pytest.raises(RuntimeError, match="not initialized"):
            create_object(None, "object-1", content_b64="dGVzdA==", content_type="application/json")

    def test_create_object_calls_client(self):
        """Test create_object calls client with correct args."""
        from modules.comms.commands.create_object import create_object

        client = MagicMock()
        client.create_object.return_value = {"id": "object-1"}

        create_object(
            client,
            "object-1",
            content_b64="dGVzdA==",
            content_type="application/json",
            usage_hint="waypoint",
            timeout=5.0,
            retries=2,
        )

        client.create_object.assert_called_once()

    def test_update_object_raises_when_client_none(self):
        """Test update_object raises RuntimeError when client is None."""
        from modules.comms.commands.update_object import update_object

        with pytest.raises(RuntimeError, match="not initialized"):
            update_object(None, "object-1")

    def test_update_object_calls_client(self):
        """Test update_object calls client with correct args."""
        from modules.comms.commands.update_object import update_object

        client = MagicMock()
        client.update_object.return_value = {"id": "object-1", "updated": True}

        update_object(
            client,
            "object-1",
            usage_hints=["waypoint", "visited"],
            timeout=5.0,
            retries=2,
        )

        client.update_object.assert_called_once()

    def test_delete_object_raises_when_client_none(self):
        """Test delete_object raises RuntimeError when client is None."""
        from modules.comms.commands.delete_object import delete_object

        with pytest.raises(RuntimeError, match="not initialized"):
            delete_object(None, "object-1")

    def test_delete_object_calls_client(self):
        """Test delete_object calls client with correct args."""
        from modules.comms.commands.delete_object import delete_object

        client = MagicMock()
        client.delete_object.return_value = {"deleted": True}

        delete_object(client, "object-1", timeout=5.0, retries=2)

        client.delete_object.assert_called_once_with(
            object_id="object-1", timeout=5.0, max_retries=2
        )

    def test_get_objects_by_entity_raises_when_client_none(self):
        """Test get_objects_by_entity raises RuntimeError when client is None."""
        from modules.comms.commands.get_objects_by_entity import get_objects_by_entity

        with pytest.raises(RuntimeError, match="not initialized"):
            get_objects_by_entity(None, "entity-1")

    def test_get_objects_by_entity_calls_client(self):
        """Test get_objects_by_entity calls client with correct args."""
        from modules.comms.commands.get_objects_by_entity import get_objects_by_entity

        client = MagicMock()
        client.get_objects_by_entity.return_value = [{"id": "object-1"}]

        get_objects_by_entity(client, "entity-1", timeout=5.0, retries=2)

        client.get_objects_by_entity.assert_called_once_with(
            entity_id="entity-1", timeout=5.0, max_retries=2
        )

    def test_get_objects_by_task_raises_when_client_none(self):
        """Test get_objects_by_task raises RuntimeError when client is None."""
        from modules.comms.commands.get_objects_by_task import get_objects_by_task

        with pytest.raises(RuntimeError, match="not initialized"):
            get_objects_by_task(None, "task-1")

    def test_get_objects_by_task_calls_client(self):
        """Test get_objects_by_task calls client with correct args."""
        from modules.comms.commands.get_objects_by_task import get_objects_by_task

        client = MagicMock()
        client.get_objects_by_task.return_value = [{"id": "object-1"}]

        get_objects_by_task(client, "task-1", timeout=5.0, retries=2)

        client.get_objects_by_task.assert_called_once_with(
            task_id="task-1", timeout=5.0, max_retries=2
        )


class TestObjectReferenceCommands:
    """Tests for object reference command handlers."""

    def test_add_object_reference_raises_when_client_none(self):
        """Test add_object_reference raises RuntimeError when client is None."""
        from modules.comms.commands.add_object_reference import add_object_reference

        with pytest.raises(RuntimeError, match="not initialized"):
            add_object_reference(None, "object-1", entity_id="entity-1")

    def test_add_object_reference_calls_client(self):
        """Test add_object_reference calls client with correct args."""
        from modules.comms.commands.add_object_reference import add_object_reference

        client = MagicMock()
        client.add_object_reference.return_value = {"added": True}

        add_object_reference(
            client, "object-1", entity_id="entity-1", timeout=5.0, retries=2
        )

        client.add_object_reference.assert_called_once_with(
            object_id="object-1",
            entity_id="entity-1",
            task_id=None,
            timeout=5.0,
            max_retries=2,
        )

    def test_remove_object_reference_raises_when_client_none(self):
        """Test remove_object_reference raises RuntimeError when client is None."""
        from modules.comms.commands.remove_object_reference import remove_object_reference

        with pytest.raises(RuntimeError, match="not initialized"):
            remove_object_reference(None, "object-1", entity_id="entity-1")

    def test_remove_object_reference_calls_client(self):
        """Test remove_object_reference calls client with correct args."""
        from modules.comms.commands.remove_object_reference import remove_object_reference

        client = MagicMock()
        client.remove_object_reference.return_value = {"removed": True}

        remove_object_reference(
            client, "object-1", entity_id="entity-1", timeout=5.0, retries=2
        )

        client.remove_object_reference.assert_called_once_with(
            object_id="object-1",
            entity_id="entity-1",
            task_id=None,
            timeout=5.0,
            max_retries=2,
        )

    def test_get_object_references_raises_when_client_none(self):
        """Test get_object_references raises RuntimeError when client is None."""
        from modules.comms.commands.get_object_references import get_object_references

        with pytest.raises(RuntimeError, match="not initialized"):
            get_object_references(None, "object-1")

    def test_get_object_references_calls_client(self):
        """Test get_object_references calls client with correct args."""
        from modules.comms.commands.get_object_references import get_object_references

        client = MagicMock()
        client.get_object_references.return_value = [{"type": "entity", "id": "entity-1"}]

        get_object_references(client, "object-1", timeout=5.0, retries=2)

        client.get_object_references.assert_called_once_with(
            object_id="object-1", timeout=5.0, max_retries=2
        )

    def test_find_orphaned_objects_raises_when_client_none(self):
        """Test find_orphaned_objects raises RuntimeError when client is None."""
        from modules.comms.commands.find_orphaned_objects import find_orphaned_objects

        with pytest.raises(RuntimeError, match="not initialized"):
            find_orphaned_objects(None)

    def test_find_orphaned_objects_calls_client(self):
        """Test find_orphaned_objects calls client correctly."""
        from modules.comms.commands.find_orphaned_objects import find_orphaned_objects

        client = MagicMock()
        client.find_orphaned_objects.return_value = [{"id": "orphan-1"}]

        result = find_orphaned_objects(client, timeout=5.0, retries=2)

        client.find_orphaned_objects.assert_called_once_with(timeout=5.0, max_retries=2)
        assert result == [{"id": "orphan-1"}]

    def test_validate_object_references_raises_when_client_none(self):
        """Test validate_object_references raises RuntimeError when client is None."""
        from modules.comms.commands.validate_object_references import validate_object_references

        with pytest.raises(RuntimeError, match="not initialized"):
            validate_object_references(None, "object-1")

    def test_validate_object_references_calls_client(self):
        """Test validate_object_references calls client correctly."""
        from modules.comms.commands.validate_object_references import validate_object_references

        client = MagicMock()
        client.validate_object_references.return_value = {"valid": True, "errors": []}

        result = validate_object_references(client, "object-1", timeout=5.0, retries=2)

        client.validate_object_references.assert_called_once_with(
            object_id="object-1", timeout=5.0, max_retries=2
        )
        assert result == {"valid": True, "errors": []}

    def test_cleanup_object_references_raises_when_client_none(self):
        """Test cleanup_object_references raises RuntimeError when client is None."""
        from modules.comms.commands.cleanup_object_references import cleanup_object_references

        with pytest.raises(RuntimeError, match="not initialized"):
            cleanup_object_references(None, "object-1")

    def test_cleanup_object_references_calls_client(self):
        """Test cleanup_object_references calls client correctly."""
        from modules.comms.commands.cleanup_object_references import cleanup_object_references

        client = MagicMock()
        client.cleanup_object_references.return_value = {"cleaned": 5}

        result = cleanup_object_references(client, "object-1", timeout=5.0, retries=2)

        client.cleanup_object_references.assert_called_once_with(
            object_id="object-1", timeout=5.0, max_retries=2
        )
        assert result == {"cleaned": 5}


class TestDatasetCommands:
    """Tests for dataset command handlers."""

    def test_get_changed_since_raises_when_client_none(self):
        """Test get_changed_since raises RuntimeError when client is None."""
        from modules.comms.commands.get_changed_since import get_changed_since

        with pytest.raises(RuntimeError, match="not initialized"):
            get_changed_since(None, "2024-01-01T00:00:00Z")

    def test_get_changed_since_calls_client(self):
        """Test get_changed_since calls client with correct args."""
        from modules.comms.commands.get_changed_since import get_changed_since

        client = MagicMock()
        client.get_changed_since.return_value = {"entities": [], "tasks": [], "objects": []}

        get_changed_since(client, "2024-01-01T00:00:00Z", timeout=5.0, retries=2)

        client.get_changed_since.assert_called_once_with(
            timestamp="2024-01-01T00:00:00Z", timeout=5.0, max_retries=2
        )

    def test_get_full_dataset_raises_when_client_none(self):
        """Test get_full_dataset raises RuntimeError when client is None."""
        from modules.comms.commands.get_full_dataset import get_full_dataset

        with pytest.raises(RuntimeError, match="not initialized"):
            get_full_dataset(None)

    def test_get_full_dataset_calls_client(self):
        """Test get_full_dataset calls client correctly."""
        from modules.comms.commands.get_full_dataset import get_full_dataset

        client = MagicMock()
        client.get_full_dataset.return_value = {"entities": [], "tasks": [], "objects": []}

        get_full_dataset(client, timeout=5.0, retries=2)

        client.get_full_dataset.assert_called_once_with(timeout=5.0, max_retries=2)


class TestFunctionRegistry:
    """Tests for the FUNCTION_REGISTRY."""

    def test_function_registry_contains_all_commands(self):
        """Test FUNCTION_REGISTRY contains all expected command functions."""
        from modules.comms.commands import FUNCTION_REGISTRY

        expected_commands = [
            "test_echo",
            "health_check",
            "list_entities",
            "list_tasks",
            "get_entity",
            "get_entity_by_alias",
            "create_entity",
            "update_entity",
            "delete_entity",
            "checkin_entity",
            "update_telemetry",
            "get_task",
            "get_tasks_by_entity",
            "create_task",
            "update_task",
            "delete_task",
            "transition_task_status",
            "acknowledge_task",
            "complete_task",
            "fail_task",
            "list_objects",
            "get_object",
            "get_objects_by_entity",
            "get_objects_by_task",
            "update_object",
            "delete_object",
            "add_object_reference",
            "remove_object_reference",
            "find_orphaned_objects",
            "get_object_references",
            "validate_object_references",
            "cleanup_object_references",
            "create_object",
            "get_changed_since",
            "get_full_dataset",
        ]

        for cmd in expected_commands:
            assert cmd in FUNCTION_REGISTRY, f"Missing command: {cmd}"

    def test_function_registry_functions_are_callable(self):
        """Test all functions in FUNCTION_REGISTRY are callable."""
        from modules.comms.commands import FUNCTION_REGISTRY

        for name, func in FUNCTION_REGISTRY.items():
            assert callable(func), f"Function {name} is not callable"
