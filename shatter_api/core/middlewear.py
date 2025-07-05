from typing import Callable
from pydantic import BaseModel
from .responses import Response, BaseHeaders
from .request import RequestCtx


class Middleware:
    def __init__(self):
        pass

class CallNext:
    def __init__(self, requestctx: RequestCtx, discpather: Callable):
        self.requestctx = requestctx
        self.discpather = discpather

    def __call__(self) -> Response[BaseModel, int, BaseHeaders]:
        # Placeholder for the actual call next logic
        return self.discpather(self.requestctx)
