# spycery

This python package provides useful modules and extensions for python development.

# Table of Contents
- [Installation](#installation)
- [Examples and Features](#examples-and-features)


## Installation

To install spycery, you can use (one of) the following command(s):
```
$ pip install git+https://github.com/steinbergs-python-packages/spycery
$ pip install git+https://github.com/steinbergs-python-packages/spycery@v0.0.1
$ pip install https://github.com/steinbergs-python-packages/spycery/archive/v0.0.1/spycery.zip
```

To uninstall spycery, you can use the following command:
```
$ pip uninstall spycery
```

## Examples and Features

### Basics

<details>
<summary>Const type</summary>

Basic const type implementation.

Use it as the metaclass, when implementing a class containing readonly attributes.

   ```python
    class MyClass(metaclass=Const):
        my_param = Const.Attribute("xyz")
   ```

   This will define myparam as readonly.
   Each try to change its value - be it as class attribute or instance attribute - will raise an AttributeError:

   ```python
    MyClass.my_param = 5
    MyClass().my_param = "abc"
   ```
</details>

<details>
<summary>Environment</summary>

environment class to be used for running python scripts, tools etc. in

Example to run a tool in a virtual environment:
   ```python
    import logging
    from python_library.environment import Environment

    Environment().activate(env_mode=Environment.EnvMode.VIRTUAL, refresh_mode=Environment.RefreshMode.SMART, log_level=logging.DEBUG)
   ```
</details>

### Extensions

<details>
<summary>Datetime</summary>

datetime extensions for getting start and end of day, week, month and year
</details>

<details>
<summary>Plot</summary>

matplotlib.pyplot extensions for creating grids, line/bar charts and timelines
</details>

<details>
<summary>SMTP</summary>
smtplib extension for sending multipart html messages with embedded images or just attachments.

Example(s):
   ```python
    from smtp_extensions import SMTP

    with SMTP("localhost", 25) as smtp:
        smtp.sendhtml(sender="From <from@address>",
                      subject="subject",
                      message="<html><img src=\"cid:image1\" width=100%><br><img src=\"cid:image2\" width=100%></html>",
                      recipients="To <to@address>,To2 <to2@address>",
                      bccs="hidden@address,hidden2@address",
                      attachments=["filepath1", "filepath2"],
                      images=["<filepath of image1>", "<filepath of image2>"])

   ```
</details>

### XParty

<details>
<summary>Jira</summary>

module for JIRA interaction
</details>

<details>
<summary>Qlik</summary>

module for handling QlikSense apps
</details>
