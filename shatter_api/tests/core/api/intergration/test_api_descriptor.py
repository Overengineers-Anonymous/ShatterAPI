from shatter_api.core.api import Mapping
from shatter_api.core.api import ApiDescriptor
from typing import Protocol
import pytest


def test_invalid_inheritance():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(TypeError, match="ApiDescriptor TestApi2 must inherit from ApiDescriptor"):

        class TestApi2(TestApi):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self): ...

    with pytest.raises(TypeError, match="ApiDescriptor TestApi3 must inherit from ApiDescriptor"):

        class TestApi3(TestApi, Protocol):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self): ...


def test_invalid_inheritance_missing_protocol():
    with pytest.raises(TypeError, match="ApiDescriptor TestApi must inherit from Protocol"):

        class TestApi(ApiDescriptor):
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self): ...

    class TestApi2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(TypeError, match="ApiDescriptor TestApi3 must inherit from Protocol"):

        class TestApi3(TestApi2, ApiDescriptor):  # type: ignore
            mapping = Mapping()

            @mapping.route("/test")
            def test_method(self): ...


def test_error_on_inst():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(TypeError, match="ApiDescriptor TestApi cannot be instantiated directly"):
        TestApi()

    class TestApi2(ApiDescriptor, Protocol):
        def __init__(self): ...

        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(TypeError, match="ApiDescriptor TestApi2 cannot be instantiated directly"):
        TestApi2()

    class TestApi3(TestApi2, ApiDescriptor, Protocol):
        def __init__(self): ...

        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(TypeError, match="ApiDescriptor TestApi3 cannot be instantiated directly"):
        TestApi3()

def test_valid_inheritance():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    class TestApi2(TestApi, ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self): ...

    class TestApi3(TestApi2, ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test3")
        def test_method3(self): ...

def test_valid_multiple_inheritance():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    class TestApi2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self): ...

    class TestApi3(TestApi, TestApi2, ApiDescriptor, Protocol):
        mapping = Mapping()


def test_composition_invalid_class():
    class InvalidApi:
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(
        TypeError, match="Function 'invalid_api' must return a valid ApiDescriptor. it returned: 'InvalidApi'"
    ):
        class TestApi(ApiDescriptor, Protocol):
            mapping = Mapping()

            @mapping.extend
            def invalid_api(self) -> InvalidApi: ...

    class TestApi2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(
        TypeError, match="Function 'invalid_api' must have a return type annotation, quoted annotation is not allowed"
    ):

        class TestApi3(ApiDescriptor, Protocol):
            mapping = Mapping()

            @mapping.extend
            def invalid_api(self) -> "TestApi2": ...

    with pytest.raises(TypeError, match="Function 'invalid_api' must have a return type annotation"):

        class TestApi4(ApiDescriptor, Protocol):
            mapping = Mapping()

            @mapping.extend
            def invalid_api(self): ...

def test_valid_composition():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    class TestApi2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self): ...

    class TestApi3(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.extend
        def test_api(self) -> TestApi: ...

        @mapping.extend
        def test_api2(self) -> TestApi2: ...

def test_unique_mapper():
    class TestApi(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self): ...

    with pytest.raises(TypeError, match="ApiDescriptor TestApi2 must have their own mapping but it inherits it from TestApi"):
        class TestApi2(TestApi, ApiDescriptor, Protocol):
            ...


