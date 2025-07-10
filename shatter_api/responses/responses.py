from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from ..statuses import HTTP_STATUS_CODES


def to_header_name(header: str) -> str:
    """
    Converts a header name to the format used in the header dictionary.
    """
    return header.replace("_", "-").title()


class BaseHeaders(BaseModel):
    model_config = ConfigDict(frozen=True)


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


class InheritedResponses(Response[BaseModel, int, BaseHeaders]): ...


class ResponseInfo:
    def __init__(
        self, body: BaseModel, code: int, header: BaseModel | None = None
    ) -> None:
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


middleware_response = Response[BaseModel, int, BaseHeaders] | InheritedResponses
