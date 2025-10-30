import logging
import math
import time
import multiprocessing
from enum import StrEnum
from dataclasses import dataclass


try:
    from .configLoader import ConfigLoader
except:
    from configLoader import ConfigLoader

from .decorators import singleton

"""
Console Level Options
0 : Only print errors and critical messages to console.
1 : Print all info, errors, and critical messages to console.
2 : Print all debug, info, errors, and critical messages to console.
"""


@dataclass
class LogMsg:
    content: str
    module: str
    filename: str
    lineno: int


class colorEnum(StrEnum):
    kColorReset = "\033[0m"
    kColorGreen = "\033[0;32m"
    kColorBrightRed = "\033[1;31m"
    kColorBrightGreen = "\033[1;32m"
    kColorBrightYellow = "\033[1;33m"
    kColorBrightBlue = "\033[1;34m"
    kColorBrightMagenta = "\033[1;35m"
    kColorBrightCyan = "\033[1;36m"
    kColorBrightWhite = "\033[1;37m"




@singleton
class logger:
    def __init__(self) -> None:
        global __initlized
        self.__severity = min(
            math.floor(ConfigLoader('./config.json')['debug_level'])*10, 50
        )
        self.__time_start = time.time()

        self.__severity_colors = {
            logging.DEBUG: colorEnum.kColorBrightCyan,
            logging.INFO: colorEnum.kColorBrightGreen,
            logging.WARNING: colorEnum.kColorBrightYellow,
            logging.ERROR: colorEnum.kColorBrightRed,
            logging.FATAL: colorEnum.kColorBrightMagenta,
        }

        self.__logger_init()


    def __logger_init(self):
        
        self.__logger = logging.getLogger(__name__)
        self.__logger.setLevel(level=self.__severity)
        logger_handler = logging.StreamHandler()
        logger_handler.setLevel(level=self.__severity)
        formatter = logging.Formatter('%(message)s')
        logger_handler.setFormatter(formatter)
        self.__logger.addHandler(logger_handler)

    @staticmethod
    def __convert_int_to_severity(level: int) -> str:
        return [
            'DEBUG',
            ' INFO',
            ' WARN',
            'ERROR',
            'FATAL'
        ][level//10-1]

    def __logger_builder(
            self,
            severity: int,
            msg: LogMsg
    ):
        return '[{time}] [{pid}] {level_color}{level}{reset_color} '\
            '{module_color}{module}{reset_color} '\
            '{file_color}{file}:{lineno}{reset_color} '\
            '{content}'.format(
                time=str((time.time()-self.__time_start)*1000)[:17],
                pid=multiprocessing.current_process().pid,
                level=self.__convert_int_to_severity(severity),
                module=msg.module,
                file=msg.filename,
                lineno=msg.lineno,
                content=msg.content,
                level_color=self.__severity_colors[severity],
                module_color=colorEnum.kColorBrightWhite,
                file_color=colorEnum.kColorBrightBlue,
                reset_color=colorEnum.kColorReset
            )

    def debug(self, content: LogMsg):
        self.__logger.debug(
            self.__logger_builder(
                severity=logging.DEBUG,
                msg=content
            )
        )

    def info(self, content: LogMsg):
        self.__logger.debug(
            self.__logger_builder(
                severity=logging.INFO,
                msg=content
            )
        )

    def warning(self, content: LogMsg):
        self.__logger.warning(
            self.__logger_builder(
                severity=logging.WARNING,
                msg=content
            )
        )

    def error(self, content: LogMsg):
        self.__logger.error(
            self.__logger_builder(
                severity=logging.ERROR,
                msg=content
            )
        )

    def fatal(self, content: LogMsg):
        self.__logger.fatal(
            self.__logger_builder(
                severity=logging.FATAL,
                msg=content
            )
        )
