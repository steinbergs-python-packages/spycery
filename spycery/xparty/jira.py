#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functionality for JIRA interaction."""

from datetime import datetime, timedelta
import json
import logging
import requests
import requests_toolbelt
import urllib.parse

from spycery.extensions.datetime_extensions import DateTimeExtensions as dte


class Jira(object):
    """The Jira class.

       Provides helpful methods using jira rest api.

       Example:

       session = Jira(<url with scheme>, <username>, <password>)
       session.get_number_of_issues("Reporter = currentUser()")
    """

    def __init__(self, server, username, password):
        """Construct a new instance.

            :param server: The JIRA server URL to be accessed. Should include the scheme as well.
            :param user: The user name.
            :param password: The password.
        """
        self.agile = "rest/agile/1.0"
        self.api = "rest/api/2"
        self.server = server
        self.authentication = requests.auth.HTTPBasicAuth(username, password)
        self.headers = {"Accept": "application/json", "Content-type": "application/json"}
        self.methods = {"GET", "POST", "PUT", "DELETE"}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("__init__(\"%s\", \"%s\", \"%s\")", server, "XXXXXXXX", "XXXXXXXX")

    def _make_request(self, method, path="", **kwargs):
        """Make a request call to path.

            :param path: The request path.
            :param method: The request method ("GET", "POST", "PUT").

            :param **kwargs: Arbitrary list of keyword arguments (see also requests module)
                    headers: Optional request headers.
                    data: Optional data.

            :returns: Json data
        """
        if (method is None) or (method not in self.methods):
            self.logger.debug("request failed. method %s not supported", method)
            return {"error": "method {0} not supported".format(method)}

        headers = kwargs.pop("headers", {})
        data = kwargs.pop("data", None)

        result = {}

        try:
            headers = {**self.headers, **headers}
            response = requests.request(method,
                                        "{0}/{1}".format(self.server, path),
                                        auth=self.authentication,
                                        headers=headers,
                                        data=data,
                                        **kwargs)
            response.raise_for_status()
            result = {} if not response.text else response.json()
        except requests.exceptions.RequestException as ex:
            self.logger.debug("request failed. %s", ex)
            return {"error": ex}

        return result

    def _get_data(self, path="", **kwargs):
        """Get data from path.

            :param path: The path to get data from.

            :param **kwargs: Arbitrary list of keyword arguments

            :returns: Json data
        """
        return self._make_request(method="GET", path=path, **kwargs)

    def _post_data(self, path="", data=None, **kwargs):
        """Post data to path.

            :param path: The path to post data to.

            :param **kwargs: Arbitrary list of keyword arguments

            :returns: Json data
        """
        return self._make_request(method="POST", path=path, data=data, **kwargs)

    def _put_data(self, path="", data=None, **kwargs):
        """Put data to path.

            :param path: The path to put data to.

            :param **kwargs: Arbitrary list of keyword arguments

            :returns: Json response
        """
        return self._make_request(method="PUT", path=path, data=data, **kwargs)

    def _delete_data(self, path="", **kwargs):
        """Delete data from path.

            :param path: The path to delete data from.

            :param **kwargs: Arbitrary list of keyword arguments

            :returns: Json response
        """
        return self._make_request(method="DELETE", path=path, **kwargs)

    def get_boards(self):
        """Return the list of all boards.

            :returns: The list of all boards.
        """
        boards = []
        i = 0
        while True:
            response = self._get_data(self.agile + "/board?startAt={0}".format(i))
            if not response:
                break
            values = response.get("values") or []
            values_read = len(values)
            boards = [*boards, *values]
            if (values_read < 1) or (response["isLast"] is True):
                break
            i += values_read
        return boards

    def get_projects(self, board_id):
        """Return the list of projects of given board.

            :param board_id: The board id.

            :returns: The list of the board's projects.
        """
        projects = []
        i = 0
        while True:
            response = self._get_data(self.agile + "/board/{0}/project?startAt={1}".format(board_id, i))
            if not response:
                break
            values = response.get("values") or []
            values_read = len(values)
            projects = [*projects, *values]
            if (values_read < 1) or (response["isLast"] is True):
                break
            i += values_read
        return [project["key"] for project in projects]

    def get_sprints(self, board_id):
        """Return the list of sprints of given board.

            :param board_id: The board id.

            :returns: The list of the board's sprints.
        """
        sprints = []
        i = 0
        while True:
            response = self._get_data(self.agile + "/board/{0}/sprint?startAt={1}".format(board_id, i))
            if not response:
                break
            values = response.get("values") or []
            values_read = len(values)
            sprints = [*sprints, *values]
            if (values_read < 1) or (response["isLast"] is True):
                break
            i += values_read
        return [sprint for sprint in sprints if sprint["originBoardId"] == board_id]

    def get_issues(self, search_mask="", index=0, count=1000, fields=None, expand=None):
        """Return the list of issue data matching the search mask (JQL string).

            :param str search_mask: The JQL string used to search for issues.
            :param int index: The index to start from.
            :param int count: The max count of issues to be returned.
            :param str fields: Comma separated list of fields to be returned.

            :returns: The list of issue data.
        """
        self.logger.debug("get_issues(\"%s\", \"%s\", \"%s\", \"%s\", \"%s\")", search_mask, index, count, fields, expand)

        path = self.api + "/search?jql={0}&startAt={1}&maxResults={2}&fields={3}&expand={4}"
        response = self._get_data(path.format(urllib.parse.quote_plus(search_mask or ""),
                                              index or 0,
                                              count or 0,
                                              urllib.parse.quote_plus(fields or ""),
                                              urllib.parse.quote_plus(expand or "")))
        return response

    def get_all_issues(self, search_mask="", fields=None, expand=None):
        """Return the list of all issue data matching the search mask (JQL string).

            :param str search_mask: The JQL string used to search for issues.
            :param str fields: Comma separated list of fields to be returned.

            :returns: The list of all issue data.
        """
        number_of_issues = self.get_issues(search_mask=search_mask, index=None, count=None)["total"]

        issues = []
        # visit all issues in blocks of 1000 (there's no way to get them all at once)
        issues_per_page = 1000
        i = 0
        while i < number_of_issues:
            result = self.get_issues(search_mask=search_mask,
                                     index=i,
                                     count=min(issues_per_page, number_of_issues - i),
                                     fields=fields,
                                     expand=expand)

            issues = [*issues, *result.get("issues", [])]
            i += len(result.get("issues", []))

        return issues

    def get_number_of_issues(self, search_mask=""):
        """Return the number of issues matching the search mask (JQL string).

            :param str search_mask: The JQL string used to search for issues.

            :returns: The number of issues found.
            :rtype: int
        """
        self.logger.debug("get_number_of_issues(\"%s\")", search_mask)

        # get total number of issues
        number_of_issues = self.get_issues(search_mask=search_mask, index=None, count=None)["total"]

        return number_of_issues

    def get_issues_creation(self, search_mask="", start_date=datetime.min, end_date=datetime.max):
        """Return the creation of issues matching the search mask (JQL string).

            :param str search_mask: The JQL string used to search for issues.
            :param date start_date: The start date to search for logged work.
            :param date end_date: The end date to search for logged work.

            :returns: The creation dictionary with key=creator and value=number_of_issues_created.
            :rtype: dict(string, int)
        """
        self.logger.debug("get_issues_creation(\"%s\", \"%s\", \"%s\")", search_mask, start_date, end_date)

        issues_creation = {}

        # get total number issues
        number_of_issues = self.get_issues(search_mask=search_mask, index=None, count=None)["total"]

        self.logger.debug("searching inside of %i issues", number_of_issues)

        # visit all issues in blocks of 1000 (there's no way to get them all at once)
        issues_per_page = 1000
        i = 0
        while i < number_of_issues:
            list_of_issues = self.get_issues(search_mask=search_mask,
                                             index=i,
                                             count=min(issues_per_page, number_of_issues - i),
                                             fields="key, created, reporter")

            for issue in list_of_issues["issues"]:
                if "reporter" not in issue["fields"] or not issue["fields"]["reporter"]:
                    pass
                elif issue["fields"]["reporter"].get("emailAddress") is not None:
                    created = datetime.strptime(issue["fields"]["created"].split("T")[0], "%Y-%m-%d")  # T%H:%M:%S.%f")
                    if (created >= start_date) and (created <= end_date):
                        issues_creation.setdefault((issue["fields"]["reporter"]["emailAddress"]).split("@")[0].lower(), []).append(1)
                i += 1
        return {k: sum(v) for k, v in issues_creation.items()}

    def get_issues_worklog(self, search_mask="", start_date=datetime.min, end_date=datetime.max):
        """Return the worklog of issues matching the search mask (JQL string).

            :param str search_mask: The JQL string used to search for issues.
            :param date start_date: The start date to search for logged work.
            :param date end_date: The end date to search for logged work.

            :returns: The worklog dictionary with key=author and value=hours.
            :rtype: dict(string, float)
        """
        self.logger.debug("get_issues_worklog(\"%s\", \"%s\", \"%s\")", search_mask, start_date, end_date)

        issues_worklog = {}

        # get total number issues
        number_of_issues = self.get_issues(search_mask=search_mask, index=None, count=None)["total"]

        self.logger.debug("searching inside of %i issues", number_of_issues)

        # visit all issues in blocks of 1000 (there's no way to get them all at once)
        issues_per_page = 1000
        i = 0
        while i < number_of_issues:
            list_of_issues = self.get_issues(search_mask=search_mask,
                                             index=i,
                                             count=min(issues_per_page, number_of_issues - i),
                                             fields="key, worklog")

            for issue in list_of_issues["issues"]:
                for worklog in issue["fields"]["worklog"]["worklogs"]:
                    if worklog["author"].get("emailAddress") is not None:
                        updated = datetime.strptime(worklog["updated"].split("T")[0], "%Y-%m-%d")  # T%H:%M:%S.%f")
                        if (updated >= start_date) and (updated <= end_date):
                            issues_worklog.setdefault((worklog["author"]["emailAddress"]).split("@")[0].lower(), []).append(worklog["timeSpentSeconds"])
                i += 1
        return {k: sum(v) / 3600 for k, v in issues_worklog.items()}

    def get_period_issuecreation(self, search_mask="", time_slot_in_weeks=1, num_time_slots=12, include_current_time_slot=False, users=None):
        """Return the creation of issues matching the search mask (JQL string) within given time slots.

            :param str search_mask: The JQL string used to search for issues.
            :param int time_slot_in_weeks: The start date to search for logged work.
            :param int num_time_slots: The end date to search for logged work.

            :returns: The creation dictionary with key=creator and value=number_of_issues_created.
            :rtype: dict(string, float)
        """
        self.logger.debug("get_period_issuecreation(\"%s\", \"%s\", \"%s\", \"%s\", \"%s\")", search_mask, time_slot_in_weeks, num_time_slots, include_current_time_slot, users)

        logged_users = []
        period_worklog = {}

        if time_slot_in_weeks > 0:
            finish_date = dte.start_of_week(datetime.now())
            start_date = dte.start_of_week(finish_date - timedelta(days=time_slot_in_weeks * 7) * num_time_slots)
            end_date = dte.end_of_week(start_date + timedelta(days=time_slot_in_weeks * 7 - 7))

            if not include_current_time_slot:
                finish_date = dte.end_of_week(finish_date - timedelta(seconds=1))
        else:
            finish_date = dte.start_of_day(datetime.now())
            start_date = dte.start_of_day(finish_date - timedelta(days=1) * num_time_slots)
            end_date = dte.end_of_day(start_date + timedelta(days=0))

            if not include_current_time_slot:
                finish_date = dte.end_of_day(finish_date - timedelta(seconds=1))

        issues = self.get_all_issues(search_mask=search_mask, fields="key, created, reporter")

        while start_date <= finish_date:

            # using get_issues_creation might be too slow, that's why we fetch all issues once (above) and get the relevant data below
            # issues_worklog = self.get_issues_creation(search_mask=search_mask, start_date=start_date, end_date=end_date)

            issues_worklog = {}
            for issue in issues:
                if "reporter" not in issue["fields"] or not issue["fields"]["reporter"]:
                    pass
                elif issue["fields"]["reporter"].get("emailAddress") is not None:
                    created = datetime.strptime(issue["fields"]["created"].split("T")[0], "%Y-%m-%d")  # T%H:%M:%S.%f")
                    if (created >= start_date) and (created <= end_date):
                        issues_worklog.setdefault((issue["fields"]["reporter"]["emailAddress"]).split("@")[0].lower(), []).append(1)
            issues_worklog = {k: sum(v) for k, v in issues_worklog.items()}

            logged_users.extend([user for user in issues_worklog if user not in logged_users])

            # making period name unique
            period_name = "{} ({}, {})".format("period", start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

            # build statistic
            period_worklog[period_name] = {}
            for user in (users or issues_worklog):
                period_worklog[period_name][user] = issues_worklog[user] if user in issues_worklog else 0

            # start of next period
            if time_slot_in_weeks > 0:
                start_date = dte.start_of_week(end_date + timedelta(seconds=1))
                end_date = dte.end_of_week(start_date + timedelta(days=time_slot_in_weeks * 7 - 7))
            else:
                start_date = dte.start_of_day(end_date + timedelta(seconds=1))
                end_date = dte.end_of_day(start_date + timedelta(days=0))

        # fill gaps
        if not users:
            for period_name in period_worklog:
                for user in logged_users:
                    if user not in period_worklog[period_name]:
                        period_worklog[period_name][user] = 0

        return period_worklog

    def get_period_worklog(self, search_mask="", time_slot_in_weeks=1, num_time_slots=12, include_current_time_slot=False, users=None):
        """Return the worklog of issues matching the search mask (JQL string) within given time slots.

            :param str search_mask: The JQL string used to search for issues.
            :param int time_slot_in_weeks: The start date to search for logged work.
            :param int num_time_slots: The end date to search for logged work.

            :returns: The worklog dictionary with key=author and value=hours.
            :rtype: dict(string, float)
        """
        self.logger.debug("get_period_worklog(\"%s\", \"%s\", \"%s\", \"%s\", \"%s\")", search_mask, time_slot_in_weeks, num_time_slots, include_current_time_slot, users)

        logged_users = []
        period_worklog = {}

        if time_slot_in_weeks > 0:
            finish_date = dte.start_of_week(datetime.now())
            start_date = dte.start_of_week(finish_date - timedelta(days=time_slot_in_weeks * 7) * num_time_slots)
            end_date = dte.end_of_week(start_date + timedelta(days=time_slot_in_weeks * 7 - 7))

            if not include_current_time_slot:
                finish_date = dte.end_of_week(finish_date - timedelta(seconds=1))
        else:
            finish_date = dte.start_of_day(datetime.now())
            start_date = dte.start_of_day(finish_date - timedelta(days=1) * num_time_slots)
            end_date = dte.end_of_day(start_date + timedelta(days=0))

            if not include_current_time_slot:
                finish_date = dte.end_of_day(finish_date - timedelta(seconds=1))

        issues = self.get_all_issues(search_mask=search_mask, fields="key, worklog")

        while start_date <= finish_date:

            # using get_issues_worklog might be too slow, that's why we fetch all issues once (above) and get the relevant data below
            # issues_worklog = self.get_issues_worklog(search_mask=search_mask, start_date=start_date, end_date=end_date)

            issues_worklog = {}
            for issue in issues:
                for worklog in issue["fields"]["worklog"]["worklogs"]:
                    if worklog["author"].get("emailAddress") is not None:
                        updated = datetime.strptime(worklog["updated"].split("T")[0], "%Y-%m-%d")  # T%H:%M:%S.%f")
                        if (updated >= start_date) and (updated <= end_date):
                            issues_worklog.setdefault((worklog["author"]["emailAddress"]).split("@")[0].lower(), []).append(worklog["timeSpentSeconds"])
            issues_worklog = {k: sum(v) / 3600 for k, v in issues_worklog.items()}

            logged_users.extend([user for user in issues_worklog if user not in logged_users])

            # making period name unique
            period_name = "{} ({}, {})".format("period", start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

            # build statistic
            period_worklog[period_name] = {}
            for user in (users or issues_worklog):
                period_worklog[period_name][user] = issues_worklog[user] if user in issues_worklog else 0.0

            # start of next period
            if time_slot_in_weeks > 0:
                start_date = dte.start_of_week(end_date + timedelta(seconds=1))
                end_date = dte.end_of_week(start_date + timedelta(days=time_slot_in_weeks * 7 - 7))
            else:
                start_date = dte.start_of_day(end_date + timedelta(seconds=1))
                end_date = dte.end_of_day(start_date + timedelta(days=0))

        # fill gaps
        if not users:
            for period_name in period_worklog:
                for user in logged_users:
                    if user not in period_worklog[period_name]:
                        period_worklog[period_name][user] = 0.0

        return period_worklog

    def get_sprint_worklog(self, board, users=None):
        """Return the worklog of all completed sprints within a board.

            :param str board: The board name to search for logged work.
            :param users: The list of users (lowercase, e.g. "prename.surname") to search for logged work.

            :returns: The nested worklog dictionary with key1=sprint key2=author and value=hours.
            :rtype: dict(dict(string, float))
        """
        self.logger.debug("get_sprint_worklog(\"%s\", \"%s\")", board, users)

        # find the board id
        board_id = -1
        boards = self.get_boards()

        for bd in boards:
            if bd["name"] == board:
                board_id = bd["id"]
                break

        if board_id == -1:
            self.logger.debug("board name unknown or not found.")
            return {}

        logged_users = []
        worklog = {}

        # Get the sprints in specific board
        sprints = self.get_sprints(board_id)

        # Get the worklogs of each sprint
        for sprint in sprints:
            if sprint["state"] == "future":
                continue

            issues_worklog = self.get_issues_worklog(search_mask="sprint=%d" % sprint["id"],
                                                     start_date=datetime.strptime(sprint["startDate"].split("T")[0], "%Y-%m-%d"),  # T%H:%M:%S.%f"),
                                                     end_date=datetime.strptime(sprint["endDate"].split("T")[0], "%Y-%m-%d"))  # T%H:%M:%S.%f"))

            logged_users.extend([user for user in issues_worklog if user not in logged_users])

            # making sprint name unique
            sprint_name = "{} {} ({}, {})".format(board, sprint["name"], sprint["startDate"].split("T")[0], sprint["endDate"].split("T")[0])

            # build sprint statistic
            worklog[sprint_name] = {}
            for user in (users or issues_worklog):
                worklog[sprint_name][user] = issues_worklog[user] if user in issues_worklog else 0.0

        # fill gaps
        if not users:
            for sprint_name in worklog:
                for user in logged_users:
                    if user not in worklog[sprint_name]:
                        worklog[sprint_name][user] = 0.0

        return worklog

    def get_sprint_report(self, board_id, sprint_id):
        """Return the sprint report of given board and sprint.

            :param board_id: The board id.
            :param sprint_id: The sprint id.

            :returns: The list of issues touched during sprint.
            :rtype: list(dict(key, summary, type, priority, status, planned, removed))
        """
        issue_stats = []

        try:
            response = self._get_data("rest/greenhopper/latest/rapid/charts/sprintreport?rapidViewId={0}&sprintId={1}".format(board_id, sprint_id))
        except requests.exceptions.RequestException as ex:
            self.logger.debug("request failed. %s", ex)
            return issue_stats

        status_map = {"1": "Open", "3": "In Progress", "4": "Reopened", "5": "Resolved", "6": "Closed", "10000": "Backlog", "10002": "Done", "10100": "Under Test", "10609": "In Review"}
        type_map = {"1": "Bug", "2": "New Feature", "3": "Task", "4": "Improvement", "10000": "Epic", "10001": "Story", "10402": "Second Source"}

        # completed_issues = [*response["contents"]["completedIssues"], *response["contents"]["issuesCompletedInAnotherSprint"]]

        #for key in response["contents"]["entityData"]["statuses"]:
        #    print(key, response["contents"]["entityData"]["statuses"][key]["statusName"])
        #for key in response["contents"]["entityData"]["types"]:
        #    print(key, response["contents"]["entityData"]["types"][key]["typeName"])
        for content in response["contents"]:
            if content in ["completedIssues", "issuesNotCompletedInCurrentSprint", "puntedIssues"]:
                for issue in response["contents"][content]:
                    # some issue types are new, tbd if they should occur in stat report
                    if issue["typeId"] not in type_map:
                        # print(issue)
                        pass
                    if type_map.get(issue["typeId"], None) == "Epic":
                        continue

                    issue_stats.append({"key": issue["key"],
                                        "summary": issue["summary"],
                                        #"type": issue.get("typeName", None),  # typeName is not available anymore
                                        "type": type_map.get(issue["typeId"], issue["typeId"]),
                                        "priority": issue.get("priorityName"),  # TODO: priorityName is not available anymore
                                        #"status": issue["status"]["name"],   # statusName is not available anymore
                                        "status": status_map[issue["statusId"]],
                                        "planned": False if issue["key"] in response["contents"]["issueKeysAddedDuringSprint"] else True,
                                        "removed": True if issue in response["contents"]["puntedIssues"] else False})
        return issue_stats

    def get_sprint_reports(self, board):
        """Return the reports of all sprints within a board.

            :param str board: The board name to search for.

            :returns: The statistic dictionary with key=sprint and value=issues.
            :rtype: dict(sprint, issues)
        """
        self.logger.debug("get_sprint_reports(\"%s\")", board)

        # find the board id
        board_id = -1
        boards = self.get_boards()

        for bd in boards:
            if bd["name"] == board:
                board_id = bd["id"]
                break

        if board_id == -1:
            self.logger.debug("board name unknown or not found.")
            return {}

        report = {}

        # Get the sprints in specific board
        sprints = self.get_sprints(board_id)

        # Get the worklogs of each sprint
        for sprint in sprints:
            if sprint["state"] == "future":
                continue

            # making sprint name unique
            sprint_name = "{} {} ({}, {})".format(board, sprint["name"], sprint["startDate"].split("T")[0], sprint["endDate"].split("T")[0])

            # build sprint statistic
            report[sprint_name] = {"issues": self.get_sprint_report(board_id, sprint["id"])}

        return report

    def get_issues_remaining_estimate(self, search_mask="", **kwargs):
        """Return the remaining time estimate of issues matching the search mask (JQL string).

            :param str search_mask: The JQL string used to search for issues.
            :param **kwargs: Arbitrary list of keyword arguments
                    estimate_unestimated: Used to estimate unestimated issues (True or False, default is False).
                    time_unit: The unit to present remaining time ("hours", "days", default is "hours").

            :returns: The remaining time estimate.
            :rtype: float
        """
        estimate_unestimated = kwargs.pop("estimate_unestimated", False)
        time_unit = kwargs.pop("time_unit", "hours")

        self.logger.debug("get_issues_remaining_estimate(\"%s\")", search_mask)

        assert not kwargs, "Unknown arguments: %r" % kwargs

        # get total number issues
        number_of_issues = self.get_issues(search_mask=search_mask, index=None, count=None)["total"]

        self.logger.debug("searching inside of %i issues", number_of_issues)

        issues_unestimated = []
        sum_of_remaining_time = 0

        time_unit_factor = 1. / 3600
        if time_unit == "days":
            time_unit_factor = 1. / 3600 / 8
        elif time_unit == "weeks":
            time_unit_factor = 1. / 3600 / 40
        else:
            time_unit = "hours"  # default

        # visit all issues in blocks of 1000 (there's no way to get them all at once)
        issues_per_page = 1000
        i = 0
        while i < number_of_issues:
            list_of_issues = self.get_issues(search_mask=search_mask,
                                             index=i,
                                             count=min(issues_per_page, number_of_issues - i),
                                             fields="key, summary, timeoriginalestimate, timetracking")

            for issue in list_of_issues["issues"]:
                original_time = int(issue["fields"].get("timeoriginalestimate") or 0)
                remaining_time = int(issue["fields"]["timetracking"].get("remainingEstimateSeconds") or 0)
                if (remaining_time <= 0) or (original_time <= 0):
                    issues_unestimated.append(issue["key"])
                sum_of_remaining_time += remaining_time
                self.logger.debug("%s;%s;%.2f;%.2f", issue["key"], issue["fields"]["summary"], original_time * time_unit_factor, remaining_time * time_unit_factor)
                i += 1

        sum_of_remaining_time = sum_of_remaining_time * time_unit_factor
        if estimate_unestimated:  # estimate the unestimated
            sum_of_remaining_time += len(issues_unestimated) * (sum_of_remaining_time / (number_of_issues - len(issues_unestimated)))
        self.logger.debug("%.2f %s needed to complete %i issues", sum_of_remaining_time, time_unit, number_of_issues)
        self.logger.debug("remarks: there are %i issues unestimated", len(issues_unestimated))
        return sum_of_remaining_time

    def get_issues_commented_by_author(self, author, search_mask=""):
        """Return a list of issues commented by author and matching the search mask (JQL string).

            :param str author: The author's name respectively key (lowercase, e.g. "prename.surname")
            :param str search_mask: The JQL string used to search for issues.

            :returns: The list of issues found including the comments.
            :rtype: list(issue key, comments)
        """
        self.logger.debug("get_issues_commented_by_author(\"%s\", \"%s\")", author, search_mask)

        # get total number of issues
        number_of_issues = self.get_issues(search_mask=search_mask, index=None, count=None)["total"]

        self.logger.debug("searching inside of %i issues", number_of_issues)

        list_of_comments = []

        # visit all issues in blocks of 1000 (there's no way to get them all at once)
        issues_per_page = 1000
        i = 0
        while i < number_of_issues:
            list_of_issues = self.get_issues(search_mask=search_mask,
                                             index=i,
                                             count=min(issues_per_page, number_of_issues - i),
                                             fields="key, comment")
            for issue in list_of_issues["issues"]:
                comments = [(comment["created"], comment["body"]) for comment in issue["fields"]["comment"]["comments"] if comment["author"]["key"] == author]
                if comments != []:
                    list_of_comments.append((issue["key"], comments))
                i += 1
        return list_of_comments

    def get_transitions(self, key):
        """Returns possible transitions.

            :param key: The issue key.

            :returns: The list (id, name) of possible transitions.
        """
        self.logger.debug("get_transitions(\"%s\")", key)

        path = self.api + "/issue/{0}/transitions"
        headers = {**self.headers}
        response = self._get_data(path.format(urllib.parse.quote_plus(key or "")),
                                  headers=headers)

        return [] if response.get("error") else [(t["id"], t["name"]) for t in response["transitions"]]

    def get_transition_names(self, key):
        """Returns possible transitions.

            :param key: The issue key.

            :returns: The list of names of possible transitions.
        """
        self.logger.debug("get_transition_names(\"%s\")", key)

        path = self.api + "/issue/{0}/transitions"
        headers = {**self.headers}
        response = self._get_data(path.format(urllib.parse.quote_plus(key or "")),
                                  headers=headers)

        return [] if response.get("error") else [t["name"] for t in response["transitions"]]

    def get_issue(self, key):
        """Get information about issue.

            :param key: The issue key.

            :returns: Json data.
        """
        self.logger.debug("get_issue(\"%s\")", key)

        path = self.api + "/issue/{0}"
        headers = {**self.headers}
        response = self._get_data(path.format(urllib.parse.quote_plus(key or "")),
                                  headers=headers)

        return {} if response.get("error") else response

    def delete_issue(self, key):
        """Delete an issue.

            :param key: The issue key.

            :returns: Json data.
        """
        self.logger.debug("delete_issue(\"%s\")", key)

        path = self.api + "/issue/{0}"
        headers = {**self.headers}
        response = self._delete_data(path.format(urllib.parse.quote_plus(key or "")),
                                  headers=headers)

        return {} if response.get("error") else response

    def assign_issue(self, key, assignee=None):
        """Assign an issue.

            :param key: The issue key.
            :param assignee: The optional new assignee. Passing None just removes the current assignee.

            :returns: True if assignment succeeded, False if not
            :rtype: bool
        """
        self.logger.debug("assign_issue(\"%s\", \"%s\")", key, assignee)

        path = self.api + "/issue/{0}/assignee"
        headers = {**self.headers}
        headers["Content-type"] = "application/json"
        response = self._put_data(path.format(urllib.parse.quote_plus(key or "")),
                                  headers=headers,
                                  data=json.dumps({"name": assignee}))

        return not response.get("error", False)

    def resolve_issue(self, key, assignee=None, comment=None):
        """Resolve issue.

            :param key: The issue key.
            :param assignee: The optional new assignee.
            :param comment: The optional comment.

            :returns: True if transition succeeded, False if not
            :rtype: bool
        """
        self.logger.debug("resolve_issue(\"%s\", \"%s\", \"%s\")", key, assignee, comment)

        issue = self.get_issue(key)

        if not issue:
            self.logger.debug("issue %s not accessible or not found", key)
            return False

        transitions = self.get_transitions(key)

        if "Resolve Issue" in [name for id, name in transitions]:
            path = self.api + "/issue/{0}/transitions"
            headers = {**self.headers}
            headers["Content-type"] = "application/json"

            data = {}

            data["transition"] = {"id": [id for id, name in transitions if name == "Resolve Issue"][0]}

            data["fields"] = {"assignee": {"name": assignee}, "resolution": {"name": "Fixed" if issue.get("fields", {}).get("issuetype", {}).get("name", None) == "Bug" else "Done"}}

            if comment:
                data["update"] = {"comment": [{"add": {"body": comment}}]}

            response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                       headers=headers,
                                       data=json.dumps(data))

            return not response.get("error", False)
        else:
            self.logger.debug("issue %s cannot be resolved. status is %s, possible transitions are %s",
                              key, issue["fields"]["status"]["name"], set([name for id, name in transitions]))
            return False

    def close_issue(self, key, assignee=None, comment=None):
        """Close issue (and subtasks). If existing, remainingEstimate is set to 0.

            :param key: The issue key.
            :param assignee: The optional new assignee.
            :param comment: The optional comment.

            :returns: True if transition succeeded, False if not
            :rtype: bool
        """
        self.logger.debug("close_issue(\"%s\", \"%s\", \"%s\")", key, assignee, comment)

        issue = self.get_issue(key)

        if not issue:
            self.logger.debug("issue %s not accessible or not found", key)
            return False

        for subtask in issue["fields"]["subtasks"]:
            self.close_issue(subtask["key"])

        transitions = self.get_transitions(key)
        transition_names = [name for id, name in transitions]

        if ("Close Issue" not in transition_names) and ("Closed" not in transition_names) and ("Ready for progress" in transition_names):
            self.logger.debug("issue %s must be set to ready for progress first", key)

            path = self.api + "/issue/{0}/transitions"
            headers = {**self.headers}
            headers["Content-type"] = "application/json"

            data = {}

            data["transition"] = {"id": [id for id, name in transitions if name == "Ready for Progress"][0]}

            response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                       headers=headers,
                                       data=json.dumps(data))

            transitions = self.get_transitions(key)

        if ("Close Issue" not in transition_names) and ("Closed" not in transition_names) and ("in review" in transition_names):
            self.logger.debug("issue %s must be set to in review first", key)

            path = self.api + "/issue/{0}/transitions"
            headers = {**self.headers}
            headers["Content-type"] = "application/json"

            data = {}

            data["transition"] = {"id": [id for id, name in transitions if name == "in review"][0]}

            response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                       headers=headers,
                                       data=json.dumps(data))

            transitions = self.get_transitions(key)

        if "Close Issue" in [name for id, name in transitions] or "Closed" in [name for id, name in transitions]:
            # remainingEstimate is missing as transition parameter sometimes, so we set it here
            # only works if timetracking is available (e.g. for stories or if bugs include subtasks)
            if issue["fields"]["timetracking"].get("remainingEstimate") is not None:
                path = self.api + "/issue/{0}"
                headers = {**self.headers}
                headers["Content-type"] = "application/json"

                data = {}

                data["update"] = {"timetracking": [{"set": {"remainingEstimate": "0h"}}]}

                response = self._put_data(path.format(urllib.parse.quote_plus(key or "")),
                                          headers=headers,
                                          data=json.dumps(data))

            path = self.api + "/issue/{0}/transitions"
            headers = {**self.headers}
            headers["Content-type"] = "application/json"

            data = {}

            data["transition"] = {"id": [id for id, name in transitions if name == "Close Issue" or name == "Closed"][0]}

            data["fields"] = {"resolution": {"name": "Fixed" if issue.get("fields", {}).get("issuetype", {}).get("name", None) == "Bug" else "Done"}}

            if comment:
                data["update"] = {"comment": [{"add": {"body": comment}}]}

            response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                       headers=headers,
                                       data=json.dumps(data))

            if response.get("error"):
                # resolution is missing as transition screen parameter sometimes
                data["fields"] = None
                response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                           headers=headers,
                                           data=json.dumps(data))
                if response.get("error"):
                    return False

            # assignee is missing as transition parameter sometimes, so we set it here
            self.assign_issue(key, assignee)

            return True
        else:
            self.logger.debug("issue %s cannot be closed. status is %s, possible transitions are %s",
                              key, issue["fields"]["status"]["name"], set([name for id, name in transitions]))
            return False

    def reopen_issue(self, key, assignee=None, comment=None):
        """Reopen issue.

            :param key: The issue key.
            :param assignee: The optional new assignee.
            :param comment: The optional comment.

            :returns: True if transition succeeded, False if not
            :rtype: bool
        """
        self.logger.debug("reopenIssue(\"%s\", \"%s\", \"%s\")", key, assignee, comment)

        issue = self.get_issue(key)

        if not issue:
            self.logger.debug("issue %s not accessible or not found", key)
            return False

        transitions = self.get_transitions(key)

        if "Reopen Issue" in [name for id, name in transitions]:
            path = self.api + "/issue/{0}/transitions"
            headers = {**self.headers}
            headers["Content-type"] = "application/json"

            data = {}

            data["transition"] = {"id": [id for id, name in transitions if name == "Reopen Issue"][0]}

            data["fields"] = {"resolution": {"name": "Incomplete"}}

            if comment:
                data["update"] = {"comment": [{"add": {"body": comment}}]}

            response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                       headers=headers,
                                       data=json.dumps(data))

            if response.get("error"):
                # resolution is missing as transition screen parameter sometimes
                data["fields"] = None
                response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                           headers=headers,
                                           data=json.dumps(data))
                if response.get("error"):
                    return False

            # assignee is missing as transition parameter sometimes, so we set it here
            self.assign_issue(key, assignee)
        else:
            self.logger.debug("issue %s cannot be reopened. status is %s, possible transitions are %s",
                              key, issue["fields"]["status"]["name"], set([name for id, name in transitions]))
            return False

        return True

    def get_attachments(self, key):
        """Get all attachments of an issue.

            :param key: The issue key.

            :returns: List of json data
        """
        self.logger.debug("get_attachments(\"%s\")", key)

        path = self.api + "/issue/{0}?fields=attachment"
        headers = {**self.headers}
        response = self._get_data(path.format(urllib.parse.quote_plus(key or "")),
                                  headers=headers)

        return [] if response.get("error") else response["fields"].get("attachment") or []

    def rem_attachments(self, key):
        """Remove all attachments of an issue.

            :param key: The issue key.

            :returns: True if succeeded, False if not
            :rtype: bool
        """
        self.logger.debug("rem_attachments(\"%s\")", key)

        attachments = self.get_attachments(key)
        for att in attachments:
            path = self.api + "/attachment/{0}"
            headers = {**self.headers}
            response = self._delete_data(path.format(urllib.parse.quote_plus(att["id"] or "")),
                                         headers=headers)
            if isinstance(response, dict) and response.get("error"):
                return False
        return True

    def get_attachment(self, attachment_id):
        """Get attachments by id.

            :param attachment_id: The attachment id.

            :returns: Json data
        """
        self.logger.debug("get_attachment(\"%s\")", attachment_id)

        path = self.api + "/attachment/{0}"
        headers = {**self.headers}
        response = self._get_data(path.format(urllib.parse.quote_plus(attachment_id or "")),
                                  headers=headers)

        return {} if response.get("error") else response

    def add_attachment(self, key, attachment, filename=None):
        """Add attachment to an issue.

            :param key: The issue key.
            :param attachment: The file attachment as filepath name.
            :param filename: The optional filename.

            :returns: True if adding attachment succeeded, False if not
            :rtype: bool
        """
        self.logger.debug("add_attachment(\"%s\", \"%s\", \"%s\")", key, attachment, filename)

        needs_to_be_closed = False
        if isinstance(attachment, str):
            try:
                attachment = open(attachment, "rb")
            except OSError as ex:
                self.logger.debug("attachment failed. %s", ex)
            needs_to_be_closed = True
        elif not filename and not attachment.name:
            self.logger.debug("attachment name missing")
            return False
        elif hasattr(attachment, "read") and hasattr(attachment, "mode") and attachment.mode != "rb":
            self.logger.debug("%s not opened in 'rb' mode, attaching file may fail.", attachment.name)
            return False

        if not filename:
            filename = attachment.name

        stream = requests_toolbelt.MultipartEncoder(fields={"file": (filename, attachment, "application/octet-stream")})

        path = self.api + "/issue/{0}/attachments"
        headers = {**self.headers}
        headers["Content-type"] = stream.content_type
        headers["X-Atlassian-Token"] = "nocheck"
        response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                   data=stream,
                                   headers=headers)
        if needs_to_be_closed:
            attachment.close()

        return not (isinstance(response, dict) and response.get("error"))

    def add_comment(self, key, comment):
        """Add comment to an issue.

            :param key: The issue key.
            :param comment: The comment to add.

            :returns: True if commenting succeeded, False if not
            :rtype: bool
        """
        self.logger.debug("add_comment(\"%s\", \"%s\")", key, comment)

        path = self.api + "/issue/{0}/comment"
        headers = {**self.headers}
        headers["Content-type"] = "application/json"
        response = self._post_data(path.format(urllib.parse.quote_plus(key or "")),
                                   headers=headers,
                                   data=json.dumps({"body": comment}))

        return not response.get("error", False)
