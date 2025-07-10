from ast import In
from typing import Literal, Protocol, Any, Self, Union, get_args, get_origin, cast
from pydantic import BaseModel, ConfigDict, ValidationError
from types import get_original_bases
from .request import RequestBody, RequestHeaders, RequestQueryParams
from .statuses import HTTP_STATUS_CODES
from .type_extraction import parse_generic


class BaseHeaders(BaseModel):
    model_config = ConfigDict(frozen=True)


def to_header_name(header: str) -> str:
    """
    Converts a header name to the format used in the header dictionary.
    """
    return header.replace("_", "-").title()


class Response[T: BaseModel | str, C: int = Literal[200], H: BaseHeaders = BaseHeaders]:
    def __init__(self, body: T, code: C, header: H = BaseHeaders()) -> None:
        self._body = body
        self._header = header
        self._code = code

    @property
    def code(self) -> str:
        """
        The HTTP status code of the response.
        """
        return f"{self._code} {HTTP_STATUS_CODES[self._code]}"

    @property
    def body(self) -> str:
        """
        The body of the response, which can be a Pydantic model or a string.
        """
        if isinstance(self._body, BaseModel):
            return self._body.model_dump_json()
        return self._body

    @property
    def headers(self) -> dict[str, Any]:
        """
        The headers of the response, which can be a Pydantic model or a dictionary.
        """
        headers = self._header.model_dump()
        final_headers = {}
        for header, value in headers.items():
            final_headers[to_header_name(header)] = value
        return final_headers

class InheritedResponses: ...

class ResponseInfo:
    def __init__(self, body: BaseModel, code: int, header: BaseModel | None = None) -> None:
        self.body = body
        self.header = header if header is not None else BaseModel()
        self.code = code

    def __repr__(self) -> str:
        return f"ResponseInfo(body={self.body}, code={self.code}, header={self.header})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ResponseInfo):
            return False
        return (
            self.body == other.body
            and self.code == other.code
            and self.header == other.header
        )

class JsonHeaders(BaseHeaders):
    """
    This is a sample header model for the response.
    """

    model_config = ConfigDict(frozen=True)
    Content_Type: str = "application/json"


class JsonResponse[D: BaseModel | str, C: int = Literal[200], H: JsonHeaders = JsonHeaders](Response[D, C, H]):
    def __init__(self, body: D, code: C = 200, header: H = JsonHeaders()) -> None:
        if header is None:
            super().__init__(body, code, JsonHeaders())
        else:
            super().__init__(body, code, header)


class TextHeaders(BaseHeaders):
    """
    This is a sample header model for the response.
    """

    Content_Type: str = "text/plain"


class TextResponse[D: str, C: int = Literal[200], H: TextHeaders = TextHeaders](Response[D, C, H]): ...


class NotFoundData(BaseModel):
    """
    This is a sample data model for the Not Found response.
    """

    detail: str = "Not Found"


class NotFoundResponse(JsonResponse[NotFoundData, Literal[404], JsonHeaders]):
    def __init__(self):
        super().__init__(NotFoundData(), 404, JsonHeaders())


class ValidationErrorInfo(BaseModel):
    loc: list[str | int] = []
    msg: str = "Validation Error"
    type: str = "validation_error"


class ValidationErrorData(BaseModel):
    """
    This is a sample data model for the Validation Error response.
    """

    detail: list[ValidationErrorInfo] = []
    kind: str

middleware_response = Response[BaseModel, int, BaseHeaders] | InheritedResponses


class ValidationErrorResponse(JsonResponse[ValidationErrorData, Literal[422], JsonHeaders]):
    def __init__(self, error_data: ValidationErrorData):
        super().__init__(error_data, 422, JsonHeaders())

    @classmethod
    def from_validation_error(cls, error: ValidationError, models: list[type[BaseModel]] = []) -> "ValidationErrorResponse":
        """
        Creates a ValidationErrorResponse from a Pydantic ValidationError.

        Args:
            error (ValidationError): The Pydantic ValidationError to convert.

        Returns:
            ValidationErrorResponse: A response containing the validation errors.
        """
        name_mapping: dict[str, str] = {}
        for _type in models:
            error_type = "unknown"
            if issubclass(_type, RequestBody):
                error_type = "request_body"
            elif issubclass(_type, RequestHeaders):
                error_type = "request_headers"
            elif issubclass(_type, RequestQueryParams):
                error_type = "request_query_params"
            name_mapping[_type.__name__] = error_type
        errors: list[ValidationErrorInfo] = []
        for error_details in error.errors():
            loc = list(error_details["loc"])
            msg = error_details["msg"]
            type_ = error_details["type"]
            if name_mapping.get(error.title, "unknown") == "request_headers":
                end_loc = loc[-1]
                if isinstance(end_loc, str):
                    # Convert header names to snake_case
                    loc[-1] = to_header_name(end_loc)
            errors.append(ValidationErrorInfo(loc=loc, msg=msg, type=type_))

        return cls(ValidationErrorData(detail=errors, kind=name_mapping.get(error.title, "unknown")))


def _parse_response(type_: Any, target_type: type) -> tuple[Any, ...] | type[InheritedResponses] | None:
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


def get_response_info(type_: Any, inherited_responses: list[ResponseInfo]) -> list[ResponseInfo]:
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
