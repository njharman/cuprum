import os
import functools
from contextlib import contextmanager

from cu.path import Path


class Environment(object):
    '''Machine's environment; exposes a dict-like interface.
    TODO:
    '''
    CASE_SENSITIVE = os.name != 'nt'

    def __init__(self, environment=os.environ, path_factory=Path):
        '''
        :param enviroment: Dictionary like object, os.environ is default.
        :param path_factory: Path() or the like.
        '''
        # os.environ already takes care of upper'ing on windows
        self._environment = environment
        self._path_factory = path_factory
        if os.name == 'nt' and 'HOME' not in self and self.home is not None:
            self['HOME'] = self.home

    def __getattr__(self, name):
        return getattr(self._environment, name)

    def __iter__(self):
        return iter(self._environment)

    def __hash__(self):
        raise TypeError('unhashable type')

    def __len__(self):
        return len(self._environment)

    def __contains__(self, name):
        '''Environment variable in current environment?'''
        if not self.CASE_SENSITIVE:
            name = name.upper()
        return name in self._environment

    def __getitem__(self, name):
        '''Environment variable from current environment.'''
        if not self.CASE_SENSITIVE:
            name = name.upper()
        return self._environment[name]

    def __setitem__(self, name, value):
        '''Sets environment variable in current environment.'''
        if not self.CASE_SENSITIVE:
            name = name.upper()
        self._environment[name] = str(value)

    def __delitem__(self, name):
        '''Deletes environment variable from current environment.'''
        if not self.CASE_SENSITIVE:
            name = name.upper()
        del self._environment[name]

    def get(self, name, *default):
        if not self.CASE_SENSITIVE:
            name = name.upper()
        return self._environment.get(name, *default)

    def update(self, **kwargs):
        '''Updates the environment.'''
        proper = dict()
        if self.CASE_SENSITIVE:
            for k, v in kwargs.items():
                proper[k] = str(v)
        else:
            for k, v in kwargs.items():
                proper[k.upper()] = str(v)
        self._environment.update(**proper)

    def as_dict(self):
        '''Environment as a real dictionary.'''
        return dict((k, str(v)) for k, v in self._environment.items())

    @property
    def path(self, safe=False):
        '''The system's ``PATH`` (as an easy-to-manipulate list).
        Returned object will update environment variable PATH.  But, unless
        safe=True changes to PATH from other sources will not be noticed.
        :param safe: if True, PATH env var will be reread prior to every operation.
        '''
        return SystemPathList(self._environment, self._path_factory, safe)

    @property
    def user(self):
        '''Username from environment or ``None`` if it is not set.'''
        if 'USER' in self:
            return self['USER']
        elif 'USERNAME' in self:
            return self['USERNAME']
        return None

    def _get_home(self):
        if 'HOME' in self:
            return self._path_factory(self['HOME'])
        elif 'USERPROFILE' in self:
            return self._path_factory(self['USERPROFILE'])
        elif 'HOMEPATH' in self:
            return self._path_factory(self.get('HOMEDRIVE', ''), self['HOMEPATH'])
        return None

    def _set_home(self, p):
        if 'HOME' in self:
            self['HOME'] = str(p)
        elif 'USERPROFILE' in self:
            self['USERPROFILE'] = str(p)
        elif 'HOMEPATH' in self:
            self['HOMEPATH'] = str(p)
        else:
            self['HOME'] = str(p)

    home = property(_get_home, _set_home)

    def expand(self, text):
        '''Expands any environment variables and home shortcuts found in ``text``
        (like ``os.path.expanduser`` after ``os.path.expandvars``)
        :param text: string containing environment variables (as ``$FOO``) or
             home shortcuts (as ``~/.bashrc``)
        :returns: expanded string
        '''
        return os.path.expanduser(os.path.expandvars(text))

    @contextmanager
    def __call__(self, **kwargs):
        '''Context manager for temporal modifications of the environment.
        Any time you enter the context, a copy of the old environment is stored,
        and then restored, when the context exits.
        :param kwargs: ENVIRONMENT_VAR => value
        '''
        prev = self._environment.copy()
        self.update(**kwargs)
        try:
            yield
        finally:
            self.clear()
            self.update(**prev)


class SystemPathList(list):
    '''Environment Variable ``PATH`` (as an easy-to-manipulate list of Path() instances).'''
    sep = os.path.pathsep  # path sep is what sperates elements of PATH, not a slash.

    def __init__(self, environment=os.environ, path_factory=Path, safe=False):
        '''
        :param enviroment: Dictionary like object from/to which PATH is loaded/dumped.
        :param path_factory: Path() or the like.
        :param safe: if True, PATH env var will be reread prior to every operation.
        '''
        self._environment = environment
        self._path_factory = lambda *a, **k: path_factory(*a, keep_trailing_slash=False, **k)
        self._safe = safe
        self.load()

    def wrapper(func):
        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            if self._safe:
                self.load()
            return func(self, *args, **kwargs)
        return inner

    @wrapper
    def __contains__(self, path):
        return super(SystemPathList, self).__contains__(self._path_factory(path))

    @wrapper
    def __getitem__(self, i):
        return super(SystemPathList, self).__getitem__(i)

    @wrapper
    def __setitem__(self, i, value):
        super(SystemPathList, self).__setitem__(i, value)
        self.dump()

    @wrapper
    def append(self, path):
        super(SystemPathList, self).append(self._path_factory(path))
        self.dump()

    @wrapper
    def extend(self, paths):
        super(SystemPathList, self).extend(self._path_factory(p) for p in paths)
        self.dump()

    def count(self):
        raise NotImplementedError

    @wrapper
    def index(self, path, i, j):
        return super(SystemPathList, self).index(self._path_factory(path), i, j)

    @wrapper
    def insert(self, i, path):
        super(SystemPathList, self).insert(i, self._path_factory(path))
        self.dump()

    @wrapper
    def pop(self, i=-1):
        super(SystemPathList, self).pop(i)
        self.dump()

    @wrapper
    def remove(self, path):
        super(SystemPathList, self).remove(self._path_factory(path))
        self.dump()

    def reverse(self):
        raise NotImplementedError

    def sort(self):
        raise NotImplementedError

    def load(self, text=None):
        '''From text or Environment.'''
        if text is None:
            text = self._environment.get('PATH', '')
        self[:] = [self._path_factory(p) for p in text.split(self.sep) if p]

    def dump(self):
        '''To environment.'''
        self._environment['PATH'] = self.sep.join(str(p) for p in self)
