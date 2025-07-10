from typing import Callable, Protocol, overload

from ..middlewear import Middleware
from ..utils import has_base
from .descriptors import ApiDescription, BoundApiDescriptor
from .endpoints import ApiEndpoint
from .api import Api
from ..request import ReqType


class Mapping:
    API_DESCR_NAME = "__api_descr"
    API_BOUND_NAME = "__api_descr_bound"

    def __init__(self, subpath: str = "", middleware: list[Middleware] | None = None):
        self.middleware = middleware or []
        self.subpath = subpath
        self.routes: dict[ReqType, dict[str, ApiEndpoint]] = {}
        self._owner: type[Api] | None = None

    def route(self, path: str, methods: list[ReqType] | None = None, middleware: list[Middleware] | None = None) -> Callable:
        middleware = middleware or self.middleware
        methods = methods or [ReqType.GET]
        def register(func: Callable) -> Callable:
            for req_type in methods:
                self.routes.setdefault(req_type, {})[path] = ApiEndpoint(path, func, req_type, self.middleware + middleware)
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
            raise TypeError(
                f"{owner.__name__} must inherit from ApiDescriptor to use Mapping"
            )
        if name != "mapping":
            raise TypeError(f"Mapping must be named 'mapping', not '{name}'")
        for api_paths in self.routes.values():
            for api_endpoint in api_paths.values():
                api_endpoint.owner = owner

    @overload
    def __get__(self, obj: None, objtype: type) -> "Mapping": ...

    @overload
    def __get__(self, obj: Api, objtype: type) -> BoundApiDescriptor: ...

    def __get__(
        self, obj: Api | None, objtype: type | None = None
    ) -> "BoundApiDescriptor | Mapping":
        if obj is None and objtype is not None:
            return self

        if obj is None:
            raise TypeError("Mapping cannot be accessed without an instance or type")

        if not has_base(obj.__class__, Api):
            raise TypeError(
                f"{obj.__class__.__name__} must inherit from ApiDescriptor to use Mapping"
            )

        api_description: ApiDescription | None = getattr(obj, self.API_DESCR_NAME, None)
        if api_description is None:
            raise RuntimeError(
                f"{obj.__class__.__name__} has not built its API description yet"
            )
        bound_api_descr: BoundApiDescriptor | None = getattr(
            obj, self.API_BOUND_NAME, None
        )
        if bound_api_descr is None:
            bound_api_descr = api_description.bind(obj)
            setattr(obj, self.API_BOUND_NAME, bound_api_descr)
        return bound_api_descr


# class RouteMap[T: "Api"]:
#     """
#     Manages routing configuration for API descriptors.
#
#     Provides a fluent interface for building API route hierarchies
#     and binding implementations to specific paths.
#     """
#
#     def __init__(self, root: str, descriptor: type[T]):
#         """
#         Initialize a route map with root path and descriptor type.
#
#         Args:
#             root: Root path for this route map
#             descriptor: ApiDescriptor type to manage
#         """
#         self.root = root
#         self.api_descriptor = descriptor
#
#     def add_descriptor[TD](self, root: str, descriptor: "type[TD]") -> "RouteMap[TD]":
#         """
#         Add a child descriptor to this route map.
#
#         Args:
#             root: Root path for the child descriptor
#             descriptor: Child ApiDescriptor type
#
#         Returns:
#             New RouteMap for the child descriptor
#         """
#         return RouteMap(self.root + root, descriptor)
#
#     def api_implementation(self, root: str, implementation: "T"):
#         """
#         Bind an API implementation to a specific root path.
#
#         Args:
#             root: Root path for the implementation
#             implementation: ApiImplementation instance
#         """
#         # TODO: Implement implementation binding logic
#         pass
#
#     def cast_to_child(self, path: str) -> "T":
#         """
#         Cast this route map to a child type at the specified path.
#
#         Args:
#             path: Path to cast to
#
#         Returns:
#             Casted instance of the child type
#         """
#         # TODO: Implement child casting logic
#         raise NotImplementedError("Child casting not yet implemented")
#
#
# route_map = RouteMap(".", Api)
