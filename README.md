geni-lib is a Python library for interacting with the [NSF GENI Federation](http://www.geni.net),
or any resource pool that uses components of the [GENI Software Architecture](http://groups.geni.net/geni/raw-attachment/wiki/GeniArchitectTeam/GENI%20Software%20Architecture%20v1.0.pdf).

Common uses include orchestrating repeatable experiments and writing small tools for
inspecting the resources available in a given federation.  There are also a number
of administrative API handlers available for interacting with software commonly used
in experiments - particularly those exposing services to other experimenters.

Documentation can be found at [https://geni-lib.readthedocs.io](https://geni-lib.readthedocs.io).

This is a fork of the original `geni-lib` library that converts the python2 code to python3 and fixes some other incompatibilities.

## Installation
The modified package is available at `dist/geni_lib_xlab-1.0.0.tar.gz`. It can be installed with:

```bash
pip install <path-to-package>
```
