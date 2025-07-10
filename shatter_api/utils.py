import inspect
from typing import Any, Callable, Union, get_args, get_origin

from pydantic import BaseModel

from .responses.responses import InheritedResponses, Response


def has_base(cls: type, base_cls: type):
    if base_cls in cls.__mro__:
        return True
    return False


class ApiFuncSig:
    def __init__(
        self,
        args: dict[str, type],
        kwargs: dict[str, type],
        return_type: type,
        name: str,
    ):
        self.args = args
        self.kwargs = kwargs
        self.defaults: dict[str, Any] = {}
        self.return_type = return_type
        self.name = name

    @classmethod
    def from_func(cls, func: Callable):
        sig = inspect.signature(func)
        args = {}
        kwargs = {}
        for param in sig.parameters.values():
            if param.name == "self":
                continue
            if not param.annotation:
                raise TypeError(
                    f"Parameter '{param.name}' in function '{func.__name__}' must have a type annotation"
                )
            if param.default is not inspect.Parameter.empty:
                kwargs[param.name] = param.annotation
            else:
                args[param.name] = param.annotation
        return_type = sig.return_annotation
        func_sig = cls(
            args=args, kwargs=kwargs, return_type=return_type, name=func.__name__
        )
        func_sig.validate()
        return func_sig

    @staticmethod
    def _check_union(self_union: set[type], other_union: set[type]):
        if self_union.intersection(other_union) == self_union:
            return True

    def _check_return_type(self, return_type: type):
        if self.return_type is return_type:
            return True

        if get_origin(self.return_type) is Union:
            self_union_args = get_args(self.return_type)
        else:
            self_union_args = (self.return_type,)
        if get_origin(return_type) is Union:
            union_args = get_args(return_type)
        else:
            union_args = (return_type,)
        return self._check_union(set(self_union_args), set(union_args))

    def _check_args(self, args: dict[str, type]):
        if len(self.args) != len(args):
            return False
        for name, type_ in self.args.items():
            if name not in args:
                return False
            if type_ is not args[name]:
                return False
        return True

    def _check_kwargs(self, kwargs: dict[str, type]):
        for name, type_ in self.kwargs.items():
            if name not in kwargs:
                return False
            if type_ is not kwargs[name]:
                return False
        return True

    def compatible_with(self, other):
        if not isinstance(other, ApiFuncSig):
            raise TypeError(f"Cannot compare FuncSignature with {type(other).__name__}")
        if not self._check_args(other.args):
            return False
        if not self._check_kwargs(other.kwargs):
            return False
        if not self._check_return_type(other.return_type):
            return False
        if self.name != other.name:
            return False
        return True

    def validate(self):
        if get_origin(self.return_type) is Union:
            union_args = get_args(self.return_type)
        else:
            union_args = (self.return_type,)
        for type_ in union_args:
            origin = get_origin(type_) or type_
            if origin and issubclass(origin, Response):
                continue
            elif origin and issubclass(origin, InheritedResponses):
                continue
            elif type_ is str:
                continue
            elif issubclass(type_, BaseModel):
                continue
            if type_ is inspect._empty:
                raise TypeError(
                    f"Return type in function '{self.name}' is not annotated."
                )
            raise TypeError(
                f"Return type '{type_.__name__}' in function '{self.name}' must be a subclass of Response, str, or BaseModel"
            )
