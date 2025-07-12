from ..request.request import RequestCtx, ReqType
from ..responses import middleware_response, MethodNotAllowedResponse
from ..utils import has_base
from .endpoints import ApiEndpoint, ApiExecutor
from .api import Api

class BoundApiDescriptor:
    def __init__(self, paths: dict[ReqType, dict[str, ApiExecutor]], methods: dict[str, list[ReqType]], owner: object):
        self.paths = paths
        self.methods = methods
        self.owner = owner

    def dispatch(self, req: RequestCtx) -> middleware_response | MethodNotAllowedResponse:
        if req.req_type not in self.methods[req.path]:
            return MethodNotAllowedResponse()
        endpoint = self.paths[req.req_type][req.path]
        return endpoint(self.owner, req)

    @property
    def is_implimented(self) -> bool:
        """
        Check if all endpoints are implemented.
        An endpoint is considered implemented if it has a valid function signature and is not a placeholder.
        """
        for req_type, path_data in self.paths.items():
            for path, api_endpoint in path_data.items():
                if not api_endpoint.is_implimented:
                    return False
        return True


class ApiDescription:
    def __init__(self, owner: type[Api]):
        self.paths: dict[ReqType, dict[str, ApiEndpoint]] = {}
        self.methods: dict[str, list[ReqType]] = {}
        self.function_names: dict[str, ApiEndpoint] = {}
        self.owner = owner

    def add_path(self, req_type: ReqType, path: str, api_endpoint: ApiEndpoint):
        request_paths = self.paths.setdefault(req_type, {})
        if eapi_endpoint := request_paths.get(path):
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
        methods = self.methods.setdefault(path, [])
        if req_type not in methods:
            methods.append(req_type)
        request_paths[path] = api_endpoint

    def is_compatable(self, other: "ApiDescription") -> bool:
        ...

    def bind(self, obj: object) -> BoundApiDescriptor:
        """
        Bind the API description to an object instance.
        This allows the API endpoints to be executed with the instance as the owner.
        """
        if not has_base(obj.__class__, Api):
            raise TypeError(
                f"{obj.__class__.__name__} must inherit from ApiDescriptor to bind API description"
            )
        paths: dict[ReqType, dict[str, ApiExecutor]] = {}
        for req_type, path_data in self.paths.items():
            request_paths = paths.setdefault(req_type, {})
            for path, api_endpoint in path_data.items():
                api_executor = ApiExecutor(api_endpoint, obj)
                request_paths[path] = api_executor
        bound_api_descr = BoundApiDescriptor(paths, self.methods, obj)
        return bound_api_descr
