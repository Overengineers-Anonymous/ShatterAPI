from typing import Any, cast

from .call_builder import CallCtx, CallDispatcher, CallDispatcherInterface
from .responses.responses import (
    InheritedResponses,
    middleware_response,
)
from .utils import ApiFuncSig


class CallNext:
    def __init__(self, call_ctx: CallCtx, dispatcher: CallDispatcherInterface):
        self.ctx = call_ctx
        self.dispatcher = dispatcher

    def __call__(self, *provides) -> InheritedResponses:
        # Placeholder for the actual call next logic
        for provide in provides:
            self.ctx.set_object(provide.__class__, provide)
        return cast(InheritedResponses, self.dispatcher.dispatch(self.ctx))


class Middleware:
    middleware = None

    def __init__(self):
        self.call_dispatcher = CallDispatcher(self.process)
        self.func_sig = ApiFuncSig.from_func(self.process)

    def process(self, *args: Any, **kwargs: Any) -> middleware_response:
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


class MiddlewareDispatcher(CallDispatcherInterface):
    def __init__(self, middleware: Middleware, dispatcher: CallDispatcherInterface):
        self.middleware = middleware
        self.dispatcher = dispatcher

    def dispatch(self, ctx: CallCtx) -> middleware_response:
        """
        Execute the middleware and return the response.
        """
        next_ = CallNext(ctx, self.dispatcher)
        ctx.set_object(CallNext, next_)
        return self.middleware.call_dispatcher.dispatch(ctx)
