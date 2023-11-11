# Copyright (c) 2016-2023 The University of Utah

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

from ..pg import Request, Namespaces, Link, Request, Node, Interface
import geni.namespaces as GNS
from lxml import etree as ET

class requestSpectrum(object):
    def __init__(self, freq_low, freq_high, power, bandwidth=None):
        self._freq_low  = freq_low
        self._freq_high = freq_high
        self._power     = power
        self._width     = bandwidth
    
    def _write(self, root):
        el = ET.SubElement(root, "{%s}spectrum" % (Namespaces.EMULAB.name))
        el.attrib["frequency_low"]  = str(self._freq_low)
        el.attrib["frequency_high"] = str(self._freq_high)
        el.attrib["power"]          = str(self._power)
        if self._width != None and self._width != 0:
            el.attrib["bandwidth"]  = str(self._width)
            pass
        return root

Node.EXTENSIONS.append(("requestSpectrum", requestSpectrum))
Interface.EXTENSIONS.append(("requestSpectrum", requestSpectrum))
Request.EXTENSIONS.append(("requestSpectrum", requestSpectrum))

class selectFrontend(object):
    def __init__(self, frontend):
        self._frontend  = frontend

    def _write(self, root):
        el = ET.SubElement(root, "{%s}frontend" % (Namespaces.EMULAB.name))
        el.attrib["name"] = self._frontend
        return root

Interface.EXTENSIONS.append(("selectFrontend", selectFrontend))
    
