'''Path

os.path really pisses me off. It's full of suprising behavior:

  - normpath('') == '.'
  - normpath('fu/') == 'fu'
  - normpath('/') == '/'
  - join('/foo/bar', '/wtf') = '/wtf'
  - join('file.txt', '') = 'file.txt/'
'''
import os
import pwd
import grp
import glob
import shutil
from contextlib import contextmanager

import logging
log = logging.getLogger('cu.path')


class Path(object):
    '''An abstraction over file system paths.

    Some properties of Path instances:
      - Have all str indexing and methods.
      - Have applicaple stuff from os.path as methods.
      - Are immutable (not enforced).
      - Trailing slash are preserved, multiple are collapsed.

    ::

      root = Path('/')
      log = Path('/', 'var', 'log')

    os.path.normpath (empty paths and trailing slashes are preserved) and
    os.path.normcase are applied to path when instantiated.

    Class attributes
      - sep: os.path.sep

    '''
    sep = os.path.sep

    def __init__(self, path, *bits, **kwargs):
        '''
        :param keep_trailing_slash: [True] if True any trailing slashes will be preserved
        '''
        self._kts = kwargs.get('keep_trailing_slash', True)
        self.__init_path__(path, *bits)

    def __init_path__(self, path, *bits):
        if not isinstance(path, Path):
            trailing_slash = path.endswith(self.sep) and self._kts
            if path:  # don't let normpath turn '' into '.'
                path = os.path.normcase(os.path.normpath(path))
            # put back trailing slash normpath strips, but not if path reduced to '/'
            if trailing_slash and path != self.sep:
                path += self.sep
        self._path = str(path)
        if bits:
            # kind of lame
            self._path = self.join(*bits)._path

    def __str__(self):
        return self._path

    def __repr__(self):
        return '<%s(\'%s\')>' % (self.__class__.__name__, self._path)

    def __getitem__(self, *args, **kwargs):
        return self.__class__(self._path.__getitem__(*args, **kwargs), keep_trailing_slash=self._kts)

    def __len__(self):
        return len(self._path)

    def __iter__(self):
        '''Iterate over the files in this directory.'''
        return iter(self.list())

    def __floordiv__(self, expr):
        '''Returns a (possibly empty) list of paths that matched the glob-pattern under this path.'''
        return self.glob(expr)

    def __div__(self, other):
        '''Joins two paths.'''
        return self.join(other)

    __truediv__ = __div__

    def __eq__(self, other):
        # Trailing slash is significant.  /foo/bar/ != /foo/bar
        if isinstance(other, Path):
            other = other._path
        elif not isinstance(other, basestring):
            other = str(other)
        return os.path.normcase(self._path) == os.path.normcase(other)

    def __cmp__(self, other):
        return cmp(self._path, other)

    def __hash__(self):
        return hash(self._path)

    def __nonzero__(self):
        return self._path != ''

    def _pathize(self, result):
        '''Dynamically modify returns of string funcs into Path instances.'''
        if isinstance(result, basestring):
            return self.__class__(result, keep_trailing_slash=self._kts)
        elif isinstance(result, list):
            return list(self.__class__(r, keep_trailing_slash=self._kts) for r in result)
        elif isinstance(result, tuple):
            return tuple(self.__class__(r, keep_trailing_slash=self._kts) for r in result)
        else:  # TODO: add iterator handling
            return result

    @property
    def basename(self):
        '''The basename component of this path.
        :return: str
        '''
        return os.path.basename(self._path)

    @property
    def dirname(self):
        '''The dirname component of this path.
        :return: new Path(dest)
        '''
        return self.__class__(os.path.dirname(self._path), keep_trailing_slash=self._kts)

    @property
    def owner(self):
        '''The owner of leaf component of this path.'''
        stat = self.stat()
        return pwd.getpwuid(stat.st_uid)[0]

    @owner.setter
    def owner(self, owner):
        self.chown(owner)

    @property
    def group(self):
        '''The group of leaf component of this path.'''
        stat = self.stat()
        return grp.getgrgid(stat.st_gid)[0]

    @group.setter
    def group(self, group):
        self.chown(group=group)

    def isdir(self):
        '''``True`` if this path is a directory, ``False`` otherwise.'''
        return os.path.isdir(self._path)

    def isfile(self):
        '''``True`` if this path is a regular file, ``False`` otherwise.'''
        return os.path.isfile(self._path)

    def exists(self):
        '''``True`` if this path exists, ``False`` otherwise.'''
        return os.path.exists(self._path)

    def stat(self):
        '''Same as os.stat(self)'''
        return os.stat(self._path)

    def split(self, sep=None):
        '''Split on self.sep by default.'''
        if sep is None:
            sep = self.sep
        return self._pathize(self._path.split(sep))

    def join(self, *bits):
        '''Returns new Path, self joined with any number of path bits.
        '''
        # os.path.join has suprising qualities;
        # e.g. join("/foo/bar", "/wtf") returns "/wtf". Seriously WTFwaffles!?
        # So, we strip left slash from each bit beyond first and '/'.join() them
        # later.  But first we drop all empty paths, including self._path.
        good_bits = [b for b in bits if b]
        if self._path:
            head = [self._path, ]
            tail = good_bits
        elif good_bits:
            head = [good_bits[0], ]
            tail = good_bits[1:]
        else:
            return self.__class__('', keep_trailing_slash=self._kts)
        proper_bits = head + [str(b.lstrip(self.sep)) for b in tail]
        return self.__class__(os.path.join(*proper_bits), keep_trailing_slash=self._kts)

    def glob(self, pattern):
        '''Returns a (possibly empty) list of Paths that matched the
        glob-pattern under this path.
        '''
        return [self.__class__(path, keep_trailing_slash=self._kts) for path in glob.glob(str(self / pattern))]

    def up(self, count=1):
        '''Go up in ``count`` directories (the default is 1).
        :return: new Path()
        '''
        return self.join('../' * count)

    def walk(self, filter=lambda p: True):
        '''Traverse all (recursive) sub-elements under this directory, that
        match the given filter.  By default, the filter accepts everything; you
        can provide a custom filter function that takes a path as an argument
        and returns a boolean.
        .'''
        for p in self.list():
            if filter(p):
                yield p
                if p.isdir():
                    for p2 in p.walk():
                        yield p2

    def list(self):
        '''Returns list of Paths or single Path if file.'''
        if self.isfile():
            return [self, ]
        return [self / file for file in os.listdir(self._path)]

    def chdir(self):
        '''Changes current working directory to self.'''
        log.debug('Chdir to %s', self._path)
        os.chdir(self._path)

    def move(self, dest, force=False):
        '''Moves this path to a different location.
        :return: new Path(dest)
        '''
        dest = self.__class__(dest, keep_trailing_slash=self._kts)
        if force:
            dest.delete()
        shutil.move(self._path, dest._path)
        return dest

    def copy(self, dest, force=False):
        '''Copies this path (recursively, if a directory) to the destination
        path.
        :return: new Path(dest)
        '''
        dest = self.__class__(dest, keep_trailing_slash=self._kts)
        if force:
            dest.delete()
        if self.isdir():
            shutil.copytree(self._path, dest)
        else:
            shutil.copy2(self._path, dest)
        return dest

    def delete(self):
        '''Deletes this path (recursively, if a directory).'''
        if not self.exists():
            return
        if self.isdir():
            shutil.rmtree(self._path)
        else:
            os.remove(self._path)

    # Unixisms
    ls = list
    cd = chdir
    mv = move
    cp = copy
    rm = delete
    # and one just cause
    remove = delete

    def touch(self, stamp=None, atime_only=False, mtime_only=False):
        '''Sets atime and mtime to 'stamp' of leaf component of this path,
        creating file if necessary.  Defaults to now().
        '''
        if stamp is None:
            stamp = time.time()

    def mkdir(self):
        '''Creates directory; if the directory already exists,
        silently ignore.'''
        if not self.exists():
            os.makedirs(self._path)

    def chown(self, owner='', group='', uid='', gid='', recursive=False):
        '''Change ownership of leaf component of this path.'''
        gid = str(gid)  # str so uid 0 (int) isn't seen as False
        uid = str(uid)
        args = list()
        if recursive:
            args.append('-R')
        if uid:
            owner = uid
        if gid:
            group = gid
        if group:
            owner = '%s:%s' % (owner, group)
        args.append(owner)
        args.append(self._path)
        # recursive is a pain using os.chown
        from local import local
        local['chown'](*args)

    def chmod(self, mode='', recursive=False):
        '''Change file mode of leaf component of this path.'''
        pass

    def open(self, mode='r'):
        '''Opens this path as a file.'''
        return open(self._path, mode)

    def read(self):
        '''Returns the contents of this file.'''
        with self.open() as f:
            return f.read()

    def write(self, data):
        '''Writes the given data to this file.'''
        with self.open('w') as f:
            f.write(data)

    def rename(self, newname):
        '''Renames this path to the ``new name`` (only the basename is changed).'''
        return self.move(self.up() / newname)

    @contextmanager
    def __call__(self):
        '''Context manager ``chdir`` into self and back to the original
        directory; much like ``pushd``/``popd``.
        '''
        prev = os.getcwd()
        self.chdir()
        try:
            yield
        finally:
            self.chdir(prev)


# Facade str.
for attr in dir(str):
    if not hasattr(Path, attr):
        method = getattr(str, attr)

        def closure(method):
            def string_method(self, *args, **kwargs):
                return self._pathize(method(self._path, *args, **kwargs))
            return string_method
        setattr(Path, attr, closure(method))


class CWD(Path):
    '''Current Working Directory manipulator.
    Some properties of CWD instances:
      - Path subclass
      - Are mutable
    '''
    def __init__(self, path=None, *bits, **kwargs):
        if path is None:
            path = os.getcwd()
        super(CWD, self).__init__(path, *bits, **kwargs)

    def __hash__(self):
        raise TypeError('unhashable type')

    def chdir(self, directory):
        '''Changes current working directory and self to directory.
        :param directory: Relative unless starting with slash.
        '''
        os.chdir(directory)
        self.__init_path__(os.getcwd())

    @contextmanager
    def __call__(self, directory):
        '''A context manager used to ``chdir`` into a directory and then
        ``chdir`` back to the previous location; much like ``pushd``/``popd``.
        :param directory: The destination director (a string or a ``Path``)
        '''
        previous = self._path
        self.chdir(directory)
        try:
            yield
        finally:
            self.chdir(previous)
