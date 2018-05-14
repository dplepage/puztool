#!/usr/bin/env python

from distutils.core import setup

setup(name='Puztool',
      version='1.0',
      description='Puzzle Tools',
      author='Dan Lepage',
      author_email='dplepage@gmail.com',
      packages=['puztool'],
      install_requires=[
        'numpy',
        'beautifulsoup4',
        'funcy',
        'flask',
        ]
     )
