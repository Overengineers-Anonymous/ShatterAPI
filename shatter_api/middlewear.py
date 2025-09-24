from typing import Any, Sequence, cast, Protocol, runtime_checkable
from .call_builder import CallCtx, CallDispatcher, CallDispatcherInterface
from .responses.responses import (
    InheritedResponses,
    middleware_response,
)
from .utils import ApiFuncSig
from .type_extraction import parse_generic


class Middleware(Protocol):
    def process(self, call_next: "CallNext[Any]", *args: Any, **kwargs: Any) -> middleware_response:
        """
        Process the request and return a response.
        This method should be overridden by subclasses to implement specific middleware logic.
        """
        ...

    @classmethod
    def placeholder(cls) -> "type[Middleware]":
        return cls

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
