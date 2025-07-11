# Copyright (c) 2014-2018  Barnstormer Softworks, Ltd.

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup, find_packages

import os
import os.path
import platform

requires = ["cryptography",
            "ipaddress; python_version=='2.7'",
            "lxml",
            "requests",
            "wrapt"]

# If you are on linux, and don't have ca-certs, we can do an awful thing and it will still work
if os.name == "posix" and os.uname()[0] == "Linux":
  if not os.path.exists("/etc/ssl/certs/ca-certificates.crt"):
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context

pkgs = find_packages()
pkgs.append('')

setup(name = 'geni-lib-xlab',
      version = '1.0.0',
      author = 'Nick Bastin and the University of Utah',
      author_email = 'nick@bssoftworks.com',
      description = 'Library and tools for working with research testbed resources that support ' \
                    'the GENI AM API, including the NSF GENI Testbed (www.geni.net) and Cloudlab (cloudlab.us).',
      long_description = open("README.rst", "r").read(),
      packages = pkgs,
      package_dir = {'' : 'tools/ipython', 'geni' : 'geni', 'ccloud' : 'ccloud'},
      pymodules = ['genish'],
      scripts = ['tools/buildcontext/context-from-bundle',
                 'tools/buildcontext/build-context',
                 'tools/shell/genish'],

      url = 'https://gitlab.flux.utah.edu/emulab/geni-lib',
      install_requires = requires,
      classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        ]
      )
