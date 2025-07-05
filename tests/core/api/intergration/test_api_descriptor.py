from shatter_api.core.api import Mapping
from shatter_api.core.api import ApiDescriptor
from typing import Protocol
import pytest

def test_valid_structure_base():
    class Test(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

def test_valid_structure_inheritance():
    class Test(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    class Test2(Test, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self) -> str: ...

    class Test3(Test2, Protocol):
        mapping = Mapping()

        @mapping.route("/test3")
        def test_method3(self) -> str: ...

def test_valid_structure_multiple_inheritance():
    class Test(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    class Test2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self) -> str: ...

    class Test3(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test3")
        def test_method3(self) -> str: ...

    class Test4(Test, Test2, Test3, Protocol):
        mapping = Mapping()

def test_valid_structure_reinheritance():
    class Test(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    class Test2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self) -> str: ...

    class Test3(Test, Test2, ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test3")
        def test_method3(self) -> str: ...


def test_missing_mapping():
    with pytest.raises(TypeError, match="Test must have a 'mapping' attribute of type Mapping"):
        class Test(ApiDescriptor, Protocol):
            def test_method(self) -> str: ...

    class Test2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test2")
        def test_method2(self) -> str: ...

    class Test3(Test2, Protocol):
        def test_method3(self) -> str: ...

    class Test4(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test4")
        def test_method4(self) -> str: ...

    class Test5(Test2, Test4, Protocol):
        def test_method5(self) -> str: ...

def test_overwrite_via_multiple_inheritance():
    class Test(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    class Test2(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...
    class Test3(Test, Test2):
        def test_method(self) -> str: ...


def test_overwrite_via_looped_inheritance():
    class Test(ApiDescriptor, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...

    class Test2(Test, Protocol):
        mapping = Mapping()


    class Test3(Test, Protocol):
        mapping = Mapping()

    class Test4(Test2, Test3, Protocol):
        mapping = Mapping()

        @mapping.route("/test")
        def test_method(self) -> str: ...
