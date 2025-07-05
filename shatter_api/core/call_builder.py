# from .request import RequestCtx, RequestBody, RequestHeaders, RequestQueryParams
# from typing import Any
# class CallCtx:
#     def __init__(self, ctx: RequestCtx):
#         self.object_mapping: dict[type, object] = {
#             RequestCtx: ctx
#         }
#         self.reqctx = ctx
#
#     def get_object(self, obj_type: type) -> object:
#         """
#         Retrieves an object of the specified type from the context.
#         If the object does not exist, it raises a KeyError.
#         """
#         if obj_type not in self.object_mapping:
#             raise KeyError(f"Object of type {obj_type} not found in context.")
#         return self.object_mapping[obj_type]
#
#     def set_object(self, obj_type: type, obj: object) -> None:
#         """
#         Sets an object of the specified type in the context.
#         If an object of that type already exists, it raises a ValueError.
#         """
#         if obj_type in self.object_mapping:
#             raise ValueError(f"Object of type {obj_type} already exists in context.")
#         self.object_mapping[obj_type] = obj
#
# class CallInfo:
#     def __init__(self, args: tuple, kwargs: dict):
#         self.args = args
#         self.kwargs = kwargs
#
# class CallBuilder:
#     def __init__(self, ctx: CallCtx):
#         ...
#
#     def _get_func_args(self, func_sig: ApiFuncSig, req: RequestCtx) -> list[Any]:
#         func_args = func_sig.args
#         args = []
#         for arg, _type in func_args.items():
#             if issubclass(_type, RequestBody):
#                 args.append(_type.model_validate(req.body))
#             elif issubclass(_type, RequestCtx):
#                 args.append(req)
#             elif issubclass(_type, RequestHeaders):
#                 args.append(_type.model_validate(req.headers))
#             elif issubclass(_type, RequestQueryParams):
#                 args.append(_type.model_validate(req.query_params))
#             else:
#                 raise TypeError(f"Unsupported type '{_type}' for argument '{arg}' in function '{func_sig.name}'")
#         return args
#
#
