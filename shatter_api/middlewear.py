from typing import Any, Sequence, cast

from fastapi.background import P

from test2 import Protocol

from .call_builder import CallCtx, CallDispatcher, CallDispatcherInterface
from .responses.responses import (
    InheritedResponses,
    middleware_response,
)
from .utils import ApiFuncSig
from .type_extraction import parse_generic


class Middleware():
    middleware = None

    def __init__(self):
        self.call_dispatcher = CallDispatcher(self.process)
        self.func_sig = ApiFuncSig.from_func(self.process)

    def process(self, call_next: "CallNext[Any]", *args: Any, **kwargs: Any) -> middleware_response:
        """
        Process the request and return a response.
        This method should be overridden by subclasses to implement specific middleware logic.
        """
        raise NotImplementedError("Middleware must implement the process method.")

    def __call__(self, call_ctx: CallCtx) -> middleware_response:
        """
        Process the request and return a response.
        If `next` is a callable, it should be called to continue the middleware chain.
        """
        return self.call_dispatcher.dispatch(call_ctx)

    @property
    def expanded_middleware(self) -> "list[Middleware]":
        combined = self.middleware or []
        combined.append(self)
        return combined

class PlaceholderMiddleware(Protocol):
    """
    A placeholder middleware that does nothing.
    This can be used as a default middleware in cases where no specific processing is needed.
    """
    middleware: "list[type[PlaceholderMiddleware]] | None" = None
    func_sig: ApiFuncSig

    def __init__(self):
        if self.__class__ is PlaceholderMiddleware:
            raise TypeError("PlaceholderMiddleware cannot be instantiated directly.")
        self.func_sig = ApiFuncSig.from_func(self.process)


    def process(self, call_next: "CallNext[Any]", *args: Any, **kwargs: Any) -> middleware_response:
        """
        Simply calls the next middleware or endpoint without any additional processing.
        """
        ...

    @classmethod
    def expanded_middleware(cls) -> "Sequence[type[PlaceholderMiddleware]]":
        combined = cls.middleware or []
        combined.append(cls)
        return combined

class CallNext[T: Any = None]:
    def __init__(self, call_ctx: CallCtx, current_middleware: Middleware, dispatcher: CallDispatcherInterface):
        self.ctx = call_ctx
        self.current_middleware = current_middleware
        self.dispatcher = dispatcher
        self.specific_type = self.get_specific_type(current_middleware.func_sig)

    def get_specific_type(self, func_sig: ApiFuncSig) -> type | None:
        call_next_sig = func_sig.args.get("call_next", None)
        if call_next_sig:
            specific_type = parse_generic(call_next_sig, CallNext)
            if specific_type is not None:
                return specific_type[0]
            return None

    def __call__(self, provided: T=None) -> InheritedResponses:
        # Placeholder for the actual call next logic
        if provided is not None:
            if self.specific_type:
                self.ctx.set_object(self.specific_type, provided)
            else:
                self.ctx.set_object(provided.__class__, provided)
        return cast(InheritedResponses, self.dispatcher.dispatch(self.ctx))


class MiddlewareDispatcher(CallDispatcherInterface):
    def __init__(self, middleware: Middleware, dispatcher: CallDispatcherInterface):
        self.middleware = middleware
        self.dispatcher = dispatcher

    def dispatch(self, ctx: CallCtx) -> middleware_response:
        """
        Execute the middleware and return the response.
        """
        next_ = CallNext(ctx, self.middleware, self.dispatcher)
        call_next_sig = self.middleware.func_sig.args.get("call_next", None)
        if call_next_sig:
            ctx.set_object(call_next_sig, next_)
        return self.middleware.call_dispatcher.dispatch(ctx)
