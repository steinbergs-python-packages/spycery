#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functionality to monitoring processes."""

# standard
import datetime
import os
import threading

# 3rd party
import psutil


class ResourceMonitor(threading.Thread):
    """The ResourceMonitor class.

       Monitors the resource usage (cpu, mem, disk i/o) of current process (and any child processes).

       Example:

       monitor = ResourceMonitor()
       monitor.start()

       ...

       monitor.stop()

       Typically, the code above is placed around the main method of a python script. Of course it can be placed anywhwere else as well.
       To investigate single code sections later, 
    """

    @classmethod
    def set_label(cls, label):
        """Set section label to be able to investigate different code sections afterwards.

           Typically, this is called at multiple places inside the process's source code.
        """
        for thread in threading.enumerate(): 
            if isinstance(thread, ResourceMonitor) and getattr(thread, "_pid", None) == os.getpid():
                setattr(thread, "label", label)

    def __init__(self, *args, **kwargs):
        self._interval = kwargs.pop("interval", None) or 1.0
        self._pid = os.getpid()
        self._stop = threading.Event()

        super().__init__(*args, **kwargs)

    def run(self):
        csv_file = open(f"monitoring_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._pid}.csv", "w")
        csv_file.write("timestamp;step_name;cpu_usage;mem_usage;reads;writes\n")

        last_read_count = 0
        last_write_count = 0
        process = psutil.Process(self._pid)
        info = process.as_dict(attrs=["cpu_percent", "memory_percent", "io_counters"])  # just for initialization
        while not self._stop.wait(self._interval):
            label = getattr(self, "label", "XXXXXXXX")
            info = process.as_dict(attrs=["cpu_percent", "memory_percent", "io_counters"])
            cpu = info["cpu_percent"]
            memory = info["memory_percent"]
            io_counters = info["io_counters"]
            read_count = io_counters.read_chars  # _chars is linux specific, read_count could be of interest as well
            write_count = io_counters.write_chars  # _chars is linux specific, write_count could be of interest as well
            for child in process.children(recursive=True):
                try:
                    child_info = child.as_dict(attrs=["cpu_percent", "memory_percent", "io_counters"])
                    cpu += child_info["cpu_percent"]
                    memory += child_info["memory_percent"]
                    io_counters = child_info["io_counters"]
                    read_count += io_counters.read_chars  # _chars is linux specific, read_count could be of interest as well
                    write_count += io_counters.write_chars  # _chars is linux specific, write_count could be of interest as well
                except (psutil.NoSuchProcess, Exception):
                    pass  # too late to get info from this child process (ignore)
            res = ";".join(map(str, (datetime.datetime.utcnow(), \
                                    label, \
                                    cpu / psutil.cpu_count(), \
                                    memory, \
                                    max((read_count - last_read_count) / 1024 / 1024, 0), \
                                    max(write_count  - last_write_count) / 1024 / 1024, 0)))
            last_read_count = read_count
            last_write_count = write_count

            csv_file.write(f"{res}\n")
            csv_file.flush()
        csv_file.close()

    def stop(self):
        """Stop monitoring."""
        self._stop.set()
