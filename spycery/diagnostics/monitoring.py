#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functionality to monitor processes."""

# standard
from datetime import datetime
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
       To investigate single code sections later, it's possible to add labels at multiple places inside the process's source code.
    """

    @classmethod
    def tag(cls, name):
        """Set section label to be able to investigate different code sections afterwards.

           Typically, this is called at multiple places inside the process's source code.
        """
        for thread in threading.enumerate(): 
            if isinstance(thread, ResourceMonitor) and getattr(thread, "_pid", None) == os.getpid():
                thread.add_tag(name)

    def __init__(self, *args, **kwargs):
        self._destpath = kwargs.pop("destpath", None) or "."
        self._interval = kwargs.pop("interval", None) or 1.0
        self._pid = os.getpid()
        self._stop = threading.Event()
        self._lock_tags = threading.Lock()
        self._tags = []

        super().__init__(*args, **kwargs)

    def run(self):
        os.makedirs(f"{self._destpath}", exist_ok=True)
        csv_file = open(f"{self._destpath}/monitoring_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._pid}.csv", "w")
        csv_file.write("timestamp;tags;cpu_usage;mem_usage;reads;writes\n")

        last_read_count = 0
        last_write_count = 0
        cpu_count = psutil.cpu_count()
        process = psutil.Process(self._pid)
        info = process.as_dict(attrs=["cpu_percent", "memory_percent", "io_counters"])  # just for initialization
        self._stop.wait(0.1)

        while True:
            timestamp = datetime.utcnow()

            infos = [process.as_dict(attrs=["cpu_percent", "memory_percent", "io_counters"])]
            try:
                infos += [child.as_dict(attrs=["cpu_percent", "memory_percent", "io_counters"]) for child in process.children(recursive=True)]
            except (psutil.NoSuchProcess, Exception) as ex:
                pass  # too late to get info from child process(es), ignore

            cpu = memory = read_count = write_count = 0

            for info in infos:
                try:
                    cpu += info["cpu_percent"]
                    memory += info["memory_percent"]
                    io_counters = info["io_counters"]
                    read_count += io_counters.read_chars  # _chars is linux specific, read_count could be of interest as well
                    write_count += io_counters.write_chars  # _chars is linux specific, write_count could be of interest as well
                except Exception as ex:
                    pass  # too late to get info from process(es), ignore

            with self._lock_tags:
                res = ";".join(map(str, (timestamp, \
                                        "#".join([f"{tag['name']}@{str(tag['timestamp'])}" for tag in self._tags]), \
                                        cpu / cpu_count, \
                                        memory, \
                                        max((read_count - last_read_count) / 1024 / 1024, 0), \
                                        max((write_count  - last_write_count) / 1024 / 1024, 0))))
                self._tags = []  # refresh tagging

            last_read_count = read_count
            last_write_count = write_count

            csv_file.write(f"{res}\n")
            csv_file.flush()

            # wait until interval is reached
            interval = self._interval - (datetime.utcnow() - timestamp).total_seconds()
            # if interval < 0:
            #     csv_file.write(f"------------------------------------------------- we are too slow\n")
            if self._stop.wait(interval):
                break
        csv_file.close()

    def add_tag(self, name):
        """Add label including timestamp."""
        with self._lock_tags:
            tags = getattr(self, "_tags", None) or []
            tags.append({"timestamp": datetime.utcnow(), "name": name})
            setattr(self, "_tags", tags)

    def stop(self):
        """Stop monitoring."""
        self._stop.set()


# the diagram section

from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
from matplotlib import gridspec, ticker
logging.getLogger("matplotlib").setLevel(logging.WARNING)
import os
import pandas as pd

from spycery.extensions.plot_extensions import PyPlotExtensions as ppe


def create_diagram(filename, title=None):
    """Create diagram (PNG) from resource monitoring csv."""

    data = pd.read_csv(filename, sep=";", na_filter=False)

    fig = plt.figure(figsize=(12, 8), dpi=300)
    fig.suptitle(title or "Performance", fontsize=16)
    plt.rcParams.update({"font.size": 8})

    fig = plt.gcf()
    size = fig.get_size_inches() * fig.dpi  # size in pixels
    hh = [400 / size[0], 400 / size[0]]

    grid = gridspec.GridSpec(2, 1, height_ratios=hh)

    colors = ppe.categorical_colormap(10, 2, "tab10").colors

    xval = [(datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f") - datetime.strptime(data["timestamp"][0], "%Y-%m-%d %H:%M:%S.%f")).total_seconds() for value in data["timestamp"]]

    if not xval:  # no data no diagram
        return

    xval_step = int(max(1, min(xval[-1] / 10, 60)))  # TODO: set this to either 1, 5, 10 or 60 depending on max value

    # CPU/RAM diagram
    ax1 = plt.subplot(grid[0, 0])

    ax1.plot(xval, data["cpu_usage"], label="CPU", color=colors[0])
    ax1.plot(xval, data["mem_usage"], label="RAM", color=colors[1])

    ax1.xaxis.set_major_locator(ticker.FixedLocator(range(0, int(xval[-1] + xval_step), xval_step)))
    ax1.xaxis.set_major_formatter(ticker.NullFormatter())
    ax1.xaxis.set_minor_locator(plt.NullLocator())
    ax1.margins(x=0.0)
    ax1.grid()
    ax1.set_axisbelow(True)

    ax1.legend(loc="upper right")
    ax1.set_xlabel("")
    ax1.set_ylabel("CPU/RAM Usage [%]", rotation=90)

    # Disk I/O diagram
    ax2 = plt.subplot(grid[1, 0])

    ax2.plot(xval, data["reads"], label="reads", color=colors[2])
    ax2.plot(xval, data["writes"], label="writes", color=colors[3])

    ax2.xaxis.set_major_locator(ticker.FixedLocator(range(0, int(xval[-1] + xval_step), xval_step)))
    if xval_step >= 60:
        ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: (datetime(2020, 1, 1, 0, 0, 0) + timedelta(minutes=y/60)).strftime("%H:%M")))
    ax2.xaxis.set_minor_locator(plt.NullLocator())
    ax2.margins(x=0.0)
    ax2.grid()
    ax2.set_axisbelow(True)

    ax2.legend(loc="upper right")
    ax2.set_xlabel("Time [sec]" if xval_step < 60 else "Time [min]", loc="right")
    ax2.set_ylabel("Disk I/O [MB]", rotation=90)

    # second x axis to display sections
    newlabels = []
    newticks = []
    lastts = 0
    for i, tags in enumerate(data["tags"]):
        entries = str(tags).split("#")
        for entry in entries:
            label, timestamp = entry.split("@", maxsplit=1) if "@" in entry else (entry, data["timestamp"][i])
            if label:
                ts = max((datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f") - datetime.strptime(data["timestamp"][0], "%Y-%m-%d %H:%M:%S.%f")).total_seconds(), 0)
                if (ts - lastts) < 1 and newlabels:  # if entries are too close, combine them as one
                    newlabels[-1] += "\n" + label
                else:
                    newticks.append(ts)
                    newlabels.append(label)
                    lastts = ts

    secax = ax2.secondary_xaxis("bottom")
    secax.set_xlim(ax2.get_xlim())
    secax.tick_params(length=35)
    secax.set_ticks(newticks)
    secax.xaxis.set_ticklabels(newlabels, ma="right", rotation=90)

    # place a text box in upper left in axes coords
    import platform
    import psutil
    uname = platform.uname()
    svmem = psutil.virtual_memory()
    info = \
        f"System:    {uname.system}\n" \
        f"Release:   {uname.release}\n" \
        f"Processor: {uname.processor}\n" \
        f"CPU(s):    {psutil.cpu_count(logical=False)} ({psutil.cpu_count(logical=True)})\n" \
        f"Frequency: {psutil.cpu_freq().current:.2f}Mhz\n" \
        f"Memory:    {int(svmem.total / 1024 / 1024 / 1024 + 0.5)}GB"

    props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)
    ax1.text(0.01, 0.95, info, transform=ax1.transAxes, verticalalignment="top", family="monospace", bbox=props)

    fig.align_xlabels()
    fig.align_ylabels()
    fig.tight_layout(pad=2.0, h_pad=1.0, w_pad=1.0)

    fig.savefig(f"{os.path.splitext(filename)[0]}.png")
