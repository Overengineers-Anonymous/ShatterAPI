from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .mapping import Mapping

class Api(Protocol):
    mapping: "Mapping"

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "mapping"):
            raise TypeError(f"{cls.__name__} must have a 'mapping' attribute of type Mapping")
        cls.mapping.build_description(cls)
        return super().__init_subclass__()
