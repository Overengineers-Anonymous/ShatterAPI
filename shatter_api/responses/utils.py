from typing import Any, Literal, Union, cast, get_args, get_origin

from pydantic import BaseModel

from ..type_extraction import parse_generic
from .response_types import JsonResponse
from .responses import InheritedResponses, Response, ResponseInfo


def _parse_response(
    type_: Any, target_type: type
) -> tuple[Any, ...] | type[InheritedResponses] | None:
    origin_type = get_origin(type_)
    if issubclass(type_, BaseModel):
        return parse_generic(
            JsonResponse[
                type_,
                200,
            ],
            Response,
        )
    if origin_type:
        if issubclass(origin_type, Response):
            return parse_generic(type_, target_type)
    else:
        if issubclass(type_, InheritedResponses):
            return InheritedResponses
    return None


def dedupe_responses(responses: list[ResponseInfo]) -> list[ResponseInfo]:
    """
    Deduplicates a list of ResponseInfo objects based on their body, code, and header attributes.
    Args:
        responses (list[ResponseInfo]): The list of ResponseInfo objects to deduplicate.
    Returns:
        list[ResponseInfo]: A new list containing unique ResponseInfo objects.
    """
    seen = set()
    unique_responses = []
    for response in responses:
        key = (response.body, response.code, response.header)
        if key not in seen:
            seen.add(key)
            unique_responses.append(response)
    return unique_responses


def get_response_info(
    type_: Any, inherited_responses: list[ResponseInfo]
) -> list[ResponseInfo]:
    """
    Extracts and returns a list of ResponseInfo objects based on the provided type annotation.
    If the provided type is a Union, it iterates through each type in the Union and collects
    ResponseInfo objects for each type that is a subclass of Response. Otherwise, it collects
    ResponseInfo objects for the given type directly.
    Args:
        type_ (Any): The type annotation to analyze, which may be a single type or a Union of types.
    Returns:
        list[ResponseInfo]: A list of ResponseInfo objects extracted from the provided type annotation.
    """

    response_args: list[tuple[Any, ...] | None | type[InheritedResponses]] = []
    if get_origin(type_) is Union:
        union_args = get_args(type_)
        for arg in union_args:
            response_args.append(_parse_response(arg, Response))
    else:
        response_args.append(_parse_response(type_, Response))
    responses: list[ResponseInfo] = []
    for response_arg in response_args:
        if response_arg is not None and isinstance(response_arg, tuple):
            body, code, header = response_arg
            if get_origin(code) is Literal:
                literal_args = get_args(code)
                if literal_args:
                    code = literal_args[0]
                else:
                    raise ValueError("Literal code must have at least one value")
            code = cast(int, code)
            responses.append(ResponseInfo(body=body, code=code, header=header))
        elif response_arg and issubclass(response_arg, InheritedResponses):
            responses.extend(inherited_responses)

    return dedupe_responses(responses)
