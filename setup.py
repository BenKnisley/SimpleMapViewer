#!/usr/bin/env python3
"""
Author: Ben Knisley [benknisley@gmail.com]
Date: 17 March, 2020
"""
from setuptools import setup

setup(
    name = "MapViewer",
    version = "0.0.1",
    author = "Ben Knisley",
    author_email = "benknisley@gmail.com",
    description = ("A module for rendering maps."),
    url = "https://github.com/BenKnisley/MapEngine",
    license = "MIT",
    keywords = "GIS map MapEngine",
    install_requires=['numpy','pyproj'],
    packages=["MapViewer",],
    long_description="...",
    entry_points = {
        'console_scripts': [
            'MapViewer = MapViewer:main',                  
        ],              
    },
    classifiers=[
        "Development Status :: 1 - Planning",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
    ],
)

