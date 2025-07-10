from typing import TYPE_CHECKING, Callable

from pydantic import ValidationError

from ..call_builder import CallCtx, CallDispatcher, CallDispatcherInterface
from ..middlewear import CallNext, Middleware, MiddlewareDispatcher
from ..request import RequestCtx
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

    def __init__(self, path: str, func: Callable, middlewares: list[Middleware]):
        self.path = path
        self.func_sig = ApiFuncSig.from_func(func)
        self.call_dispatcher = CallDispatcher(func)
        self._owner: "type[Api] | None" = None
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
                raise TypeError(
                    f"Middleware '{middleware.__class__}' is not an instance of Middleware"
                )
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
    def owner(self) -> "type[Api]":
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
    def owner(self, value: "type[Api]"):
        if not has_base(value, Api):
            raise TypeError(
                f"{value.__name__} must inherit from ApiDescriptor to set as owner"
            )
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
                raise TypeError(
                    f"Middleware '{middleware}' is not an instance of Middleware"
                )
            next_dispatcher = MiddlewareDispatcher(middleware, next_dispatcher)
        return next_dispatcher

    def __call__(self, obj: object, req: RequestCtx) -> middleware_response:
        call_ctx = CallCtx(req)
        try:
            return self.call_dispatcher.dispatch(call_ctx)

        except ValidationError as e:
            return ValidationErrorResponse.from_validation_error(
                e,
                list(self.api_endpoint.func_sig.args.values())
                + list(self.api_endpoint.func_sig.kwargs.values()),
            )
