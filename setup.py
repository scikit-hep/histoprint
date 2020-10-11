from setuptools import setup

# make open consistent between py2 and py3 as we need encoding param
from io import open

# Todo: Parse this from a proper readme file in the future
description = "histoprint"
long_description = """histoprint

Pretty print numpy histograms to the console.

"""

if __name__ == "__main__":
    # Read README
    with open("README.rst", mode="r", encoding="utf-8") as f:
        long_description = f.read()

extras = {"test": ["pytest"]}

setup(
    name="histoprint",
    version="1.5.1",
    description=description,
    long_description=long_description,
    url="https://github.com/scikit-hep/histoprint",
    author="Lukas Koch",
    author_email="lukas.koch@mailbox.org",
    license="MIT",
    packages=["histoprint"],
    install_requires=["numpy>=1.0.0", "click>=7.0.0"],
    extras_require=extras,
    tests_require=extras["test"],
    python_requires=">=2.7",
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 5 - Production/Stable",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: MIT License",
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
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
