from typing import Callable, Protocol

from .request import RequestBody, RequestCtx, RequestHeaders, RequestQueryParams
from .responses.responses import middleware_response
from .utils import ApiFuncSig


class CallCtx:
    def __init__(self, ctx: RequestCtx):
        self.object_mapping: dict[type, object] = {RequestCtx: ctx}
        self.reqctx = ctx
        self.subclass_handlers = {
            RequestBody: self.load_request_body,
            RequestHeaders: self.load_request_headers,
            RequestQueryParams: self.load_request_query_params,
        }

    def load_request_body[T: RequestBody](self, obj_type: type[T]) -> T:
        return obj_type.model_validate(self.reqctx.body)

    def load_request_headers[T: RequestHeaders](self, obj_type: type[T]) -> T:
        return obj_type.model_validate(self.reqctx.headers)

    def load_request_query_params[T: RequestHeaders](self, obj_type: type[T]) -> T:
        return obj_type.model_validate(self.reqctx.query_params)

    def __contains__(self, obj_type: type) -> bool:
        """
        Checks if an object of the specified type exists in the context.
        """
        return obj_type in self.object_mapping

    def get_object(self, obj_type: type) -> object:
        """
        Retrieves an object of the specified type from the context.
        If the object does not exist, it raises a KeyError.
        """
        if obj_type not in self.object_mapping:
            for subclass, handler in self.subclass_handlers.items():
                if issubclass(obj_type, subclass):
                    inst = handler(obj_type)
                    self.object_mapping[obj_type] = inst
                    return inst
            raise KeyError(f"Object of type {obj_type} not found in context.")
        return self.object_mapping[obj_type]

    def remove_object(self, obj_type: type) -> None:
        """
        Removes an object of the specified type from the context.
        If the object does not exist, it raises a KeyError.
        """
        if obj_type not in self.object_mapping:
            raise KeyError(f"Object of type {obj_type} not found in context.")
        del self.object_mapping[obj_type]

    def set_object(self, obj_type: type, obj: object) -> None:
        """
        Sets an object of the specified type in the context.
        If an object of that type already exists, it raises a ValueError.
        """
        self.object_mapping[obj_type] = obj


class CallDispatcherInterface(Protocol):
    def dispatch(self, ctx: CallCtx) -> middleware_response: ...


class CallDispatcher(CallDispatcherInterface):
    def __init__(self, func: Callable[..., middleware_response]):
        self.func = func
        self.func_sig = ApiFuncSig.from_func(func)

    def dispatch(self, ctx: CallCtx) -> middleware_response:
        args = []
        for _type in self.func_sig.args.values():
            args.append(ctx.get_object(_type))

        return self.func(*args)
