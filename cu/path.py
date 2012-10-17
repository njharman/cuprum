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
from six.moves import reduce

# TODO:
# path.relpath


from os.path import commonprefix, sameopenfile, samestat


class Path(object):
    '''An abstraction over file system paths.

    Some properties of Path instances:
      - Have all str indexing and methods.
      - Have applicaple stuff from os.path as methods.
      - Are immutable (not enforced).
      - Trailing slash are preserved, multiple are collapsed.
      - Can chain

    Constructors:

      - Path('/') or Path('/', 'var', 'log') or Path(iterable)
      - Path.cwd()
      - Path.common_prefix('/var', Path('/var/log/')) or Path.common_prefix(iterable)
      - Path.common_suffix('/usr/bin', Path('/bin')) or Path.common_suffix(iterable)

    Read-only attributes:

      - size: os.path.getsize()
      - atime: os.path.getatime()
      - ctime: os.path.getctime()
      - mtime: os.path.getmtime()
      - abs:  Absolute version of this path (relative to cwd if necessary)
      - basename: os.path.basename()
      - dirname: like os.path.dirname but respects ``keep_trailing_slash`` value.
      - exists: os.path.exists()
      - isabs: os.path.isabs()
      - isabsolute: alias of isabs
      - isrelative: not isabs
      - isdir: os.path.isdir()
      - isfile: os.path.isfile()
      - islink: os.path.islink()
      - ismount: os.path.ismount()
      - sep: os.path.sep
      - unicode: os.path.supports_unicode_filenames

    Read-write attributes:

      - owner: get / set owner of leaf component
      - group: get / set group of leaf component
      - mode: get / set permissions of leaf component

    '''
    sep = os.path.sep
    unicode = os.path.supports_unicode_filenames
    _str = unicode if os.path.supports_unicode_filenames else str

    @classmethod
    def common_prefix(cls, paths, *bits):
        '''Unlike os.path.commonprefix this compares by path segment.
        '/var/boo, /var/bog returns /var  not /var/bo
        :parameters: One iterable of string and Path instances.
                    Or, two or more string and Path instances.
        :return: new Path()
        '''
        # Support single iterable or bunch of parameters
        if bits:
            paths = (paths, ) + tuple(bits)
        prefix = list()
        # Path.split keeps leading slash, booyah!
        for segments in zip(*(Path(p).split() for p in paths)):
            # All segments equal?
            if not reduce(lambda a, b: a == b and a, segments):
                break
            prefix.append(segments[0])
        if prefix:
            return Path(*prefix)
        else:
            return Path('')

    @classmethod
    def common_suffix(cls, paths, *bits):
        '''Compares by path segment. Trailing slash ignored for comparison.
        :parameters: One iterable of string and Path instances.
                    Or, two or more string and Path instances.
        :return: new Path()
        '''
        def with_slash(path):
            bits = Path(path).split()
            if bits:
                bits.reverse()
                for p in bits[:-1]:
                    yield p
                    yield cls.sep
                yield bits[-1]
        if bits:
            paths = (paths, ) + tuple(bits)
        suffix = list()
        for segments in zip(*(with_slash(p) for p in paths)):
            if not reduce(lambda a, b: a == b and a, segments):
                break
            suffix.append(segments[0])
        if suffix:
            suffix.reverse()
            # Replace trailing slash if all original paths had one.
            if all(p.endswith(cls.sep) for p in paths):
                suffix.append(cls.sep)
            return Path(*suffix)
        else:
            return Path('')

    @classmethod
    def cwd(cls):
        '''Current working directory as Path instance.'''
        if os.path.supports_unicode_filenames:
            return cls(os.getcwdu())
        else:
            return cls(os.getcwd())

    getcwd = cwd

    def __enter__(self):
        '''Context manager.'''
        self.__previous_directory = os.getcwd()
        self.chdir(self._path)

    def __exit__(self):
        '''Context manager.'''
        self.chdir(self.__previous_directory)

    def __init__(self, path, *bits, **kwargs):
        '''Initialize Path from string/unicode, Path, iterator of those, multiple parameters of those
        :param keep_trailing_slash: [True] if True any trailing slashes will be preserved
        :param expand: [True] if True self.expand() called.
        '''
        self._kts = kwargs.get('keep_trailing_slash', True)
        self.__init_path__(path, *bits)

    def __init_path__(self, path, *bits):
        if not isinstance(path, Path):
            # normpath strips trailing '/', unless path == '/'. DO NOT WANT!
            # But, paths like 'path/..' and 'path/../' should eval to '', not '/', not '.'.
            slasher = path.endswith(self.sep) and self._kts
            # normpath turns '' and 'var/..' into '.'. Do not want!
            # But, want ability to create paths like '.' or './file.txt'.
            # So, if user passes, good. Otherwise unfuck normpath's fuckedupness.
            preserve = path == '.'
            path = os.path.normcase(os.path.normpath(path))
            if path == '.' and not preserve:
                path = ''
            # put back trailing slash normpath strips, but not if path reduced to '/'
            elif slasher and path != self.sep:
                path += self.sep
        self._path = self._str(path)
        if bits:
            # TODO: kind of lame
            self._path = self.join(*bits)._path

    def __repr__(self):
        return '<%s(\'%s\')>' % (self.__class__.__name__, self._path)

    def __str__(self):
        return self._path

    def __unicode__(self):
        # Note: Don't be a fascist, maybe user isn't actually doing anything
        # with *this* filesystem.
        #if not self.unicode:
        #    raise ValueError('Unicode paths are not supported by filesystem.')
        return unicode(self._path)

    def __getitem__(self, *args, **kwargs):
        '''String indexing'''
        return self._pathize(self._path.__getitem__(*args, **kwargs))

    def __len__(self):
        return len(self._path)

    def __iter__(self):
        '''Iterate over the files in this directory.'''
        return iter(self.list())

    def __floordiv__(self, expr):
        '''Returns a (possibly empty) list of paths that matched glob-pattern under this path.'''
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
            other = self._str(other)
        return os.path.normcase(self._path) == os.path.normcase(other)

    def __cmp__(self, other):
        return cmp(self._path, other)

    def __hash__(self):
        return hash(self._path)

    def __nonzero__(self):
        return self._path != ''

    def _pathize(self, result):
        '''Dynamically modify return values of methods into Path instances.'''
        if isinstance(result, six.string_types):
            return self.__class__(result, keep_trailing_slash=self._kts)
        elif isinstance(result, list):
            return list(self.__class__(r, keep_trailing_slash=self._kts) for r in result)
        elif isinstance(result, tuple):
            return tuple(self.__class__(r, keep_trailing_slash=self._kts) for r in result)
        else:  # TODO: add iterator handling
            return result

    @property
    def dirname(self):
        '''Dirname of this path, everything before final self.sep.
        Contrast with `parent` and `up`.
        Note: how this interacts with keep_trailing_slash=False.
        See `parent` for something more like os.path.dirname
        If path ends in self.sep dirname == path.
        If path has no self.sep, dirname == ''.
        :return: new Path()
        '''
        if self._path == '' or self._path.endswith(self.sep):
            path = self._path
        else:
            path = os.path.dirname(self._path)
            if path and path != '/' and self._kts:
                path += self.sep
        return self._pathize(path)

    path = dirname  # better name

    @property
    def basename(self):
        '''Basename of this path, everything after final self.sep.
        Note: how this interacts with keep_trailing_slash=False.
        If path ends in self.sep basename is '', which is different than *nix basename.
        :return: new Path()
        '''
        return self._pathize(os.path.basename(self._path))

    filename = basename   # bettername

    @property
    def name(self):
        '''Name of this path, everything before and excluding the rightmost '.' of basename.
        If path ends in self.sep, return ''.
        :return: new Path()
        '''
        base, ext = os.path.splitext(self.basename)
        return self._pathize(base)

    @property
    def extension(self):
        '''Extension of this path, everything after and including the rightmost '.' of basename.
        If path ends in self.sep, return ''.
        If basename has no '.', return ''.
        If basename starts with '.', return ''.
        :return: text
        '''
        base, ext = os.path.splitext(self.basename)
        return self._str(ext)

    @property
    def abs(self):
        '''Absolute version of this path, using cwd for relative paths.
        Unlike os.abspath, '' is returned as '' not '.'
        :return: new Path()
        '''
        if self.startswith(self.sep):
            bits = (self, )
        elif self == '':
            bits = ('', )
        else:
            bits = (os.getcwd(), self)
        # This garbage cause keyword after *args is syntax error in Python 2.5
        lame = self._pathize('')
        lame.__init_path__(*bits)
        return lame

    @property
    def parent(self):
        '''Parent directory of this path.
        Contrast with `dirname` and `up`.
        Parent of file is the directory it is in.
        Parent of '/' is  '/', of '' is ''.
        Relative paths will (eventually) return ''.
        :return: new Path()
        '''
        if self._path:
            return self.join('../')
        else:
            return self._pathize('')

    def up(self, count=1):
        '''"Up" ``count`` parent directories from this path.
        Contrast with `dirname` and `parent`.
        Up from '/' is '/', from '' or 'relative_path' is ''.
        :param count: [1] number of path segments to go up.
        :return: new Path()
        '''
        if count <= 0:
            return self._pathize(self._path)
        bits = self.split()[:-count]
        if bits:
            if self._kts:
                bits.append(self.sep)
            # This garbage cause keyword after *args is syntax error in Python 2.5
            lame = self._pathize('')
            lame.__init_path__(*bits)
            return lame
        elif self.is_absolute:
            return self._pathize(self.sep)
        else:
            return self._pathize('')

    @property
    def exists(self):
        '''True if this path exist and is not a broken link.'''
        return os.path.exists(self._path)

    isreal = exists
    is_real = exists

    @property
    def is_abs(self):
        '''True if this path is absolute, starts with self.sep.'''
        return os.path.isabs(self._path)

    isabs = is_abs
    is_absolute = is_abs

    @property
    def is_relative(self):
        '''True if this path is relative, does not start with self.sep.'''
        return not os.path.isabs(self._path)

    isrelative = is_relative

    @property
    def is_dir(self):
        '''True if this path is a directory.'''
        return os.path.isdir(self._path)

    isdir = is_dir

    @property
    def is_file(self):
        '''True if this path is a regular file.'''
        return os.path.isfile(self._path)

    isfile = is_file

    @property
    def is_link(self):
        '''True if this path is a symbolic link.'''
        return os.path.islink(self._path)

    islink = is_link

    @property
    def is_mount(self):
        '''True if this path is a mount point.'''
        return os.path.ismount(self._path)

    ismount = is_mount

    @property
    def size(self):
        '''Size in bytes of leaf component of this path.'''
        return os.stat(self._path).st_size

    @property
    def atime(self):
        '''Access time of leaf component of this path.'''
        return os.stat(self._path).st_atime

    @property
    def mtime(self):
        '''Modified time of leaf component of this path.'''
        return os.stat(self._path).st_mtime

    @property
    def ctime(self):
        '''Change/creation(win32) time of leaf component of this path.'''
        return os.stat(self._path).st_ctime

    def _get_owner(self):
        stat = self.stat()
        return pwd.getpwuid(stat.st_uid)[0]

    def _set_owner(self, owner):
        if ':' in owner:
            owner, self.group = owner.split(':', 1)
        log.info('Owner %s set on %s' % (owner, self._path))
        self.chown(owner)

    owner = property(_get_owner, _set_owner, doc='Owner of leaf component of this path.')

    def _get_group(self):
        stat = self.stat()
        return grp.getgrgid(stat.st_gid)[0]

    def _set_group(self, group):
        self.chown(group=group)

    group = property(_get_group, _set_group, doc='Group of leaf component of this path.')

    def _get_mode(self):
        stat = self.stat()
        return stat.st_mode  # TODO: translate this into something that makes sense

    def _set_mode(self, flags):
        self.chmod(flags)

    mode = property(_get_mode, _set_mode, doc='Mode of leaf component of this path.')

    def same_file(self, path):
        '''os.path.samefile'''
        return os.path.realpath(self._path, path)

    samefile = same_file  # what os.path calls it

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

    def _split(self, sep, maxsplit, func):
        if sep is None:
            sep = self.sep
        if not self._path:
            return ()
        bits = func(sep, maxsplit)
        if bits[0] == '':
            bits[0] = self.sep
        return self._pathize([b for b in bits if b])

    def rsplit(self, sep=None, maxsplit=-1):
        '''Right split on self.sep by default.
        Include leading self.sep. Remove all '' path components.
        For os.path.split behavior see split_path.
        :param sep: [self.sep]
        :param maxsplit: [unlimited]
        :return: list of Path() instances
        '''
        return self._split(sep, maxsplit, self._path.rsplit)

    def split(self, sep=None, maxsplit=-1):
        '''Split on self.sep by default.
        Include leading self.sep. Remove all '' path components.
        For os.path.split behavior see split_path.
        :param sep: [self.sep]
        :param maxsplit: [unlimited]
        :return: list of Path() instances
        '''
        return self._split(sep, maxsplit, self._path.split)

    def split_path(self):
        '''os.path.split on this path.
        :return: (Path(root), Path(tail))
        '''
        return self._pathize(os.path.split(self._path))

    splitpath = split_path  # api consistancy

    def split_drive(self):
        '''os.path.splitdrive on this path.
        :return: (Path(drive), Path(tail))
        '''
        return self._pathize(os.path.splitdrive(self._path))

    splitdrive = split_drive  # what os.path names it

    def split_extension(self):
        '''os.path.splitext on this path.
        :return: (Path(root), extension)
        '''
        base, ext = os.path.splitext(self._path)
        return (self._pathize(base), ext)

    splitext = split_extension  # what os.path names it

    def strip_extension(self, match=None):
        '''Strip one extension, return rest.
        If no extensions return entire path.
        Note: Can't tell difference between file with dots and real extension.
        :param match: list of extensions (with or without '.') to strip, others ignored.
        :return: new Path()
        '''
        if match is None:
            return self.split_extension()[0]
        else:
            for m in match:
                if self._path.endswith(m):
                    return self._pathize(self._path[:-len(m)])
        return self._pathize(self._path)

    if hasattr(os.path, 'splitunc'):
        def split_unc(self):
            '''os.path.splitunc on this path.
            :return: (Path(unc), Path(unc))
            '''
            return self._pathize(os.path.splitunc(self._path))

        splitunc = split_unc  # what os.path names it

    def join(self, *bits):
        '''Join self with any number of path bits.
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
        proper_bits = head + [self._str(b.lstrip(self.sep)) for b in tail]
        return self._pathize(os.path.join(*proper_bits))

    def join_path(self, *bits):
        '''os.path.join
        :return: new Path()
        '''
        return self._pathize(os.path.join(*bits))

    joinpath = join_path  # api consistancy

    def abspath(self):
        '''os.path.abspath'''
        return self._pathize(os.path.abspath(self._path))

    def realpath(self):
        '''os.path.realpath'''
        return self._pathize(os.path.realpath(self._path))

    def normpath(self):
        '''All Path instances are normalized on construction, os.path.normpath'''
        return self._pathize(os.path.normpath(self._path))

    def normcase(self):
        '''All Path instances are normalized on construction, os.path.normcase'''
        return self._pathize(os.path.normcase(self._path))

    def expand(self):
        '''Expands any environment variables and home shortcuts in path
        (like ``os.path.expanduser`` after ``os.path.expandvars``)
        :returns: new expanded Path()
        '''
        return self._pathize(os.path.expanduser(os.path.expandvars(self._path)))

    def expanduser(self):
        '''Probably wanna use `expand` os.path.expanduser.'''
        return self._pathize(os.path.expanduser(self._path))

    def expandvars(self):
        '''Probably wanna use `expand` os.path.expandvars.'''
        return self._pathize(os.path.expandvars(self._path))

    def glob(self, pattern):
        '''Expand pattern as glob.glob rooted at this path.
        :return: (possibly empty) generator of Path()s matching glob
        '''
        for path in glob.glob(self._str(self / pattern)):
            yield self._pathize(path)

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
            os.symlink(self._path, self._str(link))
        else:
            log.info('Hardlink to %s' % (self._path, ))
            os.link(self._path, self._str(link))
        return self._pathize(link)

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
        dest = self._pathize(dest)
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
        dest = self._pathize(dest)
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
    remove = delete  # and one just cause

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
        try:
            self.chdir(directory)
            yield
        finally:
            self.chdir(previous)
