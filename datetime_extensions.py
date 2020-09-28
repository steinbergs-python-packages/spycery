#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides extensions for datetime functionality."""

from datetime import datetime, time, timedelta


class DateTimeExtensions:
    """The DateTimeExtensions class."""

    @staticmethod
    def start_of_day(dtm):
        """Return the day's beginning datetime (e.g. 2017-02-17 00:00:00)."""
        return datetime.combine(dtm, time())

    @staticmethod
    def start_of_week(dtm):
        """Return the week's beginning datetime (Monday, e.g. 2017-02-13 00:00:00)."""
        start_of_day = DateTimeExtensions.start_of_day(dtm)
        return start_of_day - timedelta(days=start_of_day.weekday())

    @staticmethod
    def start_of_month(dtm):
        """Return the month's beginning datetime (e.g. 2017-02-01 00:00:00)."""
        return datetime.combine(dtm, time()).replace(day=1)

    @staticmethod
    def start_of_year(dtm):
        """Return the year's beginning datetime (e.g. 2017-01-01 00:00:00)."""
        return datetime.combine(dtm, time()).replace(day=1, month=1)

    @staticmethod
    def end_of_day(dtm):
        """Return the day's ending datetime (e.g. 2017-02-17 23:59:59)."""
        return datetime.combine(dtm, time(23, 59, 59))

    @staticmethod
    def end_of_week(dtm):
        """Return the week's ending datetime (Sunday, e.g. 2017-02-19 23:59:59)."""
        return DateTimeExtensions.start_of_week(dtm) + timedelta(days=7) - timedelta(seconds=1)

    @staticmethod
    def end_of_month(dtm):
        """Return the month's ending datetime (e.g. 2017-02-28 23:59:59)."""
        return datetime.combine(DateTimeExtensions.start_of_month(dtm) + timedelta(days=40), time()).replace(day=1) - timedelta(seconds=1)

    @staticmethod
    def end_of_year(dtm):
        """Return the year's ending datetime (e.g. 2017-12-31 23:59:59)."""
        return datetime.combine(DateTimeExtensions.start_of_year(dtm) + timedelta(days=400), time()).replace(day=1, month=1) - timedelta(seconds=1)
