"""
API Wrapper and Descriptor System

This module provides the core API framework for defining, wrapping, and executing
API endpoints with type safety and inheritance support.
"""

from typing import Any, Callable, Protocol, cast, overload
import functools

from pydantic import BaseModel, ValidationError

from .request import RequestBody, RequestCtx, RequestHeaders, RequestQueryParams
from .responses import BaseHeaders, Response, ResponseInfo, ValidationErrorResponse, get_response_info
from .utils import has_base, ApiFuncSig
from .middlewear import Middleware

class ApiDescriptor(Protocol):
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

    def __init__(self, path: str, func: Callable, middleware: list[Middleware] | None = None):
        self.path = path
        self.func_sig = ApiFuncSig.from_func(func)
        self._owner: type[ApiDescriptor] | None = None
        self.func = func
        self.middleware = self.build_middleware(middleware)

    @staticmethod
    def build_middleware(middleware: list[Middleware] | None) -> list[Middleware]:
        """
        Build a list of middleware for the endpoint.
        """
        if middleware is None:
            return []
        if not isinstance(middleware, list):
            raise TypeError("Middleware must be a list of Middleware instances")
        return middleware

    @property
    def response_descr(self) -> list[ResponseInfo]:
        return get_response_info(self.func_sig.return_type)

    @property
    def owner(self) -> type[ApiDescriptor]:
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
    def owner(self, value: type[ApiDescriptor]):
        if not has_base(value, ApiDescriptor):
            raise TypeError(f"{value.__name__} must inherit from ApiDescriptor to set as owner")
        self._owner = value

    def _get_func_args(self, func_sig: ApiFuncSig, req: RequestCtx) -> list[Any]:
        func_args = func_sig.args
        args = []
        for arg, _type in func_args.items():
            if issubclass(_type, RequestBody):
                args.append(_type.model_validate(req.body))
            elif issubclass(_type, RequestCtx):
                args.append(req)
            elif issubclass(_type, RequestHeaders):
                args.append(_type.model_validate(req.headers))
            elif issubclass(_type, RequestQueryParams):
                args.append(_type.model_validate(req.query_params))
            else:
                raise TypeError(f"Unsupported type '{_type}' for argument '{arg}' in function '{func_sig.name}'")
        return args

    def __call__(self, obj: object, req: RequestCtx) -> Response[BaseModel, int, BaseHeaders]:
        func = getattr(obj, self.func_sig.name, None)
        if func is None or not callable(func):
            raise AttributeError(f"Function '{self.func_sig.name}' not found in object '{obj.__class__.__name__}'")
        if not self.func_sig.compatible_with(ApiFuncSig.from_func(func)):
            raise TypeError(
                f"Function signature for '{self.func_sig.name}' in '{obj.__class__.__name__}' is not compatible with endpoint '{self.path}' defined in '{self.owner.__name__}'"
            )
        try:
            args = self._get_func_args(self.func_sig, req)
        except ValidationError as e:
            return ValidationErrorResponse.from_validation_error(e, list(self.func_sig.args.values())+list(self.func_sig.kwargs.values()))
        return cast(Response[BaseModel, int, BaseHeaders], func(*args))


class ApiDescription:
    def __init__(self, owner: type[ApiDescriptor]):
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

    def get_api_endpoint(self, path: str) -> ApiEndpoint:
        if path not in self.paths:
            raise KeyError(f"Path '{path}' not found in API description")
        return self.paths[path]


class BoundApiDescriptor:
    def __init__(self, api_description: ApiDescription, owner: object):
        self.api_description = api_description
        self.owner = owner

    @property
    def paths(self) -> dict[str, ApiEndpoint]:
        return self.api_description.paths

    def dispatch(self, path: str, req: RequestCtx) -> Response[BaseModel, int, BaseHeaders]:
        endpoint = self.api_description.get_api_endpoint(path)
        return endpoint(self.owner, req)


class Mapping:
    API_DESCR_NAME = "__api_descr"
    API_BOUND_NAME = "__api_descr_bound"

    def __init__(self, subpath: str = ""):
        self.subpath = subpath
        self.routes: dict[str, ApiEndpoint] = {}
        self._owner: type[ApiDescriptor] | None = None

    def route(self, path: str, middleware: list[Middleware] | None = None) -> Callable:
        def register(func: Callable) -> Callable:
            self.routes[path] = ApiEndpoint(path, func, middleware)
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
    def owner(self) -> type[ApiDescriptor]:
        if self._owner is None:
            raise RuntimeError("Mapping has not been initialized properly")
        return self._owner

    def __set_name__(self, owner, name):
        self._owner = owner
        if not has_base(owner, ApiDescriptor):
            raise TypeError(f"{owner.__name__} must inherit from ApiDescriptor to use Mapping")
        if name != "mapping":
            raise TypeError(f"Mapping must be named 'mapping', not '{name}'")
        for api_endpoint in self.routes.values():
            api_endpoint.owner = owner

    @overload
    def __get__(self, obj: None, objtype: type) -> "Mapping": ...

    @overload
    def __get__(self, obj: ApiDescriptor, objtype: type) -> BoundApiDescriptor: ...

    def __get__(self, obj: ApiDescriptor | None, objtype: type | None = None) -> "BoundApiDescriptor | Mapping":
        if obj is None and objtype is not None:
            return self

        if obj is None:
            raise TypeError("Mapping cannot be accessed without an instance or type")

        if not has_base(obj.__class__, ApiDescriptor):
            raise TypeError(f"{obj.__class__.__name__} must inherit from ApiDescriptor to use Mapping")

        api_description: ApiDescription | None = getattr(obj, self.API_DESCR_NAME, None)
        if api_description is None:
            raise RuntimeError(f"{obj.__class__.__name__} has not built its API description yet")
        bound_api_descr: BoundApiDescriptor | None = getattr(obj, self.API_BOUND_NAME, None)
        if bound_api_descr is None:
            bound_api_descr = BoundApiDescriptor(api_description, obj)
            setattr(obj, self.API_BOUND_NAME, bound_api_descr)
        return bound_api_descr


class RouteMap[T: "ApiDescriptor"]:
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


route_map = RouteMap(".", ApiDescriptor)
