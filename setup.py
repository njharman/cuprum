#!/usr/bin/env python
import os

try:
    from distutils.core import setup
except ImportError:
    from setuptools import setup


setup(
    name='cuprum',
    version='0.1.0',
    author='Norman J. Harman Jr.',
    author_email='njharman@gmail.com',
    url='https://github.com/njharman/cuprum',
    description='''Awesome path/file operations and "subprocess for unix daddy's"''',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst'), 'r').read(),
    license='MIT',
    platforms=['POSIX', 'Windows'],
    classifiers=[
        'Topic :: System :: Systems Administration',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        ],
    install_requires=[
        'six',
        ],
    packages=['cu', ],
    provides=['cuprum', ],
    )
