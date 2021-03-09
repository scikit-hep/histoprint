from setuptools import setup
import setuptools_scm  # noqa: F401
import toml  # noqa: F401

# make open consistent between py2 and py3 as we need encoding param
from io import open

# Todo: Parse this from a proper readme file in the future
description = "histoprint"
long_description = """histoprint

Pretty print numpy histograms to the console.

"""


# Read README
with open("README.rst", mode="r", encoding="utf-8") as f:
    long_description = f.read()

extras = {"test": ["pytest"], "root": ["uproot>=4", "awkward>=1"]}

setup(
    name="histoprint",
    description=description,
    long_description=long_description,
    url="https://github.com/scikit-hep/histoprint",
    author="Lukas Koch",
    author_email="lukas.koch@mailbox.org",
    license="MIT",
    packages=["histoprint"],
    install_requires=["numpy>=1.0.0", "click>=7.0.0"],
    extras_require=extras,
    python_requires=">=2.7",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],
    entry_points="""
        [console_scripts]
        histoprint=histoprint.cli:histoprint
    """,
    zip_safe=True,
)
