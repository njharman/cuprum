__version__ = '0.1.0'

import sys
import types
import subprocess

# imported for convience. i.e cu.tmpfile
from tempfile import NamedTemporaryFile, mkstemp, mkdtemp

from .command import (
        FG, BG, ERROUT,
        CommandNotFound, ProcessExecutionError, ProcessTimedOut, RedirectionError
        )
from .local import LocalSystem
from .path import Path


local = LocalSystem()
BG = BG()
FG = FG()
ERROUT = ERROUT(subprocess.STDOUT)


class LocalModule(types.ModuleType):
    '''The module-hack that allows us to use ``from cu.syspath import some_program``'''
    def __init__(self, name):
        super(LocalModule, self).__init__(name, __doc__)
        self.__file__ = None
        self.__package__ = '.'.join(name.split('.')[:-1])

    def __getattr__(self, name):
        return local[name]

LocalModule = LocalModule('cu.syspath')
sys.modules[LocalModule.__name__] = LocalModule
