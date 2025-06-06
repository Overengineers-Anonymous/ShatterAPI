def has_base(cls: type, base_cls: type):
    if base_cls in cls.__bases__:
        return True
    if cls.__base__ is None:
        return False
    for b in cls.__bases__:
        if has_base(b, base_cls):
            return True
    return False
