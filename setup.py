#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="en16931-validator-dach",
    version="1.0.0",
    description="Präziser EN 16931 E-Rechnung Validator für XRechnung 3.0 (UBL) & ZUGFeRD 2.2 / Factur-X (CII)",
    author="DACH Digitalwerk",
    author_email="dach.digitalwerk@gmail.com",
    url="https://github.com/DACHDigitalwerk/e-rechnung-validator-en16931-dach",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "en16931-val=en16931_validator.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Office/Business :: Financial :: Accounting",
    ],
)
