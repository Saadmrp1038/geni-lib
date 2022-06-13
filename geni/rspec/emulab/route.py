# Copyright (c) 2016-2022 The University of Utah

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

from ..pg import Request, Namespaces, Execute
from ..pg import NodeType
from .emuext import startVNC
from .spectrum import requestSpectrum as RSP
import geni.namespaces as GNS
from lxml import etree as ET

class requestBusRoute(object):
    def __init__(self, name):
        self._name = name
        self.disk_image = None
        self.services = []
        self.spectrum = []
        self.startvnc = False;
    
    def _write(self, root):
        el = ET.SubElement(root, "{%s}busroute" % (Namespaces.EMULAB.name))
        el.attrib["name"] = self._name
        
        if self.disk_image:
            if isinstance(self.disk_image, (str, unicode)):
                di = ET.SubElement(el, "{%s}disk_image" % (GNS.REQUEST.name))
                di.attrib["name"] = self.disk_image
            elif isinstance(self.disk_image, geni.urn.Base):
                di = ET.SubElement(el, "{%s}disk_image" % (GNS.REQUEST.name))
                di.attrib["name"] = str(self.disk_image)
            else:
                self.disk_image._write(el)
                pass
            pass

        if self.services:
            svc = ET.SubElement(el, "{%s}services" % (GNS.REQUEST.name))
            for service in self.services:
                service._write(svc)
                pass
            pass

        if self.startvnc:
            startVNC()._write(el)
            pass

        if self.spectrum:
            for s in self.spectrum:
                s._write(el)
                pass
            pass

        return root
    
    def addService (self, svc):
        self.services.append(svc)
        pass

    def startVNC(self, nostart=False):
        self.startvnc = True
        if nostart == False:
            command = startVNC().STARTVNC
            self.services.insert(0, Execute(shell="sh", command=command))
            pass
        pass

    def requestSpectrum(self, low, high, power):
        self.spectrum.append(RSP(low, high, power))

    pass

Request.EXTENSIONS.append(("requestBusRoute", requestBusRoute))

class requestAllRoutes(requestBusRoute):
    def __init__(self):
        super(requestAllRoutes, self).__init__("allroutes")

    pass

Request.EXTENSIONS.append(("requestAllRoutes", requestAllRoutes))

