from setuptools import setup

# Todo: Parse this from a proper readme file in the future
description = "histoprint"
long_description = """histoprint

Pretty print numpy histograms to the console.

"""

if __name__ == "__main__":
    # Read README
    with open("README.rst") as f:
        long_description = f.read()

setup(
    name="histoprint",
    version="1.0.1",
    description=description,
    long_description=long_description,
    url="https://github.com/ast0815/histoprint",
    author="Lukas Koch",
    author_email="lukas.koch@mailbox.org",
    license="MIT",
    py_modules=["histoprint"],
    install_requires=["numpy>=1.0.0", "six>=1.10.0",],
    extras_require={},
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
    zip_safe=True,
)
