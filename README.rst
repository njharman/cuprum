Cuprum
======
Awesome path/file operations and "subprocess for `Unix Daddy`_'s".

A fork of Plumbum_ with bits of PBS_ (sh.py), path.py_ and anything else that
is within the goals_.

Python path/file operations are strewn about the standard library.
Cuprum pulls all these into ``Path`` class, makes existing functionality
simpler (e.g ``delete`` recursive, no error if missing vs ``os.remove`` +
``os.rmdir`` + ``os.removedirs`` + ``shutil.rmtree``) and removes some
surprises e.g. ``os.path.join("/foo/bar", "/wtf")`` returns "/wtf".

One of the reasons I (and many) still reach for Bash is how convenient it is to
run, redirect in/out/err, and chain the scores of command line tools Unix provides.
os.system is the opposite of convenient.  In bash you can do ::

  ls -a | grep -v '\.py' | wc -l > /var/log/counts

The Cuprum equivalent has more punctuation but is close (and the punctuation
has some benefits such as partial application of arguments) ::

  (ls['-a'] | grep['-v', '\\.py'] | wc['-l']  >  "/var/log/counts")()


Goals
-----
To replace Bash for medium to high complexity "scripts" and the simple "one
offs" that grow into complex messes.

  - Pythonic.
  - Focused. Just path/file operations and Bash "like" shell scripting.
  - Convenience and functionality. All the relevant goodness from glob, os, os.path, sys, shutil, tempfile.
  - As much support for scripting windows as is reasonably possible


Testing
-------
Additional unittests prerequisites:
 - pep8_
 - unittest2_ (only Python < 2.7)

The author uses nose_ to run unittests. ::

  pip install -U -r requirements.pip --use-mirrors
  pip install -U pep8 --use-mirrors
  nosetests


Installing
----------
Prequisites:
 - six_ Python 2/3 compatibility library.

::

  pip install -U -r requirements.pip
  python setup.py install


Build Status
------------
.. image:: https://secure.travis-ci.org/njharman/cuprum.png
   :align: left
   :scale: 200%

Tested against the following Python Versions using `Travis CI`_:

  - 2.5 requires unittest2_
  - 2.6 requires unittest2_
  - 2.7
  - 3.1
  - 3.2

.. _unix daddy: http://tomayko.com/writings/that-dilbert-cartoon
.. _plumbum: https://github.com/tomerfiliba/plumbum
.. _pbs: https://github.com/amoffat/pbs/
.. _path.py: http://pypi.python.org/pypi/path.py
.. _six: http://packages.python.org/six/
.. _pep8: http://pypi.python.org/pypi/pep8/
.. _unittest2: http://pypi.python.org/pypi/unittest2/
.. _nose: http://pypi.python.org/pypi/nose/
.. _travis ci: http://travis-ci.org/#!/njharman/cuprum
