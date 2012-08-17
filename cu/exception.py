import six

if not six.PY3:
    bytes = str
    ascii = repr


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
