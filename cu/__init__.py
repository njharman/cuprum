__version__ = '0.0.1'

import sys
import subprocess
from types import ModuleType

# imported for convience. i.e cu.tmpfile
from tempfile import NamedTemporaryFile, mkstemp, mkdtemp

from path import Path
from local import LocalSystem
from command import FG, BG, ERROUT
from exception import CommandNotFound, ProcessExecutionError, ProcessTimedOut, RedirectionError


local = LocalSystem()
BG = BG()
FG = FG()
ERROUT = ERROUT(subprocess.STDOUT)


class LocalModule(ModuleType):
    '''The module-hack that allows us to use ``from cu.syspath import some_program``'''
    def __init__(self, name):
        ModuleType.__init__(self, name, __doc__)
        self.__file__ = None
        self.__package__ = '.'.join(name.split('.')[:-1])

    def __getattr__(self, name):
        return local[name]


LocalModule = LocalModule('cu.syspath')
sys.modules[LocalModule.__name__] = LocalModule
