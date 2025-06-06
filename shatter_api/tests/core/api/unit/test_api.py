# def test_bind_info_add_func():
#     from shatter_api.core.api import BindInfo
#
#     def dummy_wrapper(func):
#         return func
#
#     bind_info = BindInfo(dummy_wrapper)
#     assert len(bind_info.wrapped_funcs) == 0
#
#     def dummy_func():
#         pass
#
#     bind_info.add_func(dummy_func)
#     assert len(bind_info.wrapped_funcs) == 1
#     assert bind_info.wrapped_funcs[0] == dummy_func
#
# def test_bind_info_copy():
#     from shatter_api.core.api import BindInfo
#
#     def dummy_wrapper(func):
#         return func
#
#     bind_info = BindInfo(dummy_wrapper)
#     assert len(bind_info.wrapped_funcs) == 0
#
#     def dummy_func():
#         pass
#
#     bind_info.add_func(dummy_func)
#     copied_bind_info = bind_info.copy()
#
#     assert len(copied_bind_info.wrapped_funcs) == 1
#     assert copied_bind_info.wrapped_funcs[0] == dummy_func
#     assert copied_bind_info.wrapper == dummy_wrapper
#
# def test_bind_info_add():
#     from shatter_api.core.api import BindInfo
#
#     def dummy_wrapper(func):
#         return func
#
#     def dummy_wrapper2(func):
#         return func
#
#     bind_info1 = BindInfo(dummy_wrapper)
#     bind_info2 = BindInfo(dummy_wrapper2)
#
#     def dummy_func1():
#         pass
#
#     def dummy_func2():
#         pass
#
#     bind_info1.add_func(dummy_func1)
#     bind_info2.add_func(dummy_func2)
#
#     combined_bind_info = bind_info1 + bind_info2
#
#     assert len(combined_bind_info.wrapped_funcs) == 2
#     assert combined_bind_info.wrapped_funcs[0] == dummy_func1
#     assert combined_bind_info.wrapped_funcs[1] == dummy_func2
#     assert combined_bind_info.wrapper == dummy_wrapper
