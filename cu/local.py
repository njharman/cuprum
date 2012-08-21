from __future__ import with_statement
import os
import sys
import stat
import tempfile
import contextlib
import logging
log = logging.getLogger('cu.local')

import six

from cu.env import Environment
from cu.path import Path, CWD
from cu.session import ShellSession
from cu.command import Command, CommandNotFound


class LocalSystem(object):
    '''The *local machine* (a singleton object). It serves as an entry point to
    everything related to the local machine, such as working directory and
    environment manipulation, command creation, etc.

    Attributes:
      - ``env`` - Local environment <cu.env.Environment>
      - ``cwd`` - Local current working directory <cu.path.CWD>
      - ``python`` - Python interpreter (``sys.executable``) <cu.command.Command>
      - ``encoding`` - Local encoding (``sys.getfilesystemencoding()``)
      - ''session()'' - ShellSession <cu.session.ShellSession>
      - ''tempdir()'' - Temp directory context manager
      - ''tempfile()'' - Temp file context manager
    '''

    def __init__(self):
        self.cwd = CWD()
        self.env = Environment()
        self.encoding = sys.getfilesystemencoding()
        self.python = Command(sys.executable, self.encoding)

    def __getitem__(self, command):
        '''Returns a `Command` object representing the given program. ``command``
        can be a string or a :class:`Path <cu.path.Path>`; if it is a path, a
        command representing this path will be returned; otherwise, the program
        name will be looked up in the system's ``PATH`` (using ``which``).
        Usage::

            ls=local('ls')
        '''
        if isinstance(command, Path):
            return Command(command)
        elif isinstance(command, str):
            if '/' in command or '\\' in command:  # assume path
                return Command(Path(command))
            else:  # search for command
                return Command(self.which(command))
        else:
            raise TypeError('command must be a Path or a string: %r' % (command,))

    if os.name == 'nt':
        def _which(self, command, filelist):
            command = command.lower()
            for ext in [''] + self.env.get('PATHEXT', ':.exe:.bat').lower().split(os.path.pathsep):
                n = command + ext
                if n in filelist:
                    return filelist[n]
    else:
        def _which(self, command, filelist):
            if command in filelist:
                f = filelist[command]
                if f.stat().st_mode & stat.S_IXUSR:
                    return f

    def which(self, progname):
        '''Looks up a program in the ``PATH``. If the program is not found, raises
        :class:`CommandNotFound <cu.command.CommandNotFound>`

        :param progname: The program's name. Note that if underscores (``_``) are present
                         in the name, and the exact name is not found, they will be replaced
                         by hyphens (``-``) and the name will be looked up again

        :returns: A :class:`Path <cu.path.Path>`
        '''
        alternatives = [progname, ]
        if '_' in progname:
            alternatives.append(progname.replace('_', '-'))
        for command in alternatives:
            for path in self.env.path:
                try:
                    filelist = dict((n.basename, n) for n in path.list())
                    found = self._which(command, filelist)
                    if found:
                        return found
                except OSError:
                    continue
        raise CommandNotFound(progname, list(self.env.path))

    def session(self):
        '''Creates a new :class:`ShellSession <cu.session.ShellSession>` object;
        this invokes ``/bin/sh`` and executes commands on it over
        stdin/stdout/stderr
        '''
        return ShellSession(self['sh'].popen())

    @contextlib.contextmanager
    def tempdir(self, *args, **kwargs):
        '''Context manager that creates a temporary directory, which is
        removed when the context exits.
        :param suffix
        :yields: :class:`Path` object
        '''
        path = Path(tempfile.mkdtemp(*args, **kwargs))
        try:
            yield path
        finally:
            path.delete()

    @contextlib.contextmanager
    def tempfile(self, mode='w+b', bufsize=-1, suffix='', prefix='tmp', dir=None):
        '''Context manager that creates a named temporary file, which is
        removed when the context exits.

        :yields: file handle object with attribut 'name', a :class:`Path` object
        '''
        # Explicitly named kwargs cause order changes in Python 3.x
        # Also, bufsize renamed buffering
        kwargs = dict(mode=mode, suffix=suffix, prefix=prefix, dir=dir, delete=False)
        if six.PY3:
            if bufsize >= 0:
                kwargs['buffering'] = bufsize
        else:
            kwargs['bufsize'] = bufsize
        fh = tempfile.NamedTemporaryFile(**kwargs)
        fh.name = Path(fh.name)
        try:
            yield fh
        finally:
            fh.name.delete()
