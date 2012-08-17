#!/usr/bin/env python
import os
import cu

try:
    from distutils.core import setup
except ImportError:
    from setuptools import setup


setup(
    name='cuprum',
    version=cu.__version__,
    description='''Cuprum: Awesome path/file operations and "subprocess for unix daddy's"''',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst'), 'r').read(),
    author='Norman J. Harman Jr.',
    author_email='njharman@gmail.com',
    url='https://github.com/njharman/cuprum',
    license='MIT',
    packages=['cu', ],
    platforms=['POSIX', 'Windows'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Systems Administration',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        ],
    )
