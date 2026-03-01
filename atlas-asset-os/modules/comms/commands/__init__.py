from __future__ import annotations

import importlib.machinery
import inspect
import logging
import sys
from functools import lru_cache
from types import ModuleType
from typing import Any, Callable

from atlas_meshtastic_bridge.client import MeshtasticClient

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wrapper configuration tables
#
# Each MeshtasticClient method with a ``max_retries`` parameter is auto-wrapped
# into a legacy-compatible command function.  The tables below control how each
# wrapper's signature and call-forwarding differ from the raw client method:
#
#   _EXCLUDED_METHODS        – client methods to skip entirely.
#   _ALIAS_BY_METHOD         – wrapper ``__name__`` override (e.g. test_echo → echo).
#   _PARAM_RENAMES           – {method: {client_param: legacy_param}} renames
#                              exposed to callers while back-mapping at call time.
#   _REMOVED_PARAMS          – params dropped from the wrapper signature.
#   _LEGACY_POSITIONAL_PARAMS– params promoted to POSITIONAL_OR_KEYWORD.
#   _EXTRA_LEGACY_PARAMS     – extra inspect.Parameter objects appended to the
#                              wrapper signature (not present on the client).
#   _DEFAULT_OVERRIDES       – override a parameter's default value in the wrapper.
#   _CONDITIONAL_PARAMS      – params only forwarded to the client when not None.
# ---------------------------------------------------------------------------

_EXCLUDED_METHODS = {"send_request", "start_task"}
_ALIAS_BY_METHOD = {"test_echo": "echo"}
# Maps client param name → legacy wrapper param name.
# e.g. the client's ``since`` param is exposed as ``timestamp`` to legacy callers.
_PARAM_RENAMES = {"get_changed_since": {"since": "timestamp"}}
_REMOVED_PARAMS = {"checkin_entity": {"fields"}, "list_tasks": {"offset"}}
_LEGACY_POSITIONAL_PARAMS = {
    "list_entities": {"limit", "offset"},
    "list_tasks": {"status", "limit"},
}
_EXTRA_LEGACY_PARAMS = {
    "get_objects_by_entity": {
        "offset": inspect.Parameter(
            "offset",
            inspect.Parameter.KEYWORD_ONLY,
            default=None,
            annotation=int | None,
        )
    },
    "get_objects_by_task": {
        "offset": inspect.Parameter(
            "offset",
            inspect.Parameter.KEYWORD_ONLY,
            default=None,
            annotation=int | None,
        )
    },
}
_DEFAULT_OVERRIDES = {
    "checkin_entity": {"status_filter": None, "limit": None},
    "find_orphaned_objects": {"limit": None, "offset": None},
    "get_object": {"download": None},
    "get_objects_by_entity": {"limit": None},
    "get_objects_by_task": {"limit": None},
    "get_tasks_by_entity": {"limit": None},
    "list_entities": {"limit": None, "offset": None},
    "list_objects": {"limit": None, "offset": None},
    "list_tasks": {"limit": None},
}
_CONDITIONAL_PARAMS = {
    "checkin_entity": {
        "latitude",
        "longitude",
        "altitude_m",
        "speed_m_s",
        "heading_deg",
        "status_filter",
        "limit",
        "since",
    },
    "complete_task": {"result"},
    "find_orphaned_objects": {"limit", "offset"},
    "get_changed_since": {"limit_per_type"},
    "get_full_dataset": {"entity_limit", "task_limit", "object_limit"},
    "get_object": {"download"},
    # offset is optional in legacy wrappers and should only be forwarded when provided.
    # Combined with _EXTRA_LEGACY_PARAMS + runtime signature support checks, this keeps
    # backward-compatible wrapper signatures without forcing unsupported client kwargs.
    "get_objects_by_entity": {"limit", "offset"},
    "get_objects_by_task": {"limit", "offset"},
    "get_tasks_by_entity": {"limit"},
    "list_entities": {"limit", "offset"},
    "list_objects": {"limit", "offset", "content_type"},
    "list_tasks": {"status", "limit"},
}


def _iter_command_methods() -> list[str]:
    method_names: list[str] = []
    for name, member in inspect.getmembers(MeshtasticClient, predicate=callable):
        if name.startswith("_") or name in _EXCLUDED_METHODS:
            continue
        signature = inspect.signature(member)
        if "max_retries" not in signature.parameters:
            continue
        method_names.append(name)
    return method_names


def _legacy_param_name(method_name: str, parameter_name: str) -> str:
    method_renames = _PARAM_RENAMES.get(method_name, {})
    if parameter_name == "max_retries":
        return "retries"
    return method_renames.get(parameter_name, parameter_name)


def _client_param_name(method_name: str, parameter_name: str) -> str:
    if parameter_name == "retries":
        return "max_retries"
    for client_name, legacy_name in _PARAM_RENAMES.get(method_name, {}).items():
        if legacy_name == parameter_name:
            return client_name
    return parameter_name


def _build_wrapper_signature(method_name: str, method: Callable[..., Any]) -> inspect.Signature:
    """Build a legacy-compatible command signature from a MeshtasticClient method."""
    params = [
        inspect.Parameter(
            "client", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any
        )
    ]

    removed = _REMOVED_PARAMS.get(method_name, set())
    default_overrides = _DEFAULT_OVERRIDES.get(method_name, {})

    for parameter in inspect.signature(method).parameters.values():
        if parameter.name == "self" or parameter.name in removed:
            continue

        legacy_name = _legacy_param_name(method_name, parameter.name)
        if legacy_name in _LEGACY_POSITIONAL_PARAMS.get(method_name, set()):
            parameter = parameter.replace(
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD
            )
        if legacy_name in default_overrides:
            parameter = parameter.replace(default=default_overrides[legacy_name])
        parameter = parameter.replace(name=legacy_name)
        params.append(parameter)

    params.extend(_EXTRA_LEGACY_PARAMS.get(method_name, {}).values())
    return inspect.Signature(params)


def _create_wrapper(method_name: str) -> Callable[..., Any]:
    """Create a command wrapper with client initialization and argument forwarding."""
    method = getattr(MeshtasticClient, method_name)
    signature = _build_wrapper_signature(method_name, method)
    conditional_params = _CONDITIONAL_PARAMS.get(method_name, set())

    def _wrapper(client: Any, *args: Any, **kwargs: Any) -> Any:
        if client is None:
            raise RuntimeError("Meshtastic client is not initialized")

        bound = signature.bind(client, *args, **kwargs)
        bound.apply_defaults()

        bound_client_method = getattr(client, method_name)
        client_cls: type = type(client)
        client_params, client_accepts_var_kwargs = _client_call_shape(
            client_cls, method_name
        )

        call_kwargs: dict[str, Any] = {}
        for name in signature.parameters:
            if name == "client":
                continue
            value = bound.arguments[name]
            if name in conditional_params and value is None:
                continue
            client_name = _client_param_name(method_name, name)
            if not client_accepts_var_kwargs and client_name not in client_params:
                continue
            call_kwargs[client_name] = value

        return bound_client_method(**call_kwargs)

    _wrapper.__name__ = _ALIAS_BY_METHOD.get(method_name, method_name)
    _wrapper.__module__ = __name__
    _wrapper.__signature__ = signature  # type: ignore[attr-defined]
    return _wrapper


@lru_cache(maxsize=None)
def _client_call_shape(
    client_type: type, method_name: str
) -> tuple[frozenset[str], bool]:
    try:
        client_method = getattr(client_type, method_name)
        client_signature = inspect.signature(client_method)
    except (AttributeError, TypeError, ValueError):
        return frozenset(), True

    client_params = {
        name for name in client_signature.parameters if name not in {"self", "cls"}
    }
    client_accepts_var_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in client_signature.parameters.values()
    )
    return frozenset(client_params), client_accepts_var_kwargs


def _register_legacy_submodule(
    module_name: str, function_name: str, function: Callable[..., Any]
) -> None:
    fqn = f"{__name__}.{module_name}"
    module = ModuleType(fqn)
    module.__dict__[function_name] = function
    module.__file__ = __file__
    module.__spec__ = importlib.machinery.ModuleSpec(fqn, None, origin=__file__)
    sys.modules[fqn] = module


FUNCTION_REGISTRY: dict[str, Callable[..., Any]] = {}

try:
    for _method_name in _iter_command_methods():
        _function = _create_wrapper(_method_name)
        globals()[_method_name] = _function
        FUNCTION_REGISTRY[_method_name] = _function

        _module_name = _ALIAS_BY_METHOD.get(_method_name, _method_name)
        _register_legacy_submodule(_module_name, _module_name, _function)
except Exception:
    _log.exception(
        "Failed to build dynamic command wrappers from MeshtasticClient. "
        "The commands package will be importable but FUNCTION_REGISTRY may be incomplete."
    )

__all__ = list(FUNCTION_REGISTRY.keys())
