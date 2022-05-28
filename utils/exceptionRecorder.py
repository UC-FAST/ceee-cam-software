# encoding=utf-8

import time
import traceback
from functools import wraps


def exceptionRecorder(path="exceptions.log"):
    def decorate(func):
        @wraps(func)
        def wrap(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                traceback.print_exc()
                with open(path, 'a') as f:
                    f.write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
                    f.write('\n')
                    f.write(traceback.format_exc())
                    f.write('\n')

        return wrap

    return decorate
