#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides an environment for running python scripts, tests, tools etc."""

import logging
import os
import sys

from .singleton import Singleton


class Environment(metaclass=Singleton):
    """ """
    from enum import IntEnum

    class EnvMode(IntEnum):
        """Running on native system."""
        NATIVE = 0
        """Running in virtual environment."""
        VIRTUAL = 1

    class LogMode(IntEnum):
        """Logging disabled."""
        NONE = 0
        """Logging to console only."""
        CONSOLE = 1
        """Logging to console and file."""
        FILE = 2

    class RefreshMode(IntEnum):
        """Do nothing, just activate virtual env in case of virtual env mode."""
        NONE = 0
        """Recreate venv path (if env_mode is 'virtual') and reinstall requirements."""
        FORCE = 1
        """create venv path (if env_mode is 'virtual' and path does not exist) and reinstall requirements."""
        SMART = 2

    def __init__(self):
        self._name = os.path.basename(os.getcwd())
        self._logger = logging.getLogger(self.__class__.__name__)
        self._python_cmd = self._get_python_cmd()
        self._version_info = {"python": ".".join(map(str, sys.version_info[0:3]))}
        self._configuration = {}

    def activate(self, env_mode: EnvMode = EnvMode.VIRTUAL, **kwargs):
        """Activate environment."""

        # TODO: add option to pass list of requirements
        env_path = kwargs.pop("env_path", None) or "venv"
        refresh_mode = kwargs.pop("refresh_mode", None) or Environment.RefreshMode.NONE
        log_mode = kwargs.pop("log_mode", None) or Environment.LogMode.NONE
        log_level = kwargs.pop("log_level", None) or logging.INFO

        assert not kwargs, "Unknown arguments: %r" % kwargs

        self._activate_logging(log_mode=log_mode, log_level=log_level)

        if env_mode == Environment.EnvMode.VIRTUAL:
            if refresh_mode == Environment.RefreshMode.FORCE or not os.path.exists(env_path):  # or env_path does not exist
                self._create_virtual_environment(env_path=env_path)
                refresh_mode = Environment.RefreshMode.FORCE  # when (re-)creating virtual env, required packages needs to be installed as well
            self._activate_virtual_environment(env_path=env_path)

        if refresh_mode > Environment.RefreshMode.NONE:

            requirements = []

            # collect relevant paths
            paths = []
            path = os.path.dirname(os.path.join(*self.__module__.split(".")))
            while path:
                paths.append(os.path.abspath(path))
                path = os.path.dirname(path)

            paths.append(os.getcwd())

            # search for requirements
            for path in paths:
                if not os.path.exists(os.path.join(path, "requirements.txt")):
                    continue
                try:
                    with open(os.path.join(path, "requirements.txt")) as req_file:
                        for line in req_file.readlines():
                            if line.strip().startswith("#"):
                                continue
                            requirements.append(line.strip())
                except OSError as ex:
                    self._logger.warning(ex)

            # install requirements
            if requirements:
                self._update_requirements(requirements=requirements)

        self._update_version_info()

    def _activate_logging(self, log_mode: LogMode = LogMode.NONE, log_level=None, log_name=None):
        """Activate logging."""

        formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        for handler in logger.handlers:
            logger.removeHandler(handler)

        if log_mode <= Environment.LogMode.NONE:
            return

        # create console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.setLevel(log_level or logging.INFO)
        logger.addHandler(ch)

        if log_mode < Environment.LogMode.FILE:
            return

        # create file handler
        os.makedirs("results", exist_ok=True)
        fh = logging.FileHandler(os.path.join("results", (log_name or "results") + ".log"))
        fh.setFormatter(formatter)
        fh.setLevel(log_level or logging.DEBUG)
        logger.addHandler(fh)

    def _activate_virtual_environment(self, env_path):
        """Activate virtual environment."""

        self._logger.debug("activating virtual environment ...")

        base = os.path.abspath(env_path)
        path = os.path.join(base, "Scripts") if "win" in sys.platform else os.path.join(base, "bin")
        original_os_path = os.environ.get("PATH", "")

        os.environ["PATH"] = path + os.pathsep + original_os_path
        site_packages = os.path.join(base, "Lib", "site-packages") if "win" in sys.platform else os.path.join(base, "lib", "python%s" % sys.version[:3], "site-packages")

        # do not change this order!
        original_sys_path = list(sys.path)

        import site
        site.addsitedir(site_packages)

        sys.real_prefix = sys.prefix
        sys.prefix = base
        sys.executable = os.path.join(path, os.path.basename(sys.executable))

        # Move the added items to the front of the path:
        new_sys_path = []
        for item in list(sys.path):
            if item not in original_sys_path:
                new_sys_path.append(item)
                sys.path.remove(item)
        sys.path[:0] = new_sys_path

        self._python_cmd = self._get_python_cmd()

    def _create_virtual_environment(self, env_path):
        """Create virtual environment."""

        import venv

        self._logger.debug("creating virtual environment ...")

        venv.create(env_path,
                    system_site_packages=False,
                    clear=True,
                    with_pip=True)

    def _get_python_cmd(self):
        """Return python command path."""

        cmd = os.path.join(os.path.dirname(sys.executable), f"python{sys.version_info[0]}.{sys.version_info[1]}")
        if not os.path.exists(cmd):
            cmd = os.path.join(os.path.dirname(sys.executable), f"python{sys.version_info[0]}")
        if not os.path.exists(cmd):
            cmd = os.path.join(os.path.dirname(sys.executable), f"python")

        return cmd

    def _update_requirements(self, requirements):
        """Update requirements."""

        import subprocess

        self._logger.debug("updating requirements ...")

        try:
            command = f"{self._python_cmd} -m pip install --no-cache-dir --upgrade pip"
            output = subprocess.check_output(command.split()).decode("utf-8").strip()
        except subprocess.CalledProcessError as ex:
            self._logger.error("installation failed: %s", ex)
            return False

        import pip
        self._version_info["python"] = ".".join(map(str, sys.version_info[0:3]))
        self._version_info["pip"] = pip.__version__

        try:
            req_str = " ".join([requirement.strip() for requirement in requirements.split(",")] if isinstance(requirements, str) else requirements)
            command = f"{self._python_cmd} -m pip install --no-cache-dir --force-reinstall {req_str}"
            output = subprocess.check_output(command.split()).decode("utf-8").strip()

        except subprocess.CalledProcessError as ex:
            self._logger.error("installation failed: %s", ex)
            return False

    def _update_version_info(self):
        """ """

        import subprocess

        self._get_python_cmd()

        try:
            command = f"{self._python_cmd} -m pip freeze"
            output = subprocess.check_output(command.split()).decode("utf-8").strip()
            for line in output.splitlines():
                package_info = line.split("==")
                self._version_info[package_info[0]] = package_info[1] if len(package_info) > 1 else ""
        except subprocess.CalledProcessError as ex:
            self._logger.error("installation failed: %s", ex)
            return False

        for k, v in self._version_info.items():
            self._logger.debug(f"    {k:24} {v}")

        return True
