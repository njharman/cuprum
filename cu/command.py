from __future__ import with_statement
import sys
import time
import heapq
import tempfile
import threading
import subprocess
import logging
log = logging.getLogger('cu.command')

import six

if not six.PY3:
    bytes = str
    ascii = repr

if not hasattr(subprocess.Popen, 'kill'):
    # python 2.5 compatibility
    import os
    import signal
    subprocess.Popen.kill = lambda s: os.kill(s.pid, signal.SIGKILL)
    subprocess.Popen.terminate = lambda s: os.kill(s.pid, signal.SIGTERM)
    subprocess.Popen.send_signal = lambda s, sig: os.kill(s.pid, sig)

from cu.env import Environment


# modified from the stdlib pipes module for windows
_safechars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%_-+=:,./'
_funnychars = '"`$\\'


def shquote(text):
    '''Quotes the given text with shell escaping (assumes as syntax similar to ``sh``).'''
    if not text:
        return "''"
    text = str(text)
    for c in text:
        if c not in _safechars:
            break
    else:
        return text
    if "'" not in text:
        return "'" + text + "'"
    res = ''.join(('\\' + c if c in _funnychars else c) for c in text)
    return '"' + res + '"'


def shquote_list(seq):
    return [shquote(item) for item in seq]


class MinHeap(object):
    def __init__(self, items=()):
        self._items = list(items)
        heapq.heapify(self._items)

    def __len__(self):
        return len(self._items)

    def push(self, item):
        heapq.heappush(self._items, item)

    def pop(self):
        heapq.heappop(self._items)

    def peek(self):
        return self._items[0]


def _timeout_thread():
    waiting = MinHeap()
    while True:
        if waiting:
            ttk, _ = waiting.peek()
            timeout = max(0, ttk - time.time())
        else:
            timeout = None
        try:
            proc, time_to_kill = _timeout_queue.get(timeout=timeout)
            waiting.push((time_to_kill, proc))
        except queue.Empty:
            pass
        now = time.time()
        while waiting:
            ttk, proc = waiting.peek()
            if ttk > now:
                break
            waiting.pop()
            try:
                if proc.poll() is None:
                    proc.kill()
                    proc._timed_out = True
            except EnvironmentError:
                pass


queue = six.moves.queue
_timeout_queue = queue.Queue()
thd = threading.Thread(target=_timeout_thread)
thd.setDaemon(True)
thd.start()


def run_proc(proc, retcode, timeout=None):
    '''Waits for the given process to terminate, with the expected exit code.

    :param proc: running Popen-like object

    :param retcode: expected return (exit) code of the process. It defaults to 0 (the
        convention for success). If ``None``, the return code is ignored.
        It may also be a tuple (or any object that supports ``__contains__``)
        of expected return codes.

    :param timeout: number of seconds (a ``float``) to allow the process to run, before
        forcefully terminating it. If ``None``, not timeout is imposed; otherwise
        the process is expected to terminate within that timeout value, or it will
        be killed and :class:`ProcessTimedOut <cu.cli.ProcessTimedOut>`
        will be raised

    :returns: A tuple of (return code, stdout, stderr)
    '''
    if timeout is not None:
        _timeout_queue.put((proc, time.time() + timeout))
    stdout, stderr = proc.communicate()
    proc._end_time = time.time()
    if not stdout:
        stdout = six.b('')
    if not stderr:
        stderr = six.b('')
    if getattr(proc, 'encoding', None):
        stdout = stdout.decode(proc.encoding, 'ignore')
        stderr = stderr.decode(proc.encoding, 'ignore')
    if getattr(proc, '_timed_out', False):
        raise ProcessTimedOut('Process did not terminate within %s seconds' % (timeout,), getattr(proc, 'argv', None))
    if retcode is not None:
        if hasattr(retcode, '__contains__'):
            if proc.returncode not in retcode:
                raise ProcessExecutionError(getattr(proc, 'argv', None), proc.returncode, stdout, stderr)
        elif proc.returncode != retcode:
            raise ProcessExecutionError(getattr(proc, 'argv', None), proc.returncode, stdout, stderr)
    return proc.returncode, stdout, stderr


class BaseCommand(object):
    '''Base of all command objects.'''
    def __str__(self):
        return ' '.join(self.formulate())

    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self.executable)

    def __or__(self, other):
        '''Creates a pipe with the other command.'''
        return Pipeline(self, other)

    def __gt__(self, file):
        '''Redirects the process' stdout to the given file.'''
        return StdoutRedirection(self, file)

    def __ge__(self, file):
        '''Redirects the process' stderr to the given file.'''
        return StderrRedirection(self, file)

    def __lt__(self, file):
        '''Redirects the given file into the process' stdin.'''
        return StdinRedirection(self, file)

    def __lshift__(self, data):
        '''Redirects the given data into the process' stdin.'''
        return StdinDataRedirection(self, data)

    def __getitem__(self, args):
        '''Creates a bound-command with the given arguments.'''
        if not isinstance(args, (tuple, list)):
            args = (args,)
        if not args:
            return self
        if isinstance(self, BoundCommand):
            return BoundCommand(self.executable, self.args + tuple(args))
        else:
            return BoundCommand(self, args)

    def __call__(self, *args, **kwargs):
        '''A shortcut for `run(args)`, returning only the process' stdout.'''
        return self.run(args, **kwargs)[1]

    def _get_encoding(self):
        raise NotImplementedError()

    def formulate(self, level=0, args=()):
        '''Formulates the command into a command-line, i.e., a list of shell-quoted strings
        that can be executed by ``Popen`` or shells.
        :param level: The nesting level of the formulation; it dictates how much shell-quoting
                      (if any) should be performed
        :param args: The arguments passed to this command (a tuple)
        :returns: A list of strings
        '''
        raise NotImplementedError()

    def popen(self, args=(), **kwargs):
        '''Spawns the given command, returning a ``Popen``-like object.
        :param args: Any arguments to be passed to the process (a tuple)
        :param kwargs: Any keyword-arguments to be passed to the ``Popen`` constructor
        :returns: A ``Popen``-like object
        '''
        raise NotImplementedError()

    def run(self, args=(), **kwargs):
        '''Runs the given command (equivalent to popen() followed by
        :func:`run_proc <cu.command.run_proc>`). If the exit code of the process does
        not match the expected one, :class:`ProcessExecutionError
        <cu.command.ProcessExecutionError>` is raised.
        :param args: Any arguments to be passed to the process (a tuple)
        :param retcode: The expected return code of this process (defaults to 0).
                        In order to disable exit-code validation, pass ``None``. It may also
                        be a tuple (or any iterable) of expected exit codes.
                        .. note:: this argument must be passed as a keyword argument.
        :param timeout: The maximal amount of time (in seconds) to allow the process to run.
                       ``None`` means no timeout is imposed; otherwise, if the process hasn't
                       terminated after that many seconds, the process will be forcefully
                       terminated an exception will be raised
        :param kwargs: Any keyword-arguments to be passed to the ``Popen`` constructor
        :returns: A tuple of (return code, stdout, stderr)
        '''
        retcode = kwargs.pop('retcode', 0)
        timeout = kwargs.pop('timeout', None)
        p = self.popen(args, **kwargs)
        try:
            return run_proc(p, retcode, timeout)
        finally:
            for f in [p.stdin, p.stdout, p.stderr]:
                try:
                    f.close()
                except Exception:
                    pass


class Command(BaseCommand):
    QUOTE_LEVEL = 2

    def __init__(self, executable, encoding='auto'):
        super(Command, self).__init__()
        from cu import local
        if encoding == 'auto':
            encoding = local.encoding
        self.executable = executable
        self.encoding = encoding
        self.cwd = None
        self.env = None

    def _get_encoding(self):
        return self.encoding

    def popen(self, args=(), cwd=None, env=None, **kwargs):
        if isinstance(args, six.string_types):
            args = (args,)
        return self._popen(
            self.executable, self.formulate(0, args),
            cwd=self.cwd if cwd is None else cwd,
            env=self.env if env is None else env,
            **kwargs)

    def _popen(self, executable, argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None, env=None, **kwargs):
        from cu import local
        if subprocess.mswindows and 'startupinfo' not in kwargs and stdin not in (sys.stdin, None):
            kwargs['startupinfo'] = sui = subprocess.STARTUPINFO()
            sui.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            sui.wShowWindow = subprocess._subprocess.SW_HIDE
        if cwd is None:
            cwd = local.cwd
        if env is None:
            env = local.env
        if isinstance(env, Environment):
            env = env.as_dict()
        log.debug('Running %r', argv)
        proc = subprocess.Popen(
            argv, executable=str(executable), stdin=stdin, stdout=stdout,
            stderr=stderr, cwd=str(cwd), env=env, **kwargs)  # bufsize=4096
        proc._start_time = time.time()
        proc.encoding = self.encoding
        proc.argv = argv
        return proc

    def formulate(self, level=0, args=()):
        argv = [str(self.executable)]
        for a in args:
            if not a:
                continue
            if isinstance(a, BaseCommand):
                if level >= self.QUOTE_LEVEL:
                    argv.extend(shquote_list(a.formulate(level + 1)))
                else:
                    argv.extend(a.formulate(level + 1))
            else:
                if level >= self.QUOTE_LEVEL:
                    argv.append(shquote(a))
                else:
                    argv.append(str(a))
        #if self.encoding:
        #    argv = [a.encode(self.encoding) for a in argv if isinstance(a, six.string_types)]
        return argv


class BoundCommand(BaseCommand):
    def __init__(self, executable, args):
        super(BoundCommand, self).__init__()
        self.executable = executable
        self.args = args

    def _get_encoding(self):
        return self.executable._get_encoding()

    def formulate(self, level=0, args=()):
        return self.executable.formulate(level + 1, self.args + tuple(args))

    def popen(self, args=(), **kwargs):
        if isinstance(args, str):
            args = (args,)
        return self.executable.popen(self.args + tuple(args), **kwargs)


class Pipeline(BaseCommand):
    def __init__(self, src_executable, dst_executable):
        super(BaseCommand, self).__init__()
        self.src_executable = src_executable
        self.dst_executable = dst_executable

    def __repr__(self):
        return 'Pipeline(%r, %r)' % (self.src_executable, self.dst_executable)

    def _get_encoding(self):
        return self.src_executable._get_encoding() or self.dst_executable._get_encoding()

    def formulate(self, level=0, args=()):
        return self.src_executable.formulate(level + 1) + ['|'] + self.dst_executable.formulate(level + 1, args)

    def popen(self, args=(), **kwargs):
        src_kwargs = kwargs.copy()
        src_kwargs['stdout'] = subprocess.PIPE
        src_kwargs['stderr'] = subprocess.PIPE
        srcproc = self.src_executable.popen(args, **src_kwargs)
        kwargs['stdin'] = srcproc.stdout
        dstproc = self.dst_executable.popen(**kwargs)
        # allow p1 to receive a SIGPIPE if p2 exits
        srcproc.stdout.close()
        srcproc.stderr.close()
        if srcproc.stdin:
            srcproc.stdin.close()
        dstproc.srcproc = srcproc
        return dstproc


class BaseRedirection(BaseCommand):
    SYM = None
    KWARG = None
    MODE = None

    def __init__(self, executable, file):
        super(BaseRedirection, self).__init__()
        self.executable = executable
        self.file = file

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.executable, self.file)

    def _get_encoding(self):
        return self.executable._get_encoding()

    def formulate(self, level=0, args=()):
        return self.executable.formulate(level + 1, args) + [self.SYM, shquote(getattr(self.file, 'name', self.file))]

    def popen(self, args=(), **kwargs):
        from cu.local import Path
        if self.KWARG in kwargs and kwargs[self.KWARG] not in (subprocess.PIPE, None):
            raise RedirectionError('%s is already redirected' % (self.KWARG,))
        if isinstance(self.file, (str, Path)):
            f = kwargs[self.KWARG] = open(str(self.file), self.MODE)
        else:
            kwargs[self.KWARG] = self.file
            f = None
        try:
            return self.executable.popen(args, **kwargs)
        finally:
            if f:
                f.close()


class StdinRedirection(BaseRedirection):
    SYM = '<'
    KWARG = 'stdin'
    MODE = 'r'


class StdoutRedirection(BaseRedirection):
    SYM = '>'
    KWARG = 'stdout'
    MODE = 'w'


class StderrRedirection(BaseRedirection):
    SYM = '2>'
    KWARG = 'stderr'
    MODE = 'w'


class ERROUT(int):
    def __str__(self):
        return '&1'

    def __repr__(self):
        return 'ERROUT'


class StdinDataRedirection(BaseCommand):
    CHUNK_SIZE = 16000

    def __init__(self, executable, data):
        super(StdinDataRedirection, self).__init__()
        self.executable = executable
        self.data = data

    def _get_encoding(self):
        return self.executable._get_encoding()

    def formulate(self, level=0, args=()):
        return ['echo %s' % (shquote(self.data),), '|', self.executable.formulate(level + 1, args)]

    def popen(self, args=(), **kwargs):
        if 'stdin' in kwargs and kwargs['stdin'] != subprocess.PIPE:
            raise RedirectionError('stdin is already redirected')
        data = self.data
        if not isinstance(data, bytes) and self._get_encoding() is not None:
            data = data.encode(self._get_encoding())
        f = tempfile.TemporaryFile()
        while data:
            chunk = data[:self.CHUNK_SIZE]
            f.write(chunk)
            data = data[self.CHUNK_SIZE:]
        f.seek(0)
        try:
            return self.executable.popen(args, stdin=f, **kwargs)
        finally:
            f.close()


class Future(object):
    '''Represents a 'future result' of a running process. It basically wraps a ``Popen``
    object and the expected exit code, and provides poll(), wait(), returncode, stdout,
    and stderr.
    '''
    def __init__(self, proc, expected_retcode, timeout=None):
        self.proc = proc
        self._expected_retcode = expected_retcode
        self._timeout = timeout
        self._returncode = None
        self._stdout = None
        self._stderr = None

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<Future %r (%s)>' % (self.proc.argv, self._returncode if self.ready() else 'running',)

    @property
    def stdout(self):
        '''The process' stdout; accessing this property will wait for the process to finish.'''
        self.wait()
        return self._stdout

    @property
    def stderr(self):
        '''The process' stderr; accessing this property will wait for the process to finish.'''
        self.wait()
        return self._stderr

    @property
    def returncode(self):
        '''The process' returncode; accessing this property will wait for the process to finish.'''
        self.wait()
        return self._returncode

    def poll(self):
        '''Polls the underlying process for termination; returns ``None`` if still running,
        or the process' returncode if terminated.'''
        if self.proc.poll() is not None:
            self.wait()
        return self._returncode is not None

    ready = poll

    def wait(self):
        '''Waits for the process to terminate; will raise a
        :class:`cu.command.ProcessExecutionError` in case of failure.'''
        if self._returncode is not None:
            return
        self._returncode, self._stdout, self._stderr = run_proc(self.proc,
            self._expected_retcode, self._timeout)


class ExecutionModifier(object):
    def __init__(self, retcode=0):
        self.retcode = retcode

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.retcode)

    @classmethod
    def __call__(cls, retcode):
        return cls(retcode)


class BG(ExecutionModifier):
    '''An execution modifier that runs the given command in the background, returning a
    :class:`Future <cu.command.Future>` object. In order to mimic shell syntax, it applies
    when you right-and it with a command. If you wish to expect a different return code
    (other than the normal success indicate by 0), use ``BG(retcode)``. Example::

        future = sleep[5] & BG       # a future expecting an exit code of 0
        future = sleep[5] & BG(7)    # a future expecting an exit code of 7
    '''
    def __rand__(self, executable):
        return Future(executable.popen(), self.retcode)


class FG(ExecutionModifier):
    '''An execution modifier that runs the given command in the foreground, passing it the
    current process' stdin, stdout and stderr. Useful for interactive programs that require
    a TTY. There is no return value.

    In order to mimic shell syntax, it applies when you right-and it with a command.
    If you wish to expect a different return code (other than the normal success indicate by 0),
    use ``BG(retcode)``. Example::

        vim & FG       # run vim in the foreground, expecting an exit code of 0
        vim & FG(7)    # run vim in the foreground, expecting an exit code of 7
    '''
    def __rand__(self, executable):
        executable(retcode=self.retcode, stdin=None, stdout=None, stderr=None)


class CommandNotFound(Exception):
    '''Raised by :func:`local.which <cu.local.LocalSystem.which>` and
    :func:`RemoteMachine.which <cu.remote_machine.RemoteMachine.which>` when a
    command was not found in the system's ``PATH``.'''

    def __init__(self, program, path):
        super(CommandNotFound, self).__init__(program, path)
        self.program = program
        self.path = path


class ProcessExecutionError(Exception):
    '''Represents the failure of a process. When the exit code of a terminated
    process does not match the expected result, this exception is raised by
    :func:`run_proc <cu.command.run_proc>`. It contains the process' return
    code, stdout, and stderr, as well as the command line used to create the
    process (``argv``)
    '''

    def __init__(self, argv, retcode, stdout, stderr):
        super(ProcessExecutionError, self).__init__(argv, retcode, stdout, stderr)
        self.argv = argv
        self.retcode = retcode
        if isinstance(stdout, bytes) and not isinstance(stderr, str):
            stdout = ascii(stdout)
        if isinstance(stderr, bytes) and not isinstance(stderr, str):
            stderr = ascii(stderr)
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        lines = ['Command line: %r' % (self.argv,), 'Exit code: %s' % (self.retcode)]
        lines.append('Stdout:')
        lines.extend(self.stdout.splitlines())
        lines.append('Stderr:')
        lines.extend(self.stderr.splitlines())
        return '\n'.join(lines)


class ProcessTimedOut(Exception):
    '''Raises by :func:`run_proc <cu.command.run_proc>` when a ``timeout`` has
    been specified and it has elapsed before the process terminated.'''

    def __init__(self, msg, argv):
        super(ProcessTimedOut, self).__init__(msg, argv)
        self.argv = argv


class RedirectionError(Exception):
    '''Raised when an attempt is made to redirect an process' standard handle,
    which was already redirected to/from a file.'''
