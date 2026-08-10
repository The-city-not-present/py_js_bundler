
import re
from enum import Enum


class Type(Enum):
    PATH_RELATIVE = 1
    URL_ABSOLUTE = 2
    PATH_ABSOLUTE = 3
    BARE = 4

# class Status(str, Enum):
#     PENDING = "pending"
#     RUNNING = "running"
#     COMPLETED = "completed"
#
# print(Status.PENDING.value)  # pending

# class LogLevel(Enum):
#     DEEBUG = 1 # to not have it highlighter by linter and search - I am sometimes searching for word "deb..."
#     INFO = 2
#     ERROR = 3
#
# def log(message: str, level: LogLevel):
#     print(f"[{level.name}] {message}")


def classify_module_specifier(name):
    if re.match(r'(\.|\.{2})/.*',name):
        return Type.PATH_RELATIVE
    elif re.match(r'\w+:.*',name):
        return Type.URL_ABSOLUTE
    elif re.match(r'/.*',name):
        return Type.PATH_ABSOLUTE
    else:
        return Type.BARE
