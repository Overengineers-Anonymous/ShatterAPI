from typing import Callable, Protocol, overload
import functools
import inspect
from .utils import has_base


class FuncSignature:
    def __init__(self, args: dict[str, type], kwargs: dict[str, type], return_type: type):
        self.args = args
        self.kwargs = kwargs
        self.return_type = return_type

    @classmethod
    def from_func(cls, func: Callable):
        sig = inspect.signature(func)
        args = {}
        kwargs = {}
        for param in sig.parameters.values():
            if param.name == "self":
                continue
            if not param.annotation:
                raise TypeError(f"Parameter '{param.name}' in function '{func.__name__}' must have a type annotation")
            if param.default is not inspect.Parameter.empty:
                kwargs[param.name] = param.annotation
            else:
                args[param.name] = param.annotation
        return_type = sig.return_annotation
        return cls(args=args, kwargs=kwargs, return_type=return_type)

    def compatible_with(self, other):
        if not isinstance(other, FuncSignature):
            raise TypeError(f"Cannot compare FuncSignature with {type(other).__name__}")
        if len(self.args) != len(other.args):
            return False
        for name, type_ in self.args.items():
            if name not in other.args:
                return False
            if type_ is not other.args[name]:
                return False
        for name, type_ in other.kwargs.items():
            if name not in self.kwargs:
                return False
            if type_ is not self.kwargs[name]:
                return False
        if self.return_type is other.return_type or has_base(self.return_type, other.return_type):
            return True
        return False


class ApiWrapper:
    def __init__(self, func: Callable, path: str = ""):
        self.path = path
        self.func = func
        self.annotations = func.__annotations__
        self.unimplimented_funcs = [func]
        self._owner = None
        self.sig = FuncSignature.from_func(func)

    def extend_funcs(self, funcs: list[Callable]):
        for func in funcs:
            if not callable(func):
                raise TypeError(f"Expected a callable, got {type(func).__name__}")
            if func.__name__ != self.func_name:
                raise TypeError(f"Function '{func.__name__}' does not match the wrapper function name '{self.func_name}'")
            self.unimplimented_funcs.append(func)

    @property
    def func_name(self) -> str:
        return self.func.__name__

    def _wrapper(self, inner: Callable) -> Callable:
        @functools.wraps(inner)
        def wrapped(*args, **kwargs):
            print(f"Wrapped function: {self.func_name} at path: {self.path}")
            return inner(*args, **kwargs)

        return wrapped

    def wrap(self, cls: "type[ApiImplementation]"):
        func = getattr(cls, self.func_name)
        if not getattr(func, "_api_wrapper", False):
            wrapped = self._wrapper(func)
            wrapped._api_wrapper = True  # type: ignore
            setattr(cls, self.func_name, wrapped)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ApiWrapper):
            raise TypeError(f"Cannot compare ApiWrapper with {type(other).__name__}")
        if self.func_name == other.func_name and self.path == other.path:
            ...
        return False

    @property
    def owner(self) -> type:
        if self._owner is None:
            raise TypeError(f"ApiWrapper {self.func_name} has no owner")
        return self._owner

    @owner.setter
    def owner(self, value: type):
        if not isinstance(value, type):
            raise TypeError(f"Owner must be a type, got {type(value).__name__}")
        self._owner = value


class FunctionMap:
    def __init__(self):
        self.wrappers: dict[str, ApiWrapper] = {}
        self.path_mapping: dict[str, str] = {}
        self._owner: type | None = None

    def add_wrapper(self, wrapper: ApiWrapper):
        self.wrappers[wrapper.func_name] = wrapper
        self.path_mapping[wrapper.path] = wrapper.func_name

    def add_base(self, base_fm: "FunctionMap"):
        for wrapper in base_fm.wrappers.values():
            if wrapper.func_name not in self.wrappers:
                current_path_func = self.path_mapping.get(wrapper.path, )
                if current_path_func is not None and current_path_func != wrapper.func_name:
                    raise TypeError(
                        f"ApiDescriptor {self.owner.__name__} rebinds path '{wrapper.path}' to another method '{current_path_func}'"
                    )
                self.add_wrapper(wrapper)
            else:
                current_func_sig = self.wrappers[wrapper.func_name].sig
                if not current_func_sig.compatible_with(wrapper.sig):
                    raise TypeError(
                        f"Function '{wrapper.func_name}' in {self.owner.__name__} is not compatible with base function '{wrapper.func_name}' in {base_fm.owner.__name__}"
                    )
                self.wrappers[wrapper.func_name].extend_funcs(wrapper.unimplimented_funcs)
                current_wrapper = self.wrappers[wrapper.func_name]
                if wrapper.path != current_wrapper.path:
                    raise TypeError(
                        f"Method '{current_wrapper.func_name}' is already bound to path '{wrapper.path}' in ApiDescriptor {wrapper.owner.__name__}, but ApiDescriptor {current_wrapper.owner.__name__} attempts to rebind it to '{current_wrapper.path}'"
                    )



    @property
    def owner(self) -> type:
        if self._owner is None:
            raise TypeError("FunctionMap has no owner")
        return self._owner

    @owner.setter
    def owner(self, value: type):
        if not isinstance(value, type):
            raise TypeError(f"Owner must be a type, got {type(value).__name__}")
        for wrapper in self.wrappers.values():
            wrapper.owner = value
        self._owner = value

class BoundMapping:
    def __init__(self, obj, fm: FunctionMap):
        self.parent = obj
        self.fm = fm

    def req_api(self, path: str):
        return getattr(self.parent, self.fm.path_mapping[path])()


class Mapping:
    def __init__(self):
        self.func_map = FunctionMap()
        self.owner = None

    def route(self, path: str):
        def register_wrapper(func):
            wrapper = ApiWrapper(func, path)
            self.func_map.add_wrapper(wrapper)
            return func

        return register_wrapper
        # ...

    def extend(self, func: Callable):
        if "return" not in func.__annotations__:
            raise TypeError(f"Function '{func.__name__}' must have a return type annotation")
        rt_type = func.__annotations__["return"]
        if type(rt_type) is str:
            raise TypeError(f"Function '{func.__name__}' must have a return type annotation, quoted annotation is not allowed")
        if ApiDescriptor not in rt_type.__bases__:
            raise TypeError(f"Function '{func.__name__}' must return a valid ApiDescriptor. it returned: '{rt_type.__name__}'")
        return func

    def __set_name__(self, owner, name):
        if name != "mapping":
            raise TypeError(f"Mapping must be named 'mapping', got '{name}'")
        self.name = f"_{name}"
        self.func_map_name = f"_{name}_func_map"
        self.owner = owner
        self.func_map.owner = owner
        for cls in owner.__bases__:
            if ApiDescriptor in cls.__bases__:
                if fm := getattr(cls, self.func_map_name, None):
                    if not isinstance(fm, FunctionMap):
                        raise TypeError(f"Base class {cls.__name__} has invalid function map")
                    self.func_map.add_base(fm)
                else:
                    raise TypeError(f"Base class {cls.__name__} has no function map")
        setattr(owner, self.func_map_name, self.func_map)


    def bind(self, obj: "type[ApiImplementation]"):
        for name, wrapper in self.func_map.wrappers.items():
            if func := getattr(obj, name, None):
                if not callable(func):
                    raise TypeError(f"'{name}' in {obj.__class__.__name__} is not callable")
                if func in wrapper.unimplimented_funcs:
                    raise TypeError(f"Function '{name}' has no implementation")
                wrapper.wrap(obj)
        pass

    @overload
    def __get__(self, obj: None, objtype: type) -> "Mapping":
        ...

    @overload
    def __get__(self, obj: object, objtype:type) -> "BoundMapping":
        ...

    def __get__(self, obj: object | None, objtype: type | None = None) -> "BoundMapping | Mapping":
        if obj is None and objtype is not None:
            return self
        return BoundMapping(obj, self.func_map)
        # ...


class ApiImplementation:
    mapping: Mapping

    def __init_subclass__(cls) -> None:
        if cls.__base__:
            if not has_base(cls, ApiDescriptor):
                raise TypeError(f"{cls.__name__} must inherit from a class that subclasses ApiDescriptor")
            # for base in cls.__bases__:
            #     if ApiDescriptor in base.__bases__:
            cls.mapping.bind(cls)
        if getattr(cls.__init__, "_api_descr_init", False):
            # If the __init__ method is marked as _api_descr_init, it means this class is using __init__ from ApiDescriptor
            setattr(cls, "__init__", object.__init__)

class ApiDescriptor(Protocol):
    mapping: Mapping

    def __init_subclass__(cls):
        if ApiDescriptor in cls.__bases__:
            if cls.mapping.owner is not cls:
                raise TypeError(
                    f"ApiDescriptor {cls.__name__} must have their own mapping but it inherits it from {cls.mapping.owner.__name__}"
                )
            if Protocol not in cls.__bases__:
                raise TypeError(f"ApiDescriptor {cls.__name__} must inherit from Protocol")

            def __init__(self, *args, **kwargs):
                raise TypeError(f"ApiDescriptor {self.__class__.__name__} cannot be instantiated directly")
            __init__._api_descr_init = True  # type: ignore
            setattr(cls, "__init__", __init__)
        else:
            raise TypeError(f"ApiDescriptor {cls.__name__} must inherit from ApiDescriptor")


class RouteMap[T: "ApiDescriptor"]:
    def __init__(self, root: str, descriptor: type[T]):
        self.root = root

    def api_descriptor[TD: "ApiDescriptor"](self, root: str, descriptor: "type[TD]") -> "RouteMap[TD]":
        return RouteMap(self.root + root, descriptor)

    def api_implementation(self, root: str, implementation: "T"): ...

    def cast_to_child(self, path: str) -> "T": ...


#     def validate(self) -> None: ...
#
#     def make_app(self) -> FastAPI:
#         app = FastAPI()
#         return app


route_map = RouteMap(".", ApiDescriptor)
