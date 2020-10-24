#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functionality for REST APIs."""

import logging
import requests
import urllib.parse


class RestApi(object):
    """The RestApi class.

       Wrapper around requests module providing helpful methods for REST API requests.

       Example:

       session = RestApi(<url with scheme>, <username>, <password>)
       session.get(<apipath>)

       Typically, users inherit from this class to build their own wrapper supporting API specific paths, routes, queries or just features like pagination etc.
    """

    def __init__(self, server, username, password):
        """Construct a new instance.

            :param server: The server or base URL to be accessed. Should include the scheme as well.
            :param username: The username.
            :param password: The password.
        """
        # TODO: provide additional authentication methods
        self.server = server
        self.authentication = requests.auth.HTTPBasicAuth(username, password)
        self.headers = {"Accept": "application/json", "Content-type": "application/json"}
        self.methods = {"GET", "POST", "PUT", "DELETE"}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("__init__(\"%s\", \"%s\", \"%s\")", server, "XXXXXXXX", "XXXXXXXX")

    def request(self, method, path="", **kwargs):
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
                                        "{0}/{1}".format(self.server, urllib.parse.quote_plus(path, safe="?/&=")),
                                        auth=self.authentication,
                                        headers=headers,
                                        data=data,
                                        **kwargs)
            response.raise_for_status()
            result = {} if not response.text else response.json()
        except requests.exceptions.HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return {"error": ex}
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return {"error": ex}

        return result

    def get(self, path="", **kwargs):
        """Get data from path.

            :param path: The path to get data from.

            :param **kwargs: Arbitrary list of keyword arguments

            :returns: Json data
        """
        return self.request(method="GET", path=path, **kwargs)

    def post(self, path="", data=None, **kwargs):
        """Post data to path.

            :param path: The path to post data to.

            :param **kwargs: Arbitrary list of keyword arguments

            :returns: Json data
        """
        return self.request(method="POST", path=path, data=data, **kwargs)

    def put(self, path="", data=None, **kwargs):
        """Put data to path.

            :param path: The path to put data to.

            :param **kwargs: Arbitrary list of keyword arguments

            :returns: Json response
        """
        return self.request(method="PUT", path=path, data=data, **kwargs)

    def delete(self, path="", **kwargs):
        """Delete data from path.

            :param path: The path to delete data from.

            :param **kwargs: Arbitrary list of keyword arguments

            :returns: Json response
        """
        return self.request(method="DELETE", path=path, **kwargs)
