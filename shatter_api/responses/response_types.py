from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from ..request.request import RequestBody, RequestHeaders, RequestQueryParams
from .responses import BaseHeaders, Response, to_header_name


class JsonHeaders(BaseHeaders):
    """
    This is a sample header model for the response.
    """

    model_config = ConfigDict(frozen=True)
    Content_Type: str = "application/json"


class JsonResponse[
    D: BaseModel | str,
    C: int = Literal[200],
    H: JsonHeaders = JsonHeaders,
](Response[D, C, H]):
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


class TextResponse[D: str, C: int = Literal[200], H: TextHeaders = TextHeaders](
    Response[D, C, H]
):
    def __init__(self, body: D, code: C = 200, header: H = TextHeaders()) -> None:
        if header is None:
            super().__init__(body, code, TextHeaders())
        else:
            super().__init__(body, code, header)


class NotFoundData(BaseModel):
    """
    This is a sample data model for the Not Found response.
    """

    detail: str = "Not Found"


class NotFoundResponse(JsonResponse[NotFoundData, Literal[404], JsonHeaders]):
    def __init__(self):
        super().__init__(NotFoundData(), 404, JsonHeaders())

class MethodNotAllowedData(BaseModel):
    """
    This is a sample data model for the Method Not Allowed response.
    """

    detail: str = "Method Not Allowed"

class MethodNotAllowedResponse(
    JsonResponse[MethodNotAllowedData, Literal[405], JsonHeaders]
):
    def __init__(self):
        super().__init__(MethodNotAllowedData(), 405, JsonHeaders())

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


class ValidationErrorResponse(
    JsonResponse[ValidationErrorData, Literal[422], JsonHeaders]
):
    def __init__(self, error_data: ValidationErrorData):
        super().__init__(error_data, 422, JsonHeaders())

    @classmethod
    def from_validation_error(
        cls, error: ValidationError, models: list[type[BaseModel]] = []
    ) -> "ValidationErrorResponse":
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

        return cls(
            ValidationErrorData(
                detail=errors, kind=name_mapping.get(error.title, "unknown")
            )
        )
