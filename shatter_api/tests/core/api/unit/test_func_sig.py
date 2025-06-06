from fastapi.background import P
from shatter_api.core.api import FuncSignature
from shatter_api.tests import parametrise, Param


def test_from_func():
    def test_func(a: int, b: str = "default") -> bool:
        return True

    sig = FuncSignature.from_func(test_func)
    assert sig.args == {"a": int}
    assert sig.kwargs == {"b": str}
    assert sig.return_type is bool


def test_compatible_with_valid():
    def func_a(x: int, y: str = "default") -> bool:
        return True

    def func_b(x: int, y: str = "default") -> bool:
        return False

    sig_a = FuncSignature.from_func(func_a)
    sig_b = FuncSignature.from_func(func_b)

    assert sig_b.compatible_with(sig_a)

    def func_c(x: int, y: str = "default", c: str = "bleh") -> bool:
        return True

    sig_c = FuncSignature.from_func(func_c)
    assert sig_c.compatible_with(sig_a)
    assert sig_c.compatible_with(sig_b)

    class Base: ...

    class Derived(Base): ...

    def func_d(x: int, y: str = "default") -> Base:
        return Base()

    def func_e(x: int, y: str = "default") -> Derived:
        return Derived()

    sig_d = FuncSignature.from_func(func_d)
    sig_e = FuncSignature.from_func(func_e)
    assert sig_e.compatible_with(sig_d)


@parametrise(
    [
        Param(
            [
                FuncSignature(args={"a": int, "b": str}, kwargs={}, return_type=bool),
                FuncSignature(args={"a": int}, kwargs={}, return_type=bool),
            ],
            "missing_argument",
        ),
        Param(
            [
                FuncSignature(args={"a": int, "b": str}, kwargs={}, return_type=bool),
                FuncSignature(args={"a": int, "b": str, "c": str}, kwargs={}, return_type=bool),
            ],
            "extra_argument",
        ),
        Param(
            [
                FuncSignature(args={"a": int, "b": str}, kwargs={"c": str}, return_type=bool),
                FuncSignature(args={"a": int, "b": str}, kwargs={}, return_type=bool),
            ],
            "missing_keyword_argument",
        ),
        Param(
            [
                FuncSignature(args={"a": int, "b": str}, kwargs={"c": str}, return_type=bool),
                FuncSignature(args={"a": int, "b": str}, kwargs={"c": str}, return_type=str),
            ],
            "incompatible_return_type",
        ),
    ]
)
def test_compatible_with_invalid(sig_a, sig_b):
    assert not sig_b.compatible_with(sig_a)
