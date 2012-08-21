'''Path

os.path really pisses me off. It's full of suprising behavior:

  - normpath('') == '.'
  - normpath('fu/') == 'fu' vs normpath('/') == '/'
  - join('/foo/bar', '/wtf') = '/wtf'
  - join('file.txt', '') = 'file.txt/'
'''
from __future__ import with_statement
import os
import pwd
import grp
import glob
import shutil
import contextlib
import logging
log = logging.getLogger('cu.path')
# log.info operations that change filesystem, otherwise quiet

import six

# TODO:
# path.realpath
# path.relpath
# path.samefile


class Path(object):
    '''An abstraction over file system paths.

    Some properties of Path instances:
      - Have all str indexing and methods.
      - Have applicaple stuff from os.path as methods.
      - Are immutable (not enforced).
      - Trailing slash are preserved, multiple are collapsed.
      - Can chain

    ::

      root = Path('/')
      log = Path('/', 'var', 'log')

    Class attributes
      - sep: os.path.sep
      - unicode: os.path.supports_unicode_filenames
    '''
    sep = os.path.sep
    unicode = os.path.supports_unicode_filenames

    @classmethod
    def commonprefix(cls, paths):
        '''os.path.commonprefix classmethod'''
        return os.path.commonprefix(str(p) for p in paths)

    def __init__(self, path, *bits, **kwargs):
        '''
        :param keep_trailing_slash: [True] if True any trailing slashes will be preserved
        :param expand: [True] if True expand() called.
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
        elif not isinstance(other, six.string_types):
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
        if isinstance(result, six.string_types):
            return self.__class__(result, keep_trailing_slash=self._kts)
        elif isinstance(result, list):
            return list(self.__class__(r, keep_trailing_slash=self._kts) for r in result)
        elif isinstance(result, tuple):
            return tuple(self.__class__(r, keep_trailing_slash=self._kts) for r in result)
        else:  # TODO: add iterator handling
            return result

    @property
    def abs(self):
        '''Absolute version of this path, using cwd if necessary.
        '' is returned as '' not cwd.
        :return: new Path()
        '''
        if self.startswith(self.sep):
            bits = (self, )
        elif self == '':
            bits = ('', )
        else:
            bits = (os.getcwd(), self)
        # This garbage is cause keyword after *args is syntax error in Python 2.5
        lame = self.__class__('', keep_trailing_slash=self._kts)
        lame.__init_path__(*bits)
        return lame

    @property
    def basename(self):
        '''The basename component (everything after final slash) of this path.
        If path ends in slash basename is '', different than unix basename.
        :return: str
        '''
        return os.path.basename(self._path)

    @property
    def dirname(self):
        '''The dirname component (everything before final slash) of this path.
        If path ends in slash dirname == path.
        :return: new Path()
        '''
        return self.__class__(os.path.dirname(self._path), keep_trailing_slash=self._kts)

    @property
    def exists(self):
        '''Does this path exists and is not a broken link.'''
        return os.path.exists(self._path)

    @property
    def isabs(self):
        '''Is this path is absolute.'''
        return os.path.isabs(self._path)

    @property
    def isabsolute(self):
        '''Is this path is absolute.'''
        return os.path.isabs(self._path)

    @property
    def isrelative(self):
        '''Is this path is relative.'''
        return not os.path.isabs(self._path)

    @property
    def isdir(self):
        '''Is this path is a directory.'''
        return os.path.isdir(self._path)

    @property
    def isfile(self):
        '''Is this path is a regular file.'''
        return os.path.isfile(self._path)

    @property
    def islink(self):
        '''Is this path is a symbolic link.'''
        return os.path.islink(self._path)

    @property
    def ismount(self):
        '''Is this path is a mount point.'''
        return os.path.ismount(self._path)

    @property
    def atime(self):
        '''Access time of leaf component of this path.'''
        return os.path.getatime(self._path)

    @property
    def mtime(self):
        '''Modified time of leaf component of this path.'''
        return os.path.getmtime(self._path)

    @property
    def ctime(self):
        '''Change/creattion(win32) time of leaf component of this path.'''
        return os.path.getctime(self._path)

    @property
    def size(self):
        '''Size in bytes of leaf component of this path.'''
        return os.path.getsize(self._path)

    def _get_owner(self):
        stat = self.stat()
        return pwd.getpwuid(stat.st_uid)[0]

    def _set_owner(self, owner):
        if ':' in owner:
            owner, self.group = owner.split(':', 1)
        log.info('Owner %s set on %s' % (owner, self._path))
        self.chown(owner)

    owner = property(_get_owner, _set_owner, doc='owner of leaf component of this path.')

    def _get_group(self):
        stat = self.stat()
        return grp.getgrgid(stat.st_gid)[0]

    def _set_group(self, group):
        self.chown(group=group)

    group = property(_get_group, _set_group, doc='group of leaf component of this path.')

    def _get_mode(self):
        stat = self.stat()
        return stat.st_mode # TODO: translate this into something that makes sense

    def _set_mode(self, flags):
        self.chmod(flags)

    mode = property(_get_mode, _set_mode, doc='file mode of leaf component of this path.')

    def stat(self, followlinks=True):
        '''Same as os.stat(self).
        :param followlinks: [True] if False use os.lstat
        '''
        if followlinks:
            return os.stat(self._path)
        else:
            return os.lstat(self._path)

    def statfs(self):
        '''Same as os.statvfs(self)'''
        return os.statvfs(self._path)

    statvfs = statfs

    def split(self, sep=None):
        '''Split on self.sep by default.
        Include leading os.sep. Remove any final ''.
        For os.path.split behavior see split_path
        '''
        if sep is None:
            sep = self.sep
        bits = self._path.split(sep)
        if bits[0] == '':
            bits[0] = os.sep
        return self._pathize(bits)

    def split_drive(self):
        '''os.path.splitdrive on this path.
        :return: (drive, tail)
        '''
        return self._pathize(os.path.splitdrive(self._path))

    splitdrive = split_drive  # what it is called in os.path module

    def split_extension(self):
        '''os.path.splitext on this path.
        :return: (root, extension)
        '''
        return self._pathize(os.path.splitdrive(self._path))

    splitext = split_extension  # what it is called in os.path module
    split_ext = split_extension

    def split_path(self):
        '''os.path.split on this path.
        :return: (root, tail)
        '''
        return self._pathize(os.path.split(self._path))

    splitpath = split_path  # for api consistancy

    def split_unc(self):
        '''os.path.splitdrive on this path.
        :return: (unc, rest)
        '''
        return self._pathize(os.path.splitunc(self._path))

    splitunc = split_unc  # what it is called in os.path module

    def join(self, *bits):
        '''join self with any number of path bits.
        For os.path.join behavior see join_path.
        :return: new Path()
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

    def join_path(self, *bits):
        '''os.path.join
        :return: new Path()
        '''
        return self.__class__(os.path.join(*bits), keep_trailing_slash=self._kts)

    joinpath = join_path  # api consistancy

    def expand(self):
        '''Expands any environment variables and home shortcuts in path
        (like ``os.path.expanduser`` after ``os.path.expandvars``)
        :returns: expanded string
        '''
        return self.__class__(os.path.expanduser(os.path.expandvars(self._path)), keep_trailing_slash=self._kts)

    def glob(self, pattern):
        '''Expand pattern as glob.glob rooted at this path.
        :return: (possibly empty) list of Path()s matching glob
        '''
        return [self.__class__(path, keep_trailing_slash=self._kts) for path in glob.glob(str(self / pattern))]

    def up(self, count=1):
        '''Go up in ``count`` directories (the default is 1).
        :return: new Path()
        '''
        return self.join('../' * count)

    def walk(self, topdown=True, onerror=None, followlinks=False):
        '''os.walk, a generator.
        :return: (dirpath, dirnames, filenames)
        '''
        for x in os.walk(self._path, topdown, onerror, followlinks):
            yield x

    def walk_iter(self, filter=lambda p: True):
        '''Yield all (recursive) sub-elements under this directory, that
        match the given filter.  By default, the filter accepts everything; you
        can provide a custom filter function that takes a path as an argument
        and returns a boolean.
        .'''
        # TODO: non-recursive implementation (python's stack not infinite)
        for p in self.list():
            if filter(p):
                yield p
                if p.isdir:
                    for p2 in p.walk():
                        yield p2

    walkiter = walk_iter  # for api consistancy

    def walk_path(self, visit, arg=None):
        '''os.path.walk Does not exist Python >= 3.x
        :param visit: func(arg, dirname, names)
        :param arg: [None] passed to visit
        :return: self (for chaining)
        '''
        os.path.walk(self._path, visit, arg)
        return self

    walkpath = walk_path  # for api consistancy

    def readlink(self):
        '''Path this symbolic link points to.
        Error if self is not a symbolic link
        :return: relative or absolute Path()
        '''
        return os.readlink(self._path)

    def link(self, link, force=False, symbolic=False):
        '''Create link to this path.
        :param force: [False] remove any existing file, directory or link.
        :param symbolic: [False] if True hard link, else symbolic
        :return: Path(link)
        '''
        if force:
            Path(link).delete()
        if symbolic:
            log.info('Symlink to %s' % (self._path, ))
            os.symlink(self._path, str(link))
        else:
            log.info('Hardlink to %s' % (self._path, ))
            os.link(self._path, str(link))
        return self.__class__(link, keep_trailing_slash=self._kts)

    def hardlink(self, link, force=False):
        '''Create hard link to this path.
        No error if link exists
        :param force: [False] remove any existing file, directory or link.
        :return: Path(link)
        '''
        return self.link(link, force, symbolic=False)

    def symlink(self, link, force=False):
        '''Create symbolic link to this path.
        :param force: [False] remove any existing file, directory or link.
        :return: Path(link)
        '''
        return self.link(link, force, symbolic=True)

    def list(self):
        '''Listing of entries in this path.
        If this path represents file only it returnedk.
        :return: list of Path()s'''
        if self.isfile:
            return [self, ]
        return [self / file for file in os.listdir(self._path)]

    def chdir(self):
        '''Changes current working directory to this path.
        :return: self (for chaining)
        '''
        log.info('Chdir to %s' % (self._path, ))
        os.chdir(self._path)
        return self

    def copy(self, dest, force=False, symlinks=False):
        '''Copies this path (recursively, if a directory) to the destination.
        path.
        unless force=True.
        :param force: [False] existing dest is deleted
        :parm symlinks: [False] passed to shutil.copytree
        :return: new Path(dest)
        '''
        dest = self.__class__(dest, keep_trailing_slash=self._kts)
        if force:
            dest.delete()
        log.info('Copy to %s' % (self._path, ))
        if self.isdir:
            shutil.copytree(self._path, dest, symlinks)
        else:
            shutil.copy2(self._path, dest)
        return dest

    def move(self, dest, force=False):
        '''Moves this path to a different location.
        :param force: delete any existing dest.
        :return: new Path(dest)
        '''
        dest = self.__class__(dest, keep_trailing_slash=self._kts)
        if force:
            dest.delete()
        log.info('Move to %s' % (self._path, ))
        shutil.move(self._path, dest._path)
        return dest

    def rename(self, newname, force=False):
        '''Renames leaf to ``new name`` (only the basename is changed).
        :param force: delete any existing dest.
        :return: new Path()
        '''
        return self.move(self.up() / newname, force)

    def delete(self):
        '''Deletes this path (recursively, if a directory).
        :return: self (for chaining)
        '''
        if self.exists:
            log.info('Delete %s' % (self._path, ))
            if self.isdir:
                shutil.rmtree(self._path)
            else:
                os.remove(self._path)
        return self

    # Unixisms
    ls = list
    ln = symlink  # ln -s
    cd = chdir
    cp = copy
    mv = move
    rm = delete
    remove = delete # and one just cause

    def fifo(self, mode=666):
        '''os.mkfifo
        :param mode: [666]
        '''
        os.mkfifo(self._path, mode)
        return self

    mkfifo = fifo  # what it is called in os module

    # rare enough to not name it 'node'
    def mknode(self, mode=600, device=0, major=None, minor=None):
        '''os.mknod
        :param mode: [600]
        :param major: use os.makedev to create device number
        :param minor: use os.makedev to create device number
        '''
        if major is not None and minor is not None:
            device = os.makeddev(major, minor)
        os.mknod(self._path, mode, device)
        return self

    mknod = mknode  # what it is called in os module

    def touch(self, stamp=None, atime=True, mtime=True):
        '''Sets atime and mtime to 'stamp' of leaf component of this path,
        creating file if necessary.
        :param stamp: [now()] seconds since epoch
        :param atime: [True] set accessed time to stamp
        :param mtime: [True] set modified time to stamp
        :return: self (for chaining)
        '''
        if not self.exists:
            with open(self._path, 'w') as fh:
                fh.write('')
        if stamp is None:
            times = None
        else:
            # annoyingly Python requires times to be set together...
            if atime:
                _atime = stamp
            else:
                _atime = os.stat(self._path).st_atime
            if mtime:
                _mtime = stamp
            else:
                _mtime = os.stat(self._path).st_mtime
            times = (_atime, _mtime)
        log.info('Touch %s %s' % (stamp, self._path))
        os.utime(self._path, times)
        return self

    def mkdir(self, force=False):
        '''Creates directory.
        Silently ignore existing directory, file, or link.
        :param force: [False] remove any existing file, directory or link.
        :return: self (for chaining)
        '''
        if force:
            self.delete()
        if not self.exists:
            log.info('Mkdir %s' % (self._path, ))
            os.makedirs(self._path)
        return self

    def chown(self, owner='', group='', recursive=False):
        '''Change ownership of leaf component of this path.
        :param owner: username or user id.  Also, user:group
        :param group: groupname or group id
        :param recursive: [False] Apply ownership recursively
        :return: self (for chaining)
        '''
        owner = str(owner)  # str so uid 0 (int) isn't seen as False
        group = str(group)
        args = list()
        if recursive:
            args.append('-R')
        if group:
            owner = '%s:%s' % (owner, group)
        args.append(owner)
        args.append(self._path)
        log.info('Chown %s %s' % (owner, self._path))
        # TODO: native version not using chown
        from cu import local
        local['chown'](*args)
        return self

    def chmod(self, mode, recursive=False):
        '''Change file mode of leaf component of this path.
        :param mode: Any mode recognized by /bin/chown
        :param recursive: [False] Apply mode recursively
        :return: self (for chaining)
        '''
        mode = str(mode)
        args = list()
        if recursive:
            args.append('-R')
        args.extend(mode.split())
        args.append(self._path)
        log.info('Chmod %s %s' % (mode, self._path))
        # TODO: native version not using chown
        from cu import local
        local['chmod'](*args)
        return self

    @contextlib.contextmanager
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


# Facade str methods.
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

    @contextlib.contextmanager
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
