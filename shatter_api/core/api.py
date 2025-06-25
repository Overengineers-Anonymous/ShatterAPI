"""
API Wrapper and Descriptor System

This module provides the core API framework for defining, wrapping, and executing
API endpoints with type safety and inheritance support.
"""

from typing import Callable, Protocol, cast, overload
import functools

from .utils import has_base, FuncSignature


class ApiWrapper:
    """
    Wraps a function with API metadata including path, base functions, and owner information.

    Provides functionality for method inheritance, signature validation, and
    implementation checking in API descriptor hierarchies.
    """

    def __init__(
        self, func: Callable, path: str = "", base: "ApiWrapper | None" = None, owner: "type[ApiDescriptor] | None" = None
    ):
        """
        Initialize an API wrapper for a function.

        Args:
            func: The function to wrap
            path: API path for this function
            base: Base wrapper this extends (for inheritance)
            owner: The ApiDescriptor class that owns this wrapper
        """
        self.path = path
        self.func = func
        self.annotations = func.__annotations__
        self._base: ApiWrapper | None = base
        self._owner = owner
        self.sig = FuncSignature.from_func(func)

    @property
    def base(self) -> "ApiWrapper | None":
        return self._base

    @base.setter
    def base(self, value: "ApiWrapper"):
        """Set the base wrapper, ensuring no redefinition conflicts."""
        if not isinstance(value, ApiWrapper):
            raise TypeError(f"Base must be an ApiWrapper, got {type(value).__name__}")

        if self._base is not None:
            error_msg = (
                f"Method '{self.func_name}' is already defined in ApiDescriptor "
                f"'{self.owner.__name__}'. ApiDescriptor '{value.owner.__name__}' "
                f"attempts to redefine it"
            )
            raise TypeError(error_msg)

        self._base = value

    def is_unimplemented(self, func: Callable) -> bool:
        """
        Check if a function is unimplemented in the inheritance chain.

        Args:
            func: Function to check for implementation

        Returns:
            True if the function is unimplemented, False otherwise
        """
        # If this wrapper belongs to an ApiImplementation, it's implemented
        if has_base(self.owner, ApiImplementation):
            unimplemented = False
        else:
            # Otherwise, check if this is the original unimplemented function
            unimplemented = func is self.func

        # If no base wrapper exists, return the current implementation status
        if self.base is None:
            return unimplemented

        # Check the inheritance chain
        return unimplemented or self.base.is_unimplemented(func)

    @property
    def func_name(self) -> str:
        return self.func.__name__

    def _wrapper(self, inner: Callable) -> Callable:
        """Create a wrapper function for debugging and execution tracking."""

        @functools.wraps(inner)
        def wrapped(*args, **kwargs):
            # Optional: Add debugging or logging here
            # print(f"Wrapped function: {self.func_name} at path: {self.path}")
            return inner(*args, **kwargs)

        return wrapped

    def wrap(self, cls: "type[ApiImplementation]"):
        """
        Apply the wrapper to a method in an ApiImplementation class.

        Args:
            cls: The ApiImplementation class to modify
        """
        func = getattr(cls, self.func_name)

        # Only wrap if not already wrapped
        if not getattr(func, "_api_wrapper", False):
            wrapped = self._wrapper(func)
            wrapped._api_wrapper = True  # type: ignore
            setattr(cls, self.func_name, wrapped)

    def __eq__(self, other: object) -> bool:
        """Compare two ApiWrapper instances for equality."""
        if not isinstance(other, ApiWrapper):
            raise TypeError(f"Cannot compare ApiWrapper with {type(other).__name__}")

        return self.func_name == other.func_name and self.path == other.path

    @property
    def owner(self) -> "type[ApiDescriptor]":
        if self._owner is None:
            raise TypeError(f"ApiWrapper {self.func_name} has no owner")
        return self._owner

    @owner.setter
    def owner(self, value: "type[ApiDescriptor]"):
        """Set the owner ApiDescriptor class."""
        if not has_base(value, ApiDescriptor):
            raise TypeError(f"Owner must be an ApiDescriptor, got {type(value).__name__}")
        self._owner = value


class FunctionMap:
    """
    Manages a collection of ApiWrapper instances and their path mappings.

    Handles inheritance relationships between API descriptors and validates
    function signatures for compatibility.
    """

    def __init__(self):
        """Initialize an empty function map."""
        self.wrappers: dict[str, ApiWrapper] = {}
        self.path_mapping: dict[str, str] = {}
        self._owner: type | None = None

    def add_wrapper(self, wrapper: ApiWrapper):
        """Add a wrapper to this function map."""
        self.wrappers[wrapper.func_name] = wrapper
        self.path_mapping[wrapper.path] = wrapper.func_name

    def add_base(self, base_fm: "FunctionMap"):
        """
        Add a base function map, handling inheritance and validation.

        Args:
            base_fm: The base FunctionMap to inherit from

        Raises:
            TypeError: If there are conflicts in path bindings or function signatures
        """
        for wrapper in base_fm.wrappers.values():
            if wrapper.func_name not in self.wrappers:
                # Check for path conflicts
                existing_func_name = self.path_mapping.get(wrapper.path)
                if existing_func_name is not None and existing_func_name != wrapper.func_name:
                    error_msg = (
                        f"ApiDescriptor {self.owner.__name__} rebinds path "
                        f"'{wrapper.path}' to another method '{existing_func_name}'"
                    )
                    raise TypeError(error_msg)

                # Create new wrapper with base reference
                api_wrapper = ApiWrapper(func=wrapper.func, path=wrapper.path, base=wrapper, owner=wrapper.owner)
                self.wrappers[api_wrapper.func_name] = api_wrapper
                self.add_wrapper(api_wrapper)
            else:
                # Validate signature compatibility
                current_func_sig = self.wrappers[wrapper.func_name].sig
                if not current_func_sig.compatible_with(wrapper.sig):
                    error_msg = (
                        f"Function '{wrapper.func_name}' in {self.owner.__name__} "
                        f"is not compatible with base function '{wrapper.func_name}' "
                        f"in {base_fm.owner.__name__}"
                    )
                    raise TypeError(error_msg)

                # Set base and validate path consistency
                self.wrappers[wrapper.func_name].base = wrapper
                current_wrapper = self.wrappers[wrapper.func_name]

                if wrapper.path != current_wrapper.path:
                    error_msg = (
                        f"Method '{current_wrapper.func_name}' is already bound to "
                        f"path '{wrapper.path}' in ApiDescriptor {wrapper.owner.__name__}, "
                        f"but ApiDescriptor {current_wrapper.owner.__name__} attempts "
                        f"to rebind it to '{current_wrapper.path}'"
                    )
                    raise TypeError(error_msg)

    @property
    def owner(self) -> type:
        if self._owner is None:
            raise TypeError("FunctionMap has no owner")
        return self._owner

    @owner.setter
    def owner(self, value: type):
        """Set the owner type and update all wrappers."""
        if not isinstance(value, type):
            raise TypeError(f"Owner must be a type, got {type(value).__name__}")

        for wrapper in self.wrappers.values():
            wrapper.owner = value
        self._owner = value


class PathExecutor(Protocol):
    """
    Protocol for executing functions associated with API paths.

    Provides a common interface for different types of path execution
    strategies (bound methods, extended APIs, etc.).
    """

    def call(self, cls: "ApiDescriptor", *args, **kwargs):
        """Executes the function associated with this path executor."""
        raise NotImplementedError("Subclasses must implement this method")

    def get_handler(self, cls: "ApiDescriptor") -> Callable:
        """Returns the function that this executor will call."""
        raise NotImplementedError("Subclasses must implement this method")


class BoundPathExecutor(PathExecutor):
    """
    Executes bound methods directly from an ApiDescriptor instance.

    Caches method handlers for performance and provides direct method execution.
    """

    def __init__(self, path: str, wrapper: ApiWrapper):
        """
        Initialize with path and wrapper information.

        Args:
            path: The API path for this executor
            wrapper: The ApiWrapper containing method metadata
        """
        self.wrapper = wrapper
        self.path = path
        self.handler = None

    def get_handler(self, cls: "ApiDescriptor") -> Callable:
        """Get the callable handler for this path."""
        if self.handler is not None:
            return self.handler

        self.handler = getattr(cls, self.wrapper.func_name)
        return self.handler

    def call(self, cls: "ApiDescriptor", *args, **kwargs):
        """Execute the handler with the given arguments."""
        return self.get_handler(cls)(*args, **kwargs)


class ExtendedPathExecutor(PathExecutor):
    """
    Executes methods from extended API descriptors.

    Handles sub-API execution with optional caching for performance optimization.
    """

    def __init__(self, path: str, func_sig: FuncSignature, cacheable: bool = False):
        """
        Initialize with path, signature, and caching preferences.

        Args:
            path: The API path for this executor
            func_sig: Function signature information
            cacheable: Whether to cache the handler for performance
        """
        self.path = path
        self.func_sig = func_sig
        self.cacheable = cacheable
        self.handler = None

    def get_handler(self, cls: "ApiDescriptor"):
        """Get the handler from the extended API descriptor."""
        if self.cacheable and self.handler is not None:
            return self.handler

        # Get the sub-mapping attribute from the class
        sub_mapping_attr: ApiDescriptor | Callable[[], ApiDescriptor] = getattr(cls, self.func_sig.name)

        # Handle callable vs property sub-mappings
        if callable(sub_mapping_attr):
            sub_mapping = sub_mapping_attr()
        elif has_base(sub_mapping_attr.__class__, ApiDescriptor):
            sub_mapping = sub_mapping_attr
        else:
            raise TypeError(
                f"Extended API attribute '{self.func_sig.name}' must be either "
                f"a callable returning an ApiDescriptor or an ApiDescriptor instance"
            )

        self.handler = sub_mapping.mapping.get_handler(self.path)
        return self.handler

    def call(self, cls: "ApiDescriptor", *args, **kwargs):
        """Execute the extended API handler."""
        return self.get_handler(cls)(*args, **kwargs)


class BoundMapping:
    """
    A bound mapping that dispatches API calls to the appropriate handlers.

    Provides path-based routing and handler resolution for API instances.
    """

    def __init__(self, obj, paths: dict[str, PathExecutor]):
        """
        Initialize with parent object and path executors.

        Args:
            obj: The parent API object
            paths: Dictionary mapping paths to their executors
        """
        self.parent = obj
        self.paths = paths

    def dispatch(self, path: str, *args, **kwargs):
        """
        Dispatch a call to the appropriate path handler.

        Args:
            path: The API path to execute
            *args, **kwargs: Arguments to pass to the handler

        Returns:
            The result of the handler execution

        Raises:
            KeyError: If the path is not found in the mapping
        """
        if path not in self.paths:
            raise KeyError(f"Path '{path}' not found in API mapping")

        return self.paths[path].call(self.parent, *args, **kwargs)

    def get_handler(self, path: str) -> Callable:
        """
        Get the handler function for a specific path.

        Args:
            path: The API path

        Returns:
            The callable handler for the path

        Raises:
            KeyError: If the path is not found in the mapping
        """
        if path not in self.paths:
            raise KeyError(f"Path '{path}' not found in API mapping")

        return self.paths[path].get_handler(self.parent)


class Mapping:
    """
    Manages API route registration and path mapping for ApiDescriptor classes.

    Provides decorators for registering routes and extensions, handles inheritance,
    and creates bound mappings for API instances.
    """

    def __init__(self, base_path: str = ""):
        """
        Initialize a new mapping with optional base path.

        Args:
            base_path: Base path prefix for all routes in this mapping
        """
        self.func_map = FunctionMap()
        self.owner = None
        self.base_path = base_path
        self.paths: dict[str, PathExecutor] = {}
        self.bm = None

    def route(self, path: str):
        """
        Decorator for registering a function to a specific API route.

        Args:
            path: The API path (will be prefixed with base_path)

        Returns:
            Decorator function that registers the route
        """
        full_path = self.base_path + path

        def register_wrapper[T: Callable](func: T) -> T:
            wrapper = ApiWrapper(func, full_path)
            self.func_map.add_wrapper(wrapper)
            self.paths[full_path] = BoundPathExecutor(full_path, wrapper)
            return func

        return register_wrapper

    def extend(self, cached: bool = False):
        """
        Decorator for registering API extensions.

        Args:
            cached: Whether to cache the extended API handlers

        Returns:
            Decorator function that registers the extension
        """

        def register_extension[T: Callable](func: T) -> T:
            func_sig = FuncSignature.from_func(func)

            # Validate return type annotation
            if type(func_sig.return_type) is str:
                raise TypeError(
                    f"Function '{func.__name__}' must have a return type annotation, quoted annotation is not allowed"
                )

            if not has_base(func_sig.return_type, ApiDescriptor):
                raise TypeError(
                    f"Function '{func.__name__}' must return a valid ApiDescriptor. "
                    f"It returned: '{func_sig.return_type.__name__}'"
                )

            # Register paths from the extended API descriptor
            api_descriptor = cast(type[ApiDescriptor], func_sig.return_type)
            for path in api_descriptor.mapping.paths:
                if path not in self.paths:
                    self.paths[path] = ExtendedPathExecutor(path, func_sig, cached)
                else:
                    raise TypeError(f"Path '{path}' is already defined in this mapping")

            return func

        return register_extension

    def __set_name__(self, owner, name):
        """
        Descriptor method called when the mapping is assigned to a class attribute.

        Sets up inheritance relationships and validates the mapping configuration.
        """
        if name != "mapping":
            raise TypeError(f"Mapping must be named 'mapping', got '{name}'")

        self.name = f"_{name}"
        self.func_map_name = f"_{name}_func_map"
        self.owner = owner
        self.func_map.owner = owner

        # Handle inheritance from base classes
        for base_cls in owner.__bases__:
            if has_base(base_cls, ApiDescriptor):
                base_cls = cast(type[ApiDescriptor], base_cls)

                # Get the base function map
                base_func_map = getattr(base_cls, self.func_map_name, None)
                if base_func_map is None:
                    raise TypeError(f"Base class {base_cls.__name__} has no function map")

                if not isinstance(base_func_map, FunctionMap):
                    raise TypeError(f"Base class {base_cls.__name__} has invalid function map")

                # Add base function map and inherit paths
                self.func_map.add_base(base_func_map)
                for path, executor in base_cls.mapping.paths.items():
                    if path not in self.paths:
                        self.paths[path] = executor

        # Store the function map on the owner class
        setattr(owner, self.func_map_name, self.func_map)

    def has_child(self, api_implementation: "type[ApiImplementation]") -> bool:
        """
        Check if an ApiImplementation is a child of this mapping.

        Args:
            api_implementation: The implementation class to check

        Returns:
            True if it's a child implementation, False otherwise
        """
        if not has_base(api_implementation, ApiImplementation):
            raise TypeError(f"Expected an ApiImplementation, got {type(api_implementation).__name__}")

        return api_implementation in self.func_map.wrappers.values()

    def bind(self, obj: "type[ApiImplementation]"):
        """
        Bind this mapping to an ApiImplementation class.

        Validates that all required methods are implemented and wraps them
        with the appropriate API wrappers.

        Args:
            obj: The ApiImplementation class to bind to
        """
        for name, wrapper in self.func_map.wrappers.items():
            func = getattr(obj, name, None)

            if func is None:
                continue

            if not callable(func):
                raise TypeError(f"'{name}' in {obj.__class__.__name__} is not callable")

            if wrapper.is_unimplemented(func):
                raise TypeError(f"Function '{name}' has no implementation")

            wrapper.wrap(obj)

    @overload
    def __get__(self, obj: None, objtype: type) -> "Mapping": ...

    @overload
    def __get__(self, obj: object, objtype: type) -> "BoundMapping": ...

    def __get__(self, obj: object | None, objtype: type | None = None) -> "BoundMapping | Mapping":
        """
        Descriptor method for getting bound or unbound mappings.

        Returns:
            BoundMapping when accessed from an instance, Mapping when accessed from class
        """
        if obj is None and objtype is not None:
            return self

        if self.bm is not None:
            return self.bm

        self.bm = BoundMapping(obj, self.paths)
        return self.bm


class ApiImplementation:
    """
    Base class for API implementations.

    Provides automatic binding of API mappings and handles inheritance
    validation for API descriptor implementations.
    """

    mapping: Mapping

    def __init_subclass__(cls) -> None:
        """
        Handle subclass initialization for ApiImplementation classes.

        Validates inheritance relationships and binds mappings to implementations.
        """
        # Check if this class has a base class (not the root ApiImplementation)
        if cls.__base__:
            if not has_base(cls, ApiDescriptor):
                raise TypeError(f"{cls.__name__} must inherit from a class that subclasses ApiDescriptor")

            # Bind the mapping to this implementation
            cls.mapping.bind(cls)

        # Handle special __init__ method marking
        if getattr(cls.__init__, "_api_descr_init", False):
            # If __init__ is marked as ApiDescriptor init, replace with object.__init__
            setattr(cls, "__init__", object.__init__)

        super().__init_subclass__()


class ApiDescriptor(Protocol):
    """
    Protocol defining the interface for API descriptors.

    API descriptors define the structure and routing for APIs without
    providing implementations. They must be inherited by ApiImplementation
    classes to provide actual functionality.
    """

    mapping: Mapping

    def __init_subclass__(cls):
        """
        Handle subclass initialization for ApiDescriptor classes.

        Validates that descriptors have proper mapping attributes and
        prevents direct instantiation.
        """
        if not has_base(cls, ApiImplementation):
            # Validate mapping attribute exists and is properly configured
            if not hasattr(cls, "mapping"):
                raise TypeError(f"ApiDescriptor {cls.__name__} must have a 'mapping' attribute")

            if cls.mapping.owner is not cls:
                raise TypeError(f"ApiDescriptor {cls.__name__} must have its own 'mapping' attribute")

            if Protocol not in cls.__bases__:
                raise TypeError(f"ApiDescriptor {cls.__name__} must inherit from Protocol")

            # Create a custom __init__ that prevents instantiation
            def __init__(self, *args, **kwargs):
                raise TypeError(f"ApiDescriptor {self.__class__.__name__} cannot be instantiated directly")

            __init__._api_descr_init = True  # type: ignore
            setattr(cls, "__init__", __init__)

        super().__init_subclass__()


class RouteMap[T: "ApiDescriptor"]:
    """
    Manages routing configuration for API descriptors.

    Provides a fluent interface for building API route hierarchies
    and binding implementations to specific paths.
    """

    def __init__(self, root: str, descriptor: type[T]):
        """
        Initialize a route map with root path and descriptor type.

        Args:
            root: Root path for this route map
            descriptor: ApiDescriptor type to manage
        """
        self.root = root
        self.api_descriptor = descriptor

    def add_descriptor[TD: "ApiDescriptor"](self, root: str, descriptor: "type[TD]") -> "RouteMap[TD]":
        """
        Add a child descriptor to this route map.

        Args:
            root: Root path for the child descriptor
            descriptor: Child ApiDescriptor type

        Returns:
            New RouteMap for the child descriptor
        """
        return RouteMap(self.root + root, descriptor)

    def api_implementation(self, root: str, implementation: "T"):
        """
        Bind an API implementation to a specific root path.

        Args:
            root: Root path for the implementation
            implementation: ApiImplementation instance
        """
        # TODO: Implement implementation binding logic
        pass

    def cast_to_child(self, path: str) -> "T":
        """
        Cast this route map to a child type at the specified path.

        Args:
            path: Path to cast to

        Returns:
            Casted instance of the child type
        """
        # TODO: Implement child casting logic
        raise NotImplementedError("Child casting not yet implemented")


class MagicClient:
    """
    Creates dynamic client instances from API implementations.

    Automatically generates client objects that mirror the API structure
    with proper method signatures and routing.
    """

    def __init__(self, api_implementation: ApiImplementation):
        """
        Initialize the magic client with an API implementation.

        Args:
            api_implementation: The API implementation to create clients from
        """
        self.api_implementation = api_implementation

    def _create_client(self, api_descriptor: type[ApiDescriptor]) -> object:
        """
        Create a dynamic client class for the given API descriptor.

        Args:
            api_descriptor: The API descriptor to create a client for

        Returns:
            Dynamic client instance
        """

        class DynamicClient:
            """Dynamically generated client class."""

            pass

        # Process each path in the descriptor mapping
        for path, executor in api_descriptor.mapping.paths.items():
            if isinstance(executor, BoundPathExecutor):
                # Handle bound path executors
                handler = self.api_implementation.mapping.get_handler(path)
                func_sig = FuncSignature.from_func(handler)

                if executor.wrapper.sig.compatible_with(func_sig):
                    setattr(DynamicClient, executor.wrapper.func_name, handler)
                else:
                    error_msg = (
                        f"Function '{executor.wrapper.func_name}' in {api_descriptor.__name__} "
                        f"is not compatible with base function '{func_sig.name}' "
                        f"in '{executor.wrapper.owner.__name__}'"
                    )
                    raise TypeError(error_msg)

            elif isinstance(executor, ExtendedPathExecutor):
                # Handle extended path executors (nested APIs)
                client_attr = self._create_client(executor.func_sig.return_type)
                setattr(DynamicClient, executor.func_sig.name, client_attr)

            else:
                raise TypeError(f"Unknown PathExecutor type: {type(executor).__name__}")

        return DynamicClient()

    def create_dynamic_client[T: ApiDescriptor](self, api_descriptor: type[T]) -> T:
        """
        Create a dynamic client for the specified API descriptor.

        Args:
            api_descriptor: The API descriptor type to create a client for

        Returns:
            Dynamic client instance typed as the descriptor

        Raises:
            TypeError: If the provided type is not an ApiDescriptor
        """
        if not has_base(api_descriptor, ApiDescriptor):
            raise TypeError(f"Expected an ApiDescriptor, got {type(api_descriptor).__name__}")

        return cast(T, self._create_client(api_descriptor))


# Global route map instance for API registration
route_map = RouteMap(".", ApiDescriptor)
