#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides extensions for sending SMTP mails."""

import os
import smtplib

from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class SMTP(smtplib.SMTP):
    """The SMTP extension class.

       Extends the SMTP class of the smtplib module.

       Example:
       from smtp_extensions import SMTP

       smtp = SMTP("localhost", 25)
       smtp.sendhtml(sender="from@address",
                     subject="subject",
                     message="<html>hello</html>",
                     recipients="to@address,to2@address",
                     attachments=["filepath1", "filepath2"])
    """

    def sendhtml(self, sender, subject, message, recipients, **kwargs):
        """Send a multipart html message.

           :param str sender: The sender's address (fromaddress).
           :param str subject: The email subject.
           :param str message: The message in HTML format.
           :param str recipients: The recipient addresses (comma-separated string).

           :param **kwargs: Arbitrary list of keyword arguments
                    ccs: The recipient cc addresses (comma-separated string).
                    bccs: The recipient bcc addresses (comma-separated string).
                    attachments: The list of attachments.
                    images: The list of images to be embedded into given html message, e.g.
                            "<img src=\"cid:image1\"> matches the first image in the list
        """
        ccs = kwargs.pop("ccs", "")
        bccs = kwargs.pop("bccs", "")
        attachments = kwargs.pop("attachments", None)
        images = kwargs.pop("images", None)
        assert not kwargs, 'Unknown arguments: %r' % kwargs

        # note:
        # content-type 'related' is important to display embedded images
        # properly in mail clients like thunderbird
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipients
        msg["CC"] = ccs
        # disable this, otherwise "to and cc" receivers will see the bcc receivers
        # msg["BCC"] = BCCs
        msg.attach(MIMEText(message, "html"))

        # embed images
        if images is None:
            images = []
        for image in images:
            with open(image, "rb") as file:
                msg_mimepart = MIMEImage(file.read())
                msg_mimepart.add_header("Content-ID", "<image{}>".format(images.index(image) + 1))
                msg.attach(msg_mimepart)

        # add attachments
        if attachments is None:
            attachments = []
        for attachment in attachments:
            with open(attachment, "rb") as file:
                msg_mimepart = MIMEApplication(file.read())
                msg_mimepart.add_header("Content-Disposition", "attachment", filename=os.path.basename(attachment))
                msg.attach(msg_mimepart)

        self.sendmail(sender, recipients.split(",") + ccs.split(",") + bccs.split(","), msg.as_string())
