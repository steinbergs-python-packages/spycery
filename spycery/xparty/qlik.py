#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides extensions for handling QlikSense apps."""

import os
import json
import logging
import uuid
import shutil

# needs websocket-client
from websocket import create_connection


class Qlik(object):
    """The Qlik class.

       Can be used together with QlikSense Desktop in order to automate data updates.
       Performs methods as available via http://localhost:4848/dev-hub/engine-api-explorer.

       1. Install QlikSense Desktop
       2. Start the application and register resp. login with your credentials
          Now http://localhost:4848/dev-hub/engine-api-explorer should be online.
       3. Create or load some apps into QlikSense Desktop (if applicable)
       4. Use this class f.e. to reload apps from within python code to update included data
          qlik = Qlik()
          qlik.reloadApp("QlikSense App.qvf")
    """

    def __init__(self, server="localhost:4848"):
        # self.base_url = "ws://localhost:4848/app/{0}?reloadUri=http://localhost:4848/dev-hub/engine-api-explorer"
        self.base_url = "ws://{0}/app/%3Ftransient%3D?reloadUri=http://{0}/dev-hub/engine-api-explorer".format(server)
        self.ws = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self):
        """Create connection."""
        try:
            # self.ws = create_connection(self.base_url.format(urllib.parse.quote_plus(filename)))
            self.ws = create_connection(self.base_url)
            response = self.ws.recv()
            return json.loads(response)
        except ConnectionRefusedError as ex:
            self.logger.debug("connection failed. %s", ex)
            return {}

    def close(self):
        """Close connection."""
        if self.ws is not None:
            self.ws.close()

    def apply_method(self, params):
        """Apply a method by sending params to websocket.

           :returns: The response in json format (dict).
        """
        if self.ws is None:
            self.logger.debug("connection needed")
            return {}

        self.ws.send(json.dumps(params))
        response = self.ws.recv()
        return json.loads(response)

    def get_default_app_folder(self):
        """Get the default app folder path.

           :returns: The path of the default app folder or None.
        """
        if self.ws is None:
            self.logger.debug("connection needed")
            return None

        handle = -1

        params = {
            "handle": handle,
            "method": "GetDefaultAppFolder",
            "params": {}
        }

        response = self.apply_method(params)

        if response.get("error") is not None:
            self.logger.debug("GetDefaultAppFolder failed. %s", response["error"].get("message") or "")
            return None

        return response["result"]["qPath"]

    def reload_app(self, filename, outfilename=""):
        """Reload an existing app from default app folder.

           :param filename: The app filename.
           :param outfilename: The optional output filename. Can be used to clone the app.
           :remarks: If filenames are given without path, method loads/stores app within default app folder.
                     (e.g. "C:\\Users\\<username>\\Documents\\Qlik\\Sense\\Apps")
           :returns: False if reload failed, else True.
        """
        self.close()
        try:
            # self.ws = create_connection(self.base_url.format(urllib.parse.quote_plus(filename)))
            self.ws = create_connection(self.base_url)
            response = self.ws.recv()
        except ConnectionRefusedError as ex:
            self.logger.debug("Reload failed. %s", ex)
            return False

        handle = -1

        # note:
        # actually this is only necessary for creating connection to f
        # "ws://localhost:4848/app/{0}?reloadUri=http://localhost:4848/dev-hub/engine-api-explorer".format(fileabspath)
        # if connection is created with transient url (as it is right now) this method could be skipped.
        params = {
            "handle": handle,
            "method": "GetDefaultAppFolder",
            "params": {}
        }

        response = self.apply_method(params)

        if response.get("error") is not None:
            self.logger.debug("Reload failed. %s", response["error"].get("message") or "")

        # something failed so we try to use local path as appfolder
        appfolder = "." if response.get("error") is not None else response["result"]["qPath"]

        # extension:
        # if filename is a path filename, copy it to the default app folder (with a unique ID),
        # refresh it therein and remove it afterwards
        newfilename = None
        if filename == os.path.basename(filename):
            pass
        else:
            if outfilename is None or outfilename == "":
                # as we are working on a copy of original file,
                # outfilename needs to be specified to refresh the original file as well
                outfilename = filename
            newfilename = "{0}\\temp_app_{1}.qvf".format(appfolder, str(uuid.uuid4()))
            shutil.copyfile(filename, newfilename)
            filename = newfilename

        params = {
            "handle": handle,
            "method": "OpenDoc",
            "params": {
                "qDocName": os.path.basename(filename),
                "qUserName": "",
                "qPassword": "",
                "qSerial": "",
                "qNoData": False
            }
        }

        response = self.apply_method(params)

        if response.get("error") is not None:
            self.logger.debug("Reload failed. %s", response["error"].get("message") or "")
            self.close()
            return False

        params = {
            "handle": handle,
            "method": "GetActiveDoc",
            "params": {}
        }

        response = self.apply_method(params)

        if response.get("error") is not None:
            self.logger.debug("Reload failed. %s", response["error"].get("message") or "")
            self.close()
            return False

        handle = response["result"]["qReturn"]["qHandle"]

        params = {
            "handle": handle,
            "method": "DoReload",
            "params": {
                "qMode": 0,
                "qPartial": False,
                "qDebug": False
            }
        }

        response = self.apply_method(params)

        if response.get("error") is not None:
            self.logger.debug("Reload failed. %s", response["error"].get("message") or "")
            self.close()
            return False

        params = {
            "handle": handle,
            "method": "DoSave",
            "params": {
                "qFileName": os.path.abspath(outfilename)
            }
        }

        response = self.apply_method(params)

        if response.get("error") is not None:
            self.logger.debug("Reload failed. %s", response["error"].get("message") or "")
            self.close()
            return False

        if newfilename is not None:
            os.remove(newfilename)

        self.close()
        return True
