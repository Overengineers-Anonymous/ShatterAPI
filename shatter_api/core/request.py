from enum import Enum
from typing import Any
from pydantic import BaseModel


@staticmethod
def from_header_name(header: str) -> str:
    """
    Converts a header name to the format used in the header dictionary.
    """
    return header.replace("-", "_").lower()


class ReqType(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class RequestCtx:
    def __init__(self, req_type: ReqType, body: Any, headers: dict[str, str], query_params: dict[str, str]) -> None:
        self.req_type: ReqType = req_type
        self.body: dict[str, Any] = {"body": body}
        self.headers: dict[str, str] = headers if headers is not None else {}
        self.query_params: dict[str, str] = query_params if query_params is not None else {}

    @classmethod
    def new(
        cls,
        req_type: ReqType,
        body: Any = None,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
    ) -> "RequestCtx":
        if headers is None:
            headers = {}
        else:
            headers = {from_header_name(k): v for k, v in headers.items()} # FIXME: handle headers with underscores
        if query_params is None:
            query_params = {}
        return cls(req_type=req_type, body=body, headers=headers, query_params=query_params)


class RequestBody(BaseModel): ...


class RequestHeaders(BaseModel): ...


class RequestQueryParams(BaseModel): ...


class RequestInfo:
    def __init__(self, body: type[RequestBody], headers: type[RequestHeaders], query_params: type[RequestQueryParams]) -> None:
        self.body = body
        self.headers = headers
        self.query_params = query_params
