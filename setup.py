#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages
from warnings import warn
from setuptools.command.install import install
from warnings import warn


test_requires = [
    "pytest",
    "pyfakefs",
    "pytest-cov",
    "black",
    "flake8",
    "anybadge",
]

setup(
    name="sparc-x-api",
    version="1.0.0",
    python_requires=">=3.8",
    description="Python API for the SPARC DFT Code",
    author="Tian Tian, Ben Comer",
    author_email="alchem0x2a@gmail.com, ben.comer@gatech.edu",
    url="https://github.com/SPARC-X/SPARC-X-API",
    packages=find_packages(),
    install_requires=["ase>=3.22.0"],
    entry_points={
        "ase.io": [
            "sparc = sparc.io",
        ],
        "console_scripts": ["sparc-ase=sparc.cli:main"],
    },
    extras_require={
        "test": test_requires,
    },
    package_data={"sparc": ["psp/*", "sparc_json_api/*.json"]},
    include_package_data=True,
)
