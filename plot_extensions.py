#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides extensions for pyplot functionality."""

# standard
from datetime import timedelta

# 3rd party
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.dates as dates
import matplotlib.ticker as ticker
import numpy as np


def regression_xy(x, y, deg=1):
    """Calculate regression of y values over x values."""
    xi = np.arange(len(x))
    fit = np.polyfit(xi, y, deg=min(deg, len(x) - 1))
    fit_fn = np.poly1d(fit)
    return fit_fn(xi)


def sort_xy(x, y, index=None, order=None):
    """Sort x, y arrays by either x or y.

        :param x: array of x values
        :param y: array of y values
        :param index: sorting index (=0 sort by x, =1 sort by y)
        :param order: sorting order (=0 ascending, =1 descending)
    """
    if index in (0, 1):
        s = sorted(zip(x, y), key=lambda pair: pair[index], reverse=True if (order or 0) > 0 else False)
        return zip(*s)

    return x, y


class PyPlotExtensions:
    """The PyplotExtensions class."""

    @staticmethod
    def categorical_colormap(num_categories, num_colors, cmap="tab10"):
        """Generate a categorical colormap."""
        if num_categories > plt.get_cmap(cmap).N:
            raise ValueError("Too many categories for colormap.")
        ccolors = plt.get_cmap(cmap)(np.arange(num_categories, dtype=int))
        cols = np.zeros((num_categories * num_colors, 3))
        for i, c in enumerate(ccolors):
            chsv = colors.rgb_to_hsv(c[:3])
            arhsv = np.tile(chsv, num_colors).reshape(num_colors, 3)
            arhsv[:, 1] = np.linspace(chsv[1], 0.25, num_colors)
            arhsv[:, 2] = np.linspace(chsv[2], 1, num_colors)
            rgb = colors.hsv_to_rgb(arhsv)
            cols[i * num_colors:(i + 1) * num_colors, :] = rgb
        cmap = colors.ListedColormap(cols)
        return cmap

    @staticmethod
    def plot_grid(ax, **kwargs):
        """Plot a grid.

            :param ax:

            :param **kwargs: Arbitrary list of keyword arguments
                    xtick_major:
                    ytick_major:
                    xlabel_rot:
        """
        xtick_major = int(kwargs.pop("xtick_major", "0"))
        ytick_major = int(kwargs.pop("ytick_major", "0"))
        xlabel_rot = kwargs.pop("xlabel_rot", None)
        assert not kwargs, "Unknown arguments: %r" % kwargs

        plt.setp(ax.xaxis.get_label(), visible=True)
        plt.setp(ax.get_xticklabels(), visible=True, rotation=xlabel_rot, ha="center")

        if xtick_major > 0:
            ax.xaxis.set_major_locator(ticker.IndexLocator(xtick_major, 0))
            ax.xaxis.set_minor_locator(plt.NullLocator())
        if ytick_major > 0:
            ax.yaxis.set_major_locator(ticker.IndexLocator(ytick_major, 0))
            ax.yaxis.set_minor_locator(plt.NullLocator())

        ax.margins(x=0.0)
        ax.grid()
        ax.set_axisbelow(True)

    @staticmethod
    def plot_line_chart(ax, x, y, **kwargs):
        """Plot a line chart.

            :param ax: The subplot.
            :param x: The x axis data.
            :param y: The y axis data.

            :param **kwargs: Arbitrary list of keyword arguments (see pyplot.plot's kwargs for more)
                    sort_index: The sorting index (=0 sort data by x, =1 sort data by y).
                    sort_order: The sorting order (=0 ascending, =1 descending).
        """
        sort_index = kwargs.pop("sort_index", None)
        sort_order = kwargs.pop("sort_order", None)
        # the rest is passed to pyplot.plot
        # assert not kwargs, "Unknown arguments: %r" % kwargs

        x, y = sort_xy(x, y, sort_index, sort_order)

        xa = np.arange(len(x))
        ax.plot(xa, y, **kwargs)

        # set xtick labels properly according to stepsize
        loc = ax.xaxis.get_major_locator()
        stepsize = max(int(loc()[1] - loc()[0]), 1) if len(loc()) > 1 else 1
        ax.set_xticks(xa[::stepsize])
        ax.set_xticklabels(x[::stepsize])

        ax.legend()

    @staticmethod
    def plot_bar_chart(ax, x, y, **kwargs):
        """Plot a bar chart.

            :param ax: The subplot.
            :param x: The x axis data.
            :param y: The y axis data.

            :param **kwargs: Arbitrary list of keyword arguments (see pyplot.plot's kwargs for more)
                    sort_index: The sorting index (=0 sort data by x, =1 sort data by y).
                    sort_order: The sorting order (=0 ascending, =1 descending).
                    regression: Used to plot a regression curve (=1 linear, >1 polynomial)
        """
        sort_index = kwargs.pop("sort_index", None)
        sort_order = kwargs.pop("sort_order", None)
        regression = kwargs.pop("regression", None) or 0
        align = kwargs.pop("align", "center")  # specific defaults
        alpha = kwargs.pop("alpha", 1.0 if regression < 1 else 0.75)  # specific defaults
        # the rest is passed to pyplot.plot
        # assert not kwargs, "Unknown arguments: %r" % kwargs

        x, y = sort_xy(x, y, sort_index, sort_order)

        xa = np.arange(len(x))
        rects = ax.bar(xa, y, align=align, alpha=alpha, **kwargs)

        # set xtick labels properly according to stepsize
        loc = ax.xaxis.get_major_locator()
        stepsize = max(int(loc()[1] - loc()[0]), 1) if len(loc()) > 1 else 1
        ax.set_xticks(xa[::stepsize])
        ax.set_xticklabels(x[::stepsize])

        ax.legend()

        if regression >= 1:
            reg = regression_xy(xa, y, regression)

            kwargs.pop("label", None)  # hide label for regression line
            kwargs.pop("width", None)

            # align regression curve to bar xcenter
            xr = [rect.get_width() / 2 for rect in rects]
            ax.plot(xa + xr, reg, label=None, **kwargs)

            ax.annotate("{:.2f}".format(reg[0]),
                        xy=(xa[0] + xr[0], reg[0]),
                        xytext=(-15, 0), textcoords="offset points",
                        horizontalalignment="center", verticalalignment="center",
                        arrowprops=None)

            ax.annotate("{:.2f}".format(reg[-1]),
                        xy=(xa[-1] + xr[-1], reg[-1]),
                        xytext=(15, 0), textcoords="offset points",
                        horizontalalignment="center", verticalalignment="center",
                        arrowprops=None)

    @staticmethod
    def plot_timeline(ax, timeline_start, start_date, duration, timeline_end=None, **kwargs):
        """Plot a timeline chart.

            :param ax: The subplot.
            :param timeline_start: The date to start the timeline from.
            :param timeline_end: The date to end the timeline (if None it is set automatically).
            :param start_date: The date where work starts.
            :param duration: The duration of the work (in days).

            :param **kwargs: Arbitrary list of keyword arguments
                    xlabel_rot: The rotation degree of x-axis tick label.
                    color: The color of the timeline bar.
        """
        xlabel_rot = kwargs.pop("xlabel_rot", None)
        color = kwargs.pop("color", None)
        assert not kwargs, "Unknown arguments: %r" % kwargs

        ax.xaxis_date()
        ax.xaxis.set_major_formatter(dates.DateFormatter("%Y-%m-%d"))
        # ax.xaxis.set_minor_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(ticker.MultipleLocator(7))  # major tick every week
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))  # minor tick every day
        ax.yaxis.set_major_locator(plt.NullLocator())

        plt.setp(ax.xaxis.get_label(), visible=True)
        plt.setp(ax.get_xticklabels(), visible=True, rotation=xlabel_rot, ha="center")

        begin = np.array([start_date.date().toordinal()])
        end = np.array([(start_date + timedelta(days=duration)).date().toordinal()])

        ax.barh(0, end - begin + 1, left=begin, align="center", color=color)

        # set limits (timeline from start to end or auto mode)
        ax.set_xlim(timeline_start, ax.get_xlim()[1] if timeline_end is None else timeline_end)

    @staticmethod
    def plot_timeline_multi(ax, timeline_start, task_list, timeline_end=None, **kwargs):
        """Plot a multiple timeline chart.

            :param ax: The subplot.
            :param timeline_start: The date to start the timeline from.
            :param timeline_end: The date to end the timeline (if None it is set automatically).
            :param task_list: A list of tuples (group, label, start_date, duration) where duration is in days.

            :param **kwargs: Arbitrary list of keyword arguments
                    xlabel_rot: The rotation degree of x-axis tick label.
                    color: The color of the timeline bars (can also be an array/list).
                           Tasks of the same group/category are colored the same.
        """
        xlabel_rot = kwargs.pop("xlabel_rot", None)
        color = kwargs.pop("color", None)
        assert not kwargs, "Unknown arguments: %r" % kwargs

        ax.xaxis_date()
        ax.xaxis.set_major_formatter(dates.DateFormatter("%Y-%m-%d"))
        # ax.xaxis.set_minor_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(ticker.MultipleLocator(7))  # major tick every week
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))  # minor tick every day
        ax.yaxis.set_major_locator(plt.NullLocator())

        plt.setp(ax.xaxis.get_label(), visible=True)
        plt.setp(ax.get_xticklabels(), visible=True, rotation=xlabel_rot, ha="center")

        groups = [group for group, _, _, _ in task_list]
        begin = np.array([start_date.date().toordinal() for _, _, start_date, _ in task_list])
        end = np.array([(start_date + timedelta(days=duration)).date().toordinal() for _, _, start_date, duration in task_list])

        # building color categories based on groups
        categories = None
        if color is not None:
            cd = {}
            for group in groups:
                if group not in cd:
                    cd[group] = len(cd)
            categories = [color[cd[group]] for group in groups] if not np.isscalar(color) else color

        # plot tasks
        rects = ax.barh(groups, end - begin + 1, left=begin, align="center", color=categories)

        # labeling
        labels = [label for _, label, _, _ in task_list]
        for rect, label in zip(rects, labels):
            ax.text(rect.get_x() + rect.get_width() / 2,
                    rect.get_y() + rect.get_height() / 2,
                    label,
                    ha="center", va="center", color="white")

        # need unique values for yticks
        groups = list(dict.fromkeys(groups))
        plt.yticks(np.arange(len(groups)), groups)

        # set limits (timeline from start to end or auto mode, y-axis inversed to show groups in the original order)
        ax.set_xlim(timeline_start, ax.get_xlim()[1] if timeline_end is None else timeline_end)
        ax.set_ylim(ax.get_ylim()[::-1])
        ax.tick_params(axis="y", which="both", length=0)

        ax.xaxis.grid()
        ax.set_axisbelow(True)
