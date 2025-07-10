from shatter_api.core.api import Mapping, Api
from typing import Protocol
import pytest


def test_api_descr_overwrite():
    class TestApi(Api, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    class TestApi2(TestApi, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    class TestApi3(Api, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    class TestApi4(TestApi3, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self) -> str: ...


def test_api_descr_path_rebind_error():
    class TestApi(Api, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    with pytest.raises(TypeError, match="ApiDescriptor 'TestApi2' rebinds path '/test' to another method 'test_method2'"):

        class TestApi2(TestApi, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method2(self) -> str: ...


def test_api_descr_function_rebind_error():
    class TestApi(Api, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    with pytest.raises(
        TypeError,
        match="Method 'test_method' is already bound to path '/test' in ApiDescriptor 'TestApi'",
    ):

        class TestApi2(TestApi, Protocol):
            mapping = Mapping()

            @mapping.route("/test2")
            def test_method(self) -> str: ...  # Rebinding the same function name should raise an error


def test_invalid_overwrite():
    class TestApi(Api, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    with pytest.raises(
        TypeError,
        match="Function 'test_method' in 'TestApi2' is not compatible with base function in 'TestApi'",
    ):

        class TestApi2(TestApi, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self, a: int) -> str:  # This should not raise an error as it inherits correctly
                ...


def test_incomparable_overwrite():
    class TestApi(Api, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self, a: float) -> str: ...

    with pytest.raises(
        TypeError,
        match="Function 'test_method' in 'TestApi2' is not compatible with base function in 'TestApi'",
    ):

        class TestApi2(TestApi, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self, a: int) -> str:  # This should not raise an error as it inherits correctly
                ...


def test_ambiguous_overwrite():
    class TestApi(Api, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self, a: int) -> str: ...

    class TestApi2(Api, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self, a: str) -> str: ...

    with pytest.raises(
        TypeError,
        match="Function 'test_method' in 'TestApi' is not compatible with base function in 'TestApi2'",
    ):

        class TestAp3(TestApi, TestApi2, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self, a: int) -> str:  # This should raise an error due to ambiguity
                ...
