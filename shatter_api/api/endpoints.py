from typing import TYPE_CHECKING, Callable, Sequence, cast
from urllib import response

from pydantic import ValidationError

from ..call_builder import CallCtx, CallDispatcher, CallDispatcherInterface
from ..middlewear import CallNext, Middleware, MiddlewareDispatcher, PlaceholderMiddleware
from ..request.request import ReqType, RequestCtx
from ..responses import (
    ResponseInfo,
    ValidationErrorResponse,
    get_response_info,
    middleware_response,
)
from ..utils import ApiFuncSig, has_base

from .api import Api


class ApiEndpoint:
    """
    Represents a single API endpoint with a specific path and function signature.
    """

    def __init__(
        self,
        path: str,
        func: Callable,
        req_type: ReqType,
        middlewares: list[Middleware | type[PlaceholderMiddleware]],
    ):
        self.path = path
        self.req_type = req_type
        self.func_sig = ApiFuncSig.from_func(func)
        self.call_dispatcher = CallDispatcher(func)
        self._owner: "type[Api] | None" = None
        self.middlewares = self._remove_placeholder_middleware(middlewares)
        self.placeholder_middleware = self._expand_middleware(middlewares)

    def _remove_placeholder_middleware[T: Middleware | type[PlaceholderMiddleware]](
        self, middlewares: Sequence[T]
    ) -> list[Middleware]:
        """
        Remove placeholder middleware from the list.
        """
        trimmed: list[Middleware] = []
        for middleware in middlewares:
            if isinstance(middleware, Middleware):
                trimmed.append(middleware)
        return self._expand_middleware(trimmed)

    def _expand_middleware[T: Middleware | type[PlaceholderMiddleware]](self, middlewares: Sequence[T]) -> list[T]:
        """
        Expand the middleware list by including the expanded middleware of each item.
        """
        expanded: list[T] = []
        for middleware in middlewares:
            if isinstance(middleware, Middleware):
                expanded.extend(cast(list[T], middleware.expanded_middleware))
            elif has_base(middleware, PlaceholderMiddleware):
                expanded.extend(cast(list[T], middleware.expanded_middleware()))
            else:
                raise TypeError(f"Middleware '{middleware}' is not an instance of Middleware")
        return self._dedupe_middleware(expanded)

    @staticmethod
    def _dedupe_middleware[T: Middleware | type[PlaceholderMiddleware]](middlewares: Sequence[T]) -> list[T]:
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

    def _get_response_info(self, middlewares: Sequence[Middleware | type[PlaceholderMiddleware]]) -> set[ResponseInfo]:
        responses = get_response_info(self.func_sig.return_type, [])
        for middleware in middlewares[::-1]:
            responses = get_response_info(middleware.func_sig.return_type, responses)
        return set(responses)

    @property
    def response_descr(self) -> set[ResponseInfo]:
        return self._get_response_info(self.middlewares)

    @property
    def is_implimented(self) -> bool:
        response_info = self._get_response_info(self.middlewares)
        desired_response_info = self._get_response_info(self.placeholder_middleware)
        return response_info == desired_response_info

    @property
    def owner(self) -> "type[Api]":
        if self._owner is None:
            raise RuntimeError("ApiEndpoint has no owner")
        return self._owner

    @owner.setter
    def owner(self, value: "type[Api]"):
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
    def is_implimented(self) -> bool:
        """
        Check if the API endpoint is implemented.
        An endpoint is considered implemented if it has a valid function signature and is not a placeholder.
        """
        return self.api_endpoint.is_implimented

    @property
    def response_descr(self) -> set[ResponseInfo]:
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
                e,
                list(self.api_endpoint.func_sig.args.values()) + list(self.api_endpoint.func_sig.kwargs.values()),
            )
