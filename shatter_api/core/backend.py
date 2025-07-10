from .request import ReqType
from .responses import NotFoundResponse
from .api import Api, RequestCtx
from urllib.parse import parse_qs


class WsgiDispatcher:
    """
    A WSGI dispatcher that handles requests and responses.
    """

    def __init__(self, api_descriptor: Api):
        self.api_descriptor = api_descriptor

    def __call__(self, environ, start_response):
        """
        Call the WSGI application with the given environment and start response.
        """
        query_params = parse_qs(environ.get("QUERY_STRING", ""))
        query_params = {k: v[0] for k, v in query_params.items()}

        reqctx = RequestCtx.new(
            ReqType(environ["REQUEST_METHOD"]),
            body=environ.get("wsgi.input"),
            headers={k.replace("HTTP_", ""): v for k, v in environ.items() if k.startswith("HTTP_")},
            query_params=query_params,
        )

        path = environ.get("PATH_INFO", "/")
        try:
            response = self.api_descriptor.mapping.dispatch(path, reqctx)
        except KeyError:
            response = NotFoundResponse()

        start_response(
            str(response.code),
            response.headers.items(),
        )
        if isinstance(response.body, str):
            return [response.body.encode("utf-8")]
        elif hasattr(response.body, "model_dump_json"):
            return [response.body.model_dump_json().encode("utf-8")]
        else:
            raise ValueError("Response body must be a string or a Pydantic model.")
