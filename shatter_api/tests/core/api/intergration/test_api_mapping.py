from shatter_api.core.api import Mapping, ApiDescriptor
from typing import Protocol
import pytest


def test_api_descr_overwrite():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    class TestApi2(TestApi, ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    class TestApi3(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    class TestApi4(TestApi3, ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self): ...


def test_api_descr_path_rebind_error():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(TypeError, match="ApiDescriptor TestApi2 rebinds path '/test' to another method 'test_method2'"):

        class TestApi2(TestApi, ApiDescriptor, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method2(self): ...


def test_api_descr_function_rebind_error():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(
        TypeError,
        match="Method 'test_method' is already bound to path '/test' in ApiDescriptor TestApi, but ApiDescriptor TestApi2 attempts to rebind it to '/test2'",
    ):

        class TestApi2(TestApi, ApiDescriptor, Protocol):
            mapping = Mapping()

            @mapping.route("/test2")
            def test_method(self): ...  # Rebinding the same function name should raise an error


def test_invalid_overwrite():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> int: ...

    with pytest.raises(
        TypeError,
        match="Function 'test_method' in TestApi2 is not compatible with base function 'test_method' in TestApi",
    ):

        class TestApi2(TestApi, ApiDescriptor, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self, a: int) -> int:  # This should not raise an error as it inherits correctly
                ...

def test_incomparable_overwrite():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self, a: float) -> int: ...

    with pytest.raises(
        TypeError,
        match="Function 'test_method' in TestApi2 is not compatible with base function 'test_method' in TestApi",
    ):

        class TestApi2(TestApi, ApiDescriptor, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self, a: int) -> int:  # This should not raise an error as it inherits correctly
                ...


def test_ambiguous_overwrite():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self, a: int) -> int: ...

    class TestApi2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self, a: str) -> int: ...

    with pytest.raises(
        TypeError,
        match="Function 'test_method' in TestAp3 is not compatible with base function 'test_method' in TestApi",
    ):

        class TestAp3(TestApi, TestApi2, ApiDescriptor, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self, a: int): ...  # This should raise an error due to ambiguity

