from typing import TYPE_CHECKING, Protocol

from ..utils import has_base
from ..request.request import RequestCtx

if TYPE_CHECKING:
    from .mapping import Mapping

class Api(Protocol):
    mapping: "Mapping"

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "mapping"):
            raise TypeError(f"{cls.__name__} must have a 'mapping' attribute of type Mapping")
        cls.mapping.build_description(cls)
        return super().__init_subclass__()


class RouteMap:
    def __init__(self):
        self.paths: dict[str, Api] = {}

    def add_api(self, api: Api):
        """
        Adds an API descriptor to the route map.
        """
        if not has_base(api.__class__, Api):
            raise TypeError(f"{api.__class__.__name__} must implement Api protocol")
        if not api.mapping.is_implimented:
            raise RuntimeError(f"API '{api.__class__.__name__}' is not fully implemented")
        
        for path in api.mapping.methods.keys():
            self.paths[path] = api

    def dispatch(self, ctx: RequestCtx):
        return self.paths[ctx.path].mapping.dispatch(ctx)

route_map = RouteMap()
