#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides a Const type to be used to define readonly attributes."""


class Const(type):
    """
    Basic const type implementation.

    Use it as the metaclass, when implementing a class containing readonly attributes.

    Example:
        class MyClass(metaclass=Const):
            my_param = Const.Attribute("xyz")

    This will define myparam as readonly.
    Each try to change its value - be it as class attribute or instance attribute - will raise an AttributeError:
        MyClass.my_param = 5
        MyClass().my_param = "abc"
    """

    def __setattr__(cls, name, value):
        """Set attribute value (if allowed)."""
        # these two lines look like the more proper check, but there's an easier approach used below
        #     attributes = tuple([item for item in Const.__dict__.values() if isinstance(item, type)])
        #     if isinstance(getattr(cls, name, None), attributes):
        attr = type(getattr(cls, name, None))
        if attr.__module__ == __name__ and attr.__qualname__.startswith("Const."):
            raise AttributeError("can't set attribute")
        super(Const, cls).__setattr__(name, value)

    class Attribute:  # pylint: disable=too-few-public-methods
        """Attribute class."""

        def __init__(self, value):
            self.value = value

        def __call__(self):
            return self.value

        def __len__(self):
            return len(self.value)

        def __repr__(self):
            return str(self.value)

        def __str__(self):
            return str(self.value)

    class Int(int):  # pylint: disable=too-few-public-methods
        """Int attribute class."""

    class Str(str):  # pylint: disable=too-few-public-methods
        """Str attribute class."""


class ConstBase(metaclass=Const):
    """
    Basic const class implementation.

    Use it as base class, when implementing a class containing readonly attributes.

    Example:
        class MyClass(ConstBase):
            my_param = Const.Attribute("xyz")

    This will define myparam as readonly.
    Each try to change its value - be it as class attribute or instance attribute - will raise an AttributeError:
        MyClass.my_param = 5
        MyClass().my_param = "abc"
    """

    def __setattr__(self, name, value):
        """Set attribute value (if allowed)."""
        # these two lines look like the more proper check, but there's an easier approach used below
        #     attributes = tuple([item for item in Const.__dict__.values() if isinstance(item, type)])
        #     if isinstance(getattr(self, name, None), attributes):
        attr = type(getattr(self, name, None))
        if attr.__module__ == __name__ and attr.__qualname__.startswith("Const."):
            raise AttributeError("can't set attribute")
        super(ConstBase, self).__setattr__(name, value)
