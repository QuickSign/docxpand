"""Instantiable class definition."""
import copy
import importlib
import re
import typing as tp


def _is_string_formattable(value: str) -> bool:
    """Test if a string is formattable (i.e. contains {.*} pattern).

    Args:
        value: the string to test

    Returns:
        True if it is formattable, else False
    """
    return re.search("{.*}", value) is not None


def import_object(full_name: str) -> tp.Any:
    """Dynamically import an object using its fully qualified name.

    Args:
        full_name: fully qualified name of the object to import

    Returns:
        the imported object
    """
    module_name, object_name = full_name.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, object_name)


class Instantiable:
    """Factory that instantiates object from dictionary definitions."""

    @staticmethod
    def is_instantiable(object: tp.Any) -> bool:
        """Indicate whether any object is candidate to `instantiate` method.

        The object must follow these rules to be instantiable:
            - be a python dictionary
            - have a "__class__" key

        The "init_args" and "init_context" keys are optional.

        Args:
            object: the object to test

        Returns:
            True if it is compatible with `instantiate` method, else False.
        """
        if not isinstance(object, dict):
            return False
        return "__class__" in object

    @staticmethod
    def instantiate(instantiable: tp.Dict, **kwargs) -> tp.Any:
        """Instantiate an object from a dictionary definition.

        The object is instantiated using these pieces of information:
            - the value under the "__class__" is imported as the class
              to instantiate
            - the keywords arguments under the "init_args" are extracted
            - these arguments are also instantiated if applicable
            - these arguments are formatted using the context if applicable
            - the values missing at configuration writing time are completed
              using the context if they are available at runtime

        Args:
            instantiable: an instantiable dictionary
            **kwargs: the context

        Returns:
            the fully instantiated object
        """
        instantiable = copy.deepcopy(instantiable)

        # Initialize arguments
        arguments = instantiable.get("init_args", {})
        assert isinstance(arguments, dict)

        # Format configuration arguments using context and instantiate
        # sub-objects when applicable
        for key, value in arguments.items():
            if isinstance(value, str) and _is_string_formattable(value):
                arguments[key] = value.format(**kwargs)
            elif isinstance(value, list):
                arguments[key] = [
                    Instantiable.try_instantiate(element, **kwargs) for element in value
                ]
            else:
                arguments[key] = Instantiable.try_instantiate(value, **kwargs)

        # Add other arguments from context
        for key, value in instantiable.get("init_context", {}).items():
            if value in kwargs:
                arguments[key] = kwargs.get(value)

        # Import module and class
        the_class_str = instantiable.get("__class__")
        assert isinstance(the_class_str, str)
        if _is_string_formattable(the_class_str):
            the_class_str = the_class_str.format(**kwargs)
        the_class = import_object(the_class_str)

        # Make instance
        instance = the_class(**arguments)

        return instance

    @staticmethod
    def try_instantiate(an_object: tp.Any, **kwargs) -> tp.Any:
        """Instantiate an object if possible.

        Args:
            an_object: an object that may be an instantiable dictionary
            **kwargs: the context

        Returns:
            the fully instantiated object when applicable, or the input object
        """
        if Instantiable.is_instantiable(an_object):
            return Instantiable.instantiate(an_object, **kwargs)

        return an_object


class CallableInstantiable(Instantiable):
    """Factory that calls methods from instantiable objects."""

    @staticmethod
    def is_callable(object: tp.Any) -> bool:
        """Indicate whether any object is candidate to `call` method.

        The object must follow these rules to be instantiable:
            - be a python dictionary
            - be instantiable
            - have a "__method__" key

        The "call_args" and "call_context" keys are optional.

        Args:
            object: the object to test

        Returns:
            True if it is compatible with `call` method, else False.

        """
        if not isinstance(object, dict):
            return False
        if not Instantiable.is_instantiable(object):
            return False
        return "__method__" in object

    @staticmethod
    def get_methods(
        callable: tp.Dict, **kwargs
    ) -> tp.Union[tp.Callable, tp.Dict[str, tp.Callable]]:
        """Get method(s) of an instantiable object from a dictionary.

        The object is first instantiated using Instantiable factory. Then,
        the method(s) are retrieved by their names, stored in "__method__" key.

        Args:
            callable: a callable object as dictionary
            **kwargs: the context

        Returns:
            the method or a dictionary of methods
        """
        # Instantiate object and get method
        instance = Instantiable.instantiate(callable, **kwargs)
        method_names = callable["__method__"]

        # Method could be a dictionary of method names
        if isinstance(method_names, dict):
            methods = {}
            for method_key, method_name in method_names.items():
                if _is_string_formattable(method_name):
                    method_name = method_name.format(**kwargs)
                method = getattr(instance, method_name)
                methods[method_key] = method
        # Or a single method name
        elif isinstance(method_names, str):
            if _is_string_formattable(method_names):
                method_names = method_names.format(**kwargs)
            methods = getattr(instance, method_names)
        else:
            raise ValueError(f"Unsupported __method__ argument: {method_names}")

        return methods

    @staticmethod
    def call(callable: tp.Dict, **kwargs) -> tp.Any:
        """Call method(s) of an instantiable object from a dictionary.

        The object is first instantiated using Instantiable factory. Then :
            - the method to call is retrieved by its name, stored in
              "__method__" key
            - the keywords arguments under the "call_args" are extracted
            - these arguments are also instantiated if applicable
            - these arguments are formatted using the context if applicable
            - the values missing at configuration writing time are completed
              using the context if they are available at runtime

        Args:
            callable: a callable object as dictionary
            **kwargs: the context

        Returns:
            the result of the method called on the instantiated object
        """
        callable = copy.deepcopy(callable)

        # Get methods
        methods = CallableInstantiable.get_methods(callable, **kwargs)
        # Initialize arguments
        arguments = callable.get("call_args", {})
        assert isinstance(arguments, dict)
        # Format configuration arguments using context and instantiate
        # sub-objects when applicable
        for key, value in arguments.items():
            if isinstance(value, str) and _is_string_formattable(value):
                arguments[key] = value.format(**kwargs)
            elif isinstance(value, list):
                arguments[key] = [
                    Instantiable.try_instantiate(element, **kwargs) for element in value
                ]
            else:
                arguments[key] = Instantiable.try_instantiate(value, **kwargs)

        # Add other arguments from context
        for key, value in callable.get("call_context", {}).items():
            if value in kwargs:
                arguments[key] = kwargs.get(value)
        if isinstance(methods, dict):
            results = {}
            for method_key, method in methods.items():
                results[method_key] = method(**arguments)
        else:
            results = methods(**arguments)

        return results

    @staticmethod
    def try_call(an_object: tp.Any, **kwargs) -> tp.Any:
        """Call a method of an object if possible.

        Args:
            an_object: an object that may be an instantiable and callable
                dictionary
            **kwargs: the context

        Returns:
            the result of the method called on the instantiated object when
            applicable, or the input object
        """
        if CallableInstantiable.is_callable(an_object):
            return CallableInstantiable.call(an_object, **kwargs)

        return an_object
