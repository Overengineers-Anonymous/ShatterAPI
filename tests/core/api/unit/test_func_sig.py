from fastapi.background import P
from pydantic import BaseModel
from shatter_api.core.api import ApiFuncSig
from shatter_api.tests import parametrise, Param


def test_from_func():
    def test_func(a: int, b: str = "default") -> bool:
        return True

    sig = ApiFuncSig.from_func(test_func)
    assert sig.args == {"a": int}
    assert sig.kwargs == {"b": str}
    assert sig.return_type is bool


def test_compatible_with_valid():
    def func_a(x: int, y: str = "default") -> str:
        return True

    sig_a = ApiFuncSig.from_func(func_a)

    def func_a(x: int, y: str = "default") -> str:
        return False

    sig_b = ApiFuncSig.from_func(func_a)

    assert sig_b.compatible_with(sig_a)

    def func_a(x: int, y: str = "default", c: str = "bleh") -> str:
        return True

    sig_c = ApiFuncSig.from_func(func_a)
    assert sig_c.compatible_with(sig_a)
    assert sig_c.compatible_with(sig_b)

    class Base(BaseModel): ...

    class Derived(Base): ...

    def func_d(x: int, y: str = "default") -> Base:
        return Base()

    sig_d = ApiFuncSig.from_func(func_d)

    def func_d(x: int, y: str = "default") -> Derived:
        return Derived()

    sig_e = ApiFuncSig.from_func(func_d)
    assert not sig_e.compatible_with(sig_d)


@parametrise(
    [
        Param(
            [
                ApiFuncSig(args={"a": int, "b": str}, kwargs={}, return_type=bool, name="test"),
                ApiFuncSig(args={"a": int}, kwargs={}, return_type=bool, name="test"),
            ],
            "missing_argument",
        ),
        Param(
            [
                ApiFuncSig(args={"a": int, "b": str}, kwargs={}, return_type=bool, name="test"),
                ApiFuncSig(args={"a": int, "b": str, "c": str}, kwargs={}, return_type=bool, name="test"),
            ],
            "extra_argument",
        ),
        Param(
            [
                ApiFuncSig(args={"a": int, "b": str}, kwargs={"c": str}, return_type=bool, name="test"),
                ApiFuncSig(args={"a": int, "b": str}, kwargs={}, return_type=bool, name="test"),
            ],
            "missing_keyword_argument",
        ),
        Param(
            [
                ApiFuncSig(args={"a": int, "b": str}, kwargs={"c": str}, return_type=bool, name="test"),
                ApiFuncSig(args={"a": int, "b": str}, kwargs={"c": str}, return_type=str, name="test"),
            ],
            "incompatible_return_type",
        ),
        Param(
            [
                ApiFuncSig(args={"a": int, "b": str}, kwargs={"c": str}, return_type=bool, name="test"),
                ApiFuncSig(args={"a": int, "b": str}, kwargs={"c": str}, return_type=bool, name="test1"),
            ],
            "incompatible_return_type",
        ),
    ]
)
def test_compatible_with_invalid(sig_a, sig_b):
    assert not sig_b.compatible_with(sig_a)
