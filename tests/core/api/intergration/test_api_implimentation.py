from shatter_api.core.api import Mapping
from shatter_api.core.api import ApiDescriptor
from typing import Protocol
import pytest

#
# def test_valid_structure():
#     class Test(ApiDescriptor, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test")
#         def test_method(self): ...
#
#     class Test2(Test, ApiImplementation):
#         def test_method(self): ...
#
#     class Test3(ApiImplementation, Test):
#         def test_method(self): ...
#
#     test2 = Test2()
#     test3 = Test3()
#
#
# def test_valid_structure_inheritance():
#     class Test(ApiDescriptor, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test")
#         def test_method(self): ...
#
#     class Test2(Test, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test2")
#         def test_method2(self): ...
#
#     class Test3(Test2, ApiImplementation):
#         def test_method(self): ...
#         def test_method2(self): ...
#
#     class Test4(ApiImplementation, Test2):
#         def test_method(self): ...
#         def test_method2(self): ...
#
#     test3 = Test3()
#     test4 = Test4()
#
# def test_valid_structure_multiple_inheritance_instant():
#     class Test(ApiDescriptor, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test")
#         def test_method(self): ...
#
#     class Test2(ApiDescriptor, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test2")
#         def test_method2(self): ...
#
#     class Test3(ApiDescriptor, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test3")
#         def test_method3(self): ...
#
#     class Test4(Test, Test2, Test3, Protocol):
#         mapping = Mapping()
#
#     class Test5(Test, ApiImplementation):
#         def test_method(self): ...
#
#     class Test6(Test2, ApiImplementation):
#         def test_method2(self): ...
#
#     class Test7(Test3, ApiImplementation):
#         def test_method3(self): ...
#
#     class Test8(Test5, Test6, Test7, Test4):
#         ...
#
#     test8 = Test8()
#     test8.test_method()
#     test5 = Test5()
#     test5.test_method()
#
# def test_valid_structure_multiple_inheritance_delayed():
#     class Test(ApiDescriptor, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test")
#         def test_method(self): ...
#
#     class Test2(ApiDescriptor, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test2")
#         def test_method2(self): ...
#
#     class Test3(ApiDescriptor, Protocol):
#         mapping = Mapping()
#
#         @mapping.route("/test3")
#         def test_method3(self): ...
#
#     class Test4(Test, Test2, Test3, Protocol):
#         mapping = Mapping()
#
#     class Test5:
#         def test_method(self): ...
#
#     class Test6:
#         def test_method2(self): ...
#
#     class Test7:
#         def test_method3(self): ...
#
#     class Test8(Test5, Test6, Test7, Test4, ApiImplementation):
#         ...
#
#     test4 = Test8()
