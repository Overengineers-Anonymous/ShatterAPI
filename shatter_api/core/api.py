"""
API Wrapper and Descriptor System

This module provides the core API framework for defining, wrapping, and executing
API endpoints with type safety and inheritance support.
"""

from typing import Any, Callable, Protocol, cast, overload
import functools

from pydantic import BaseModel, ValidationError

from .request import RequestBody, RequestCtx, RequestHeaders, RequestQueryParams
from .responses import BaseHeaders, Response, ResponseInfo, ValidationErrorResponse, get_response_info, middleware_response
from .utils import has_base, ApiFuncSig
from .middlewear import CallNext, Middleware, MiddlewareDispatcher
from .call_builder import CallDispatcher, CallCtx, CallDispatcherInterface


class Api(Protocol):
    mapping: "Mapping"

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "mapping"):
            raise TypeError(f"{cls.__name__} must have a 'mapping' attribute of type Mapping")
        cls.mapping.build_description(cls)
        return super().__init_subclass__()


class ApiEndpoint:
    """
    Represents a single API endpoint with a specific path and function signature.
    """

    def __init__(self, path: str, func: Callable, middlewares: list[Middleware]):
        self.path = path
        self.func_sig = ApiFuncSig.from_func(func)
        self.call_dispatcher = CallDispatcher(func)
        self._owner: type[Api] | None = None
        self.middlewares = self._expand_middleware(middlewares)

    def _expand_middleware(self, middlewares: list[Middleware]) -> list[Middleware]:
        """
        Expand the middleware list by including the expanded middleware of each item.
        """
        expanded = []
        for middleware in middlewares:
            if isinstance(middleware, Middleware):
                expanded.extend(middleware.expanded_middleware)
            else:
                raise TypeError(f"Middleware '{middleware.__class__}' is not an instance of Middleware")
        return self._dedupe_middleware(expanded)

    @staticmethod
    def _dedupe_middleware(middlewares: list[Middleware]) -> list[Middleware]:
        """
        Remove duplicate middleware from the list.
        """
        seen = set()
        deduped_middlewares = []
        for middleware in middlewares:
            if middleware not in seen:
                seen.add(middleware)
                deduped_middlewares.append(middleware)
        return deduped_middlewares

    @property
    def response_descr(self) -> list[ResponseInfo]:
        responses = get_response_info(self.func_sig.return_type, [])
        for middleware in self.middlewares[::-1]:
            responses = get_response_info(middleware.func_sig.return_type, responses)
        return responses

    @property
    def owner(self) -> type[Api]:
        if self._owner is None:
            raise RuntimeError("ApiEndpoint has no owner")
        return self._owner

    @property
    def valid(self) -> bool:
        """
        Check if the endpoint is valid, i.e., has a valid owner and function signature.
        """

        return True

    @owner.setter
    def owner(self, value: type[Api]):
        if not has_base(value, Api):
            raise TypeError(f"{value.__name__} must inherit from ApiDescriptor to set as owner")
        self._owner = value


class ApiCallDispatcher(CallDispatcherInterface):
    def __init__(self, func: Callable[..., middleware_response]):
        self.calldispatcher = CallDispatcher(func)

    def dispatch(self, ctx: CallCtx) -> middleware_response:
        """
        Dispatch the API call using the provided context.
        """
        if CallNext in ctx:
            ctx.remove_object(CallNext)

        return self.calldispatcher.dispatch(ctx)


class ApiExecutor:
    def __init__(self, api_endpoint: ApiEndpoint, obj: object):
        self.obj = obj
        self.api_endpoint = api_endpoint
        self.func = self._get_func(obj)
        self.call_dispatcher = self.build_middleware()

    @property
    def response_descr(self) -> list[ResponseInfo]:
        return self.api_endpoint.response_descr

    def _get_func(self, obj: object) -> Callable:
        """
        Get the function to be executed for this endpoint.
        """

        func = getattr(obj, self.api_endpoint.func_sig.name, None)
        if func is None or not callable(func):
            raise AttributeError(
                f"Function '{self.api_endpoint.func_sig.name}' not found in object '{obj.__class__.__name__}'"
            )
        if not self.api_endpoint.func_sig.compatible_with(ApiFuncSig.from_func(func)):
            raise TypeError(
                f"Function signature for '{self.api_endpoint.func_sig.name}' in '{obj.__class__.__name__}' is not compatible with endpoint '{self.api_endpoint.path}' defined in '{self.api_endpoint.owner.__name__}'"
            )
        return func

    def build_middleware(self) -> CallDispatcherInterface:
        """
        Build a list of middleware for the endpoint.
        """
        next_dispatcher = ApiCallDispatcher(self.func)
        for middleware in reversed(self.api_endpoint.middlewares):
            if not isinstance(middleware, Middleware):
                raise TypeError(f"Middleware '{middleware}' is not an instance of Middleware")
            next_dispatcher = MiddlewareDispatcher(middleware, next_dispatcher)
        return next_dispatcher

    def __call__(self, obj: object, req: RequestCtx) -> middleware_response:
        call_ctx = CallCtx(req)
        try:
            return self.call_dispatcher.dispatch(call_ctx)

        except ValidationError as e:
            return ValidationErrorResponse.from_validation_error(
                e, list(self.api_endpoint.func_sig.args.values()) + list(self.api_endpoint.func_sig.kwargs.values())
            )


class BoundApiDescriptor:
    def __init__(self, paths: dict[str, ApiExecutor], owner: object):
        self.paths = paths
        self.owner = owner

    def dispatch(self, path: str, req: RequestCtx) -> Response[BaseModel, int, BaseHeaders]:
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
            raise TypeError(f"{obj.__class__.__name__} must inherit from ApiDescriptor to bind API description")
        paths = {}
        for path, api_endpoint in self.paths.items():
            api_executor = ApiExecutor(api_endpoint, obj)
            paths[path] = api_executor
        bound_api_descr = BoundApiDescriptor(paths, obj)
        return bound_api_descr


class Mapping:
    API_DESCR_NAME = "__api_descr"
    API_BOUND_NAME = "__api_descr_bound"

    def __init__(self, subpath: str = "", middleware: list[Middleware] | None = None):
        self.middleware = middleware or []
        self.subpath = subpath
        self.routes: dict[str, ApiEndpoint] = {}
        self._owner: type[Api] | None = None

    def route(self, path: str, middleware: list[Middleware] | None = None) -> Callable:
        middleware = middleware or self.middleware

        def register(func: Callable) -> Callable:
            self.routes[path] = ApiEndpoint(path, func, self.middleware + middleware)
            return func

        return register

    def build_description(self, owner: type) -> ApiDescription:
        api_description = ApiDescription(owner)
        for base in owner.__mro__[::-1]:
            mapping = getattr(base, "mapping", None)
            if isinstance(mapping, Mapping):
                for path, api_endpoint in mapping.routes.items():
                    api_description.add_path(path, api_endpoint)
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
        for api_endpoint in self.routes.values():
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


class RouteMap[T: "Api"]:
    """
    Manages routing configuration for API descriptors.

    Provides a fluent interface for building API route hierarchies
    and binding implementations to specific paths.
    """

    def __init__(self, root: str, descriptor: type[T]):
        """
        Initialize a route map with root path and descriptor type.

        Args:
            root: Root path for this route map
            descriptor: ApiDescriptor type to manage
        """
        self.root = root
        self.api_descriptor = descriptor

    def add_descriptor[TD: "ApiDescriptor"](self, root: str, descriptor: "type[TD]") -> "RouteMap[TD]":
        """
        Add a child descriptor to this route map.

        Args:
            root: Root path for the child descriptor
            descriptor: Child ApiDescriptor type

        Returns:
            New RouteMap for the child descriptor
        """
        return RouteMap(self.root + root, descriptor)

    def api_implementation(self, root: str, implementation: "T"):
        """
        Bind an API implementation to a specific root path.

        Args:
            root: Root path for the implementation
            implementation: ApiImplementation instance
        """
        # TODO: Implement implementation binding logic
        pass

    def cast_to_child(self, path: str) -> "T":
        """
        Cast this route map to a child type at the specified path.

        Args:
            path: Path to cast to

        Returns:
            Casted instance of the child type
        """
        # TODO: Implement child casting logic
        raise NotImplementedError("Child casting not yet implemented")


route_map = RouteMap(".", Api)
