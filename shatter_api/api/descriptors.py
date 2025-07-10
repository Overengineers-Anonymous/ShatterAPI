from ..request import RequestCtx
from ..responses.responses import middleware_response
from ..utils import has_base
from .endpoints import ApiEndpoint, ApiExecutor
from .api import Api


class BoundApiDescriptor:
    def __init__(self, paths: dict[str, ApiExecutor], owner: object):
        self.paths = paths
        self.owner = owner

    def dispatch(self, path: str, req: RequestCtx) -> middleware_response:
        endpoint = self.paths[path]
        return endpoint(self.owner, req)


class ApiDescription:
    def __init__(self, owner: type[Api]):
        self.paths: dict[str, ApiEndpoint] = {}
        self.function_names: dict[str, ApiEndpoint] = {}
        self.owner = owner

    def add_path(self, path: str, api_endpoint: ApiEndpoint):
        if eapi_endpoint := self.paths.get(path):
            if eapi_endpoint.func_sig.name != api_endpoint.func_sig.name:
                raise TypeError(
                    f"ApiDescriptor '{api_endpoint.owner.__name__}' rebinds path '{path}' to another method '{api_endpoint.func_sig.name}'"
                )
            if not eapi_endpoint.func_sig.compatible_with(api_endpoint.func_sig):
                raise TypeError(
                    f"Function '{api_endpoint.func_sig.name}' in '{api_endpoint.owner.__name__}' is not compatible with base function in '{eapi_endpoint.owner.__name__}'"
                )
        else:
            if eapi_endpoint := self.function_names.get(api_endpoint.func_sig.name):
                raise TypeError(
                    f"Method '{api_endpoint.func_sig.name}' is already bound to path '{eapi_endpoint.path}' in ApiDescriptor '{eapi_endpoint.owner.__name__}'"
                )
        self.function_names[api_endpoint.func_sig.name] = api_endpoint
        self.paths[path] = api_endpoint

    def bind(self, obj: object) -> BoundApiDescriptor:
        """
        Bind the API description to an object instance.
        This allows the API endpoints to be executed with the instance as the owner.
        """
        if not has_base(obj.__class__, Api):
            raise TypeError(
                f"{obj.__class__.__name__} must inherit from ApiDescriptor to bind API description"
            )
        paths = {}
        for path, api_endpoint in self.paths.items():
            api_executor = ApiExecutor(api_endpoint, obj)
            paths[path] = api_executor
        bound_api_descr = BoundApiDescriptor(paths, obj)
        return bound_api_descr
