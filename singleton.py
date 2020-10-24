#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides a metaclass that acts as a singleton."""

import threading


class Singleton(type):
    """A metaclass that acts as a singleton."""

    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        # print("__call__", cls._instances[cls], dir(cls._instances[cls]), args, kwargs)
        return cls._instances[cls]


class SingletonClass(metaclass=Singleton):
    pass