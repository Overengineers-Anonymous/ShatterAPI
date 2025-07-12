from typing import Callable, Protocol, Sequence, overload

from fastapi.background import P

from ..middlewear import Middleware, PlaceholderMiddleware
from ..utils import has_base
from .descriptors import ApiDescription, BoundApiDescriptor
from .endpoints import ApiEndpoint
from .api import Api
from ..request.request import ReqType


class Mapping:
    API_DESCR_NAME = "__api_descr"
    API_BOUND_NAME = "__api_descr_bound"

    def __init__(
        self,
        subpath: str = "",
        middleware: list[Middleware] | None = None,
        placeholder_middleware: list[PlaceholderMiddleware | Middleware] | None = None,
    ):
        self.placeholder_middleware = placeholder_middleware or []
        self.middleware = middleware or []
        self.subpath = subpath
        self.routes: dict[ReqType, dict[str, ApiEndpoint]] = {}
        self._owner: type[Api] | None = None

    def route(
        self,
        path: str,
        methods: list[ReqType] | None = None,
        middleware: list[Middleware] | None = None,
    ) -> Callable:
        middleware = middleware or []
        methods = methods or [ReqType.GET]

        def register(func: Callable) -> Callable:
            for req_type in methods:
                self.routes.setdefault(req_type, {})[path] = ApiEndpoint(
                    path, func, req_type, self.middleware + middleware
                )
            return func

        return register

    def build_description(self, owner: type) -> ApiDescription:
        api_description = ApiDescription(owner)
        for base in owner.__mro__[::-1]:
            mapping = getattr(base, "mapping", None)
            if isinstance(mapping, Mapping):
                for req_type, path_data in mapping.routes.items():
                    for path, api_endpoint in path_data.items():
                        if not api_endpoint.path.startswith(self.subpath):
                            api_endpoint.path = self.subpath + api_endpoint.path
                        api_description.add_path(req_type, path, api_endpoint)
        setattr(owner, self.API_DESCR_NAME, api_description)
        return api_description

    @property
    def owner(self) -> type[Api]:
        if self._owner is None:
            raise RuntimeError("Mapping has not been initialized properly")
        return self._owner

    def __set_name__(self, owner, name):
        self._owner = owner
        if not has_base(owner, Api):
            raise TypeError(f"{owner.__name__} must inherit from ApiDescriptor to use Mapping")
        if name != "mapping":
            raise TypeError(f"Mapping must be named 'mapping', not '{name}'")
        for api_paths in self.routes.values():
            for api_endpoint in api_paths.values():
                api_endpoint.owner = owner

    @overload
    def __get__(self, obj: None, objtype: type) -> "Mapping": ...

    @overload
    def __get__(self, obj: Api, objtype: type) -> BoundApiDescriptor: ...

    def __get__(self, obj: Api | None, objtype: type | None = None) -> "BoundApiDescriptor | Mapping":
        if obj is None and objtype is not None:
            return self

        if obj is None:
            raise TypeError("Mapping cannot be accessed without an instance or type")

        if not has_base(obj.__class__, Api):
            raise TypeError(f"{obj.__class__.__name__} must inherit from ApiDescriptor to use Mapping")

        api_description: ApiDescription | None = getattr(obj, self.API_DESCR_NAME, None)
        if api_description is None:
            raise RuntimeError(f"{obj.__class__.__name__} has not built its API description yet")
        bound_api_descr: BoundApiDescriptor | None = getattr(obj, self.API_BOUND_NAME, None)
        if bound_api_descr is None:
            bound_api_descr = api_description.bind(obj)
            setattr(obj, self.API_BOUND_NAME, bound_api_descr)
        return bound_api_descr
