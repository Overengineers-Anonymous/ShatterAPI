from types import get_original_bases
from typing import Any, Union, get_args, get_origin


def parse_generic(type_: type , target_type: type) -> tuple[Any] | None:
    """
    Parses a generic response type and extracts response information.

    This function analyses a generic type annotation (typically related to API response types)
    and returns a list of `ResponseInfo` objects describing the response body, status code,
    and headers. It recursively traverses the type's base classes to collect all relevant
    response information.

    Args:
        type_ (Any): The generic type annotation to parse, expected to be a specialization
            of a `Response` type or a type with `Response` in its inheritance hierarchy.

    Returns:
        list[ResponseInfo]: A list of `ResponseInfo` objects extracted from the given type.

    Note:
        This function relies on internal attributes such as `__type_params__`, `__args__`,
        and utility functions like `get_args`, `get_origin`, and `get_original_bases`.
        It is intended for advanced use cases involving generic type introspection.
    """
    param_map = {}  # what the fuck is this, read this at your own peril
    args = get_args(type_)
    origin_type = get_origin(type_) or type_
    if origin_type is target_type:
        if args:
            return args
        else: # generic type passed is relying on defaults
            return tuple(default_arg.__default__ for default_arg in origin_type.__type_params__)

    type_params = origin_type.__type_params__
    for name, type_ in zip(type_params, args):
        param_map[name] = type_
    for base_type in get_original_bases(origin_type):
        origin_base_type = get_origin(base_type)
        if origin_base_type and issubclass(origin_base_type, target_type):
            generic_args = []
            for arg in base_type.__args__:
                param = param_map.get(arg) or arg
                generic_args.append(param)
            return parse_generic(origin_base_type[*generic_args], target_type)
        else:
            return parse_generic(base_type, target_type)

    return None


def parse_union_generic(type_: Any, target_type: type) -> list[tuple[Any]]:
    if get_origin(type_) is Union:
        results = []
        args = get_args(type_)
        for arg in args:
            results.append(parse_generic(arg, target_type))
        return results
    return []
