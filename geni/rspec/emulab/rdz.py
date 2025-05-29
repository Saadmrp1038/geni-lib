# Copyright (c) 2016-2024 The University of Utah

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.



from ..pg import Request, Namespaces
import geni.namespaces as GNS
from lxml import etree as ET
# Import Emulab Ansible-specific extensions.
import geni.rspec.emulab.ansible
from geni.rspec.emulab.ansible import (Override)

class useRDZ(object):
    """Flag the rspec so that spectrum requests are turned into RDZ grants"""
    __ONCEONLY__ = True
    
    def __init__(self, instance=None, url=None, token=None):
        self._enabled = True
        self._url = url
        self._token = token
        self._instance = instance
        if (url and not token) or (token and not url):
            raise Exception("useRDZ: must provide both url and token of rdz")
        if instance and url:
            raise Exception("useRDZ: must provide instance OR url/token of rdz")
        pass
    
    def _write(self, root):
        if self._enabled:
            el = ET.SubElement(root, "{%s}rdz-request" % (Namespaces.EMULAB.name))
            if self._url:
                el.attrib["url"] = self._url
                el.attrib["token"] = self._token
                pass
            if self._instance:
                el.attrib["instance"] = self._instance
                pass
            pass
        return root

Request.EXTENSIONS.append(("useRDZ", useRDZ))

class enableHeartbeats(object):
    """Tell the RDZ to require heartbeats on grants."""
    __ONCEONLY__ = True
    
    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled:
            el = ET.SubElement(root, "{%s}rdz-options" % (Namespaces.EMULAB.name))
            el.attrib["heartbeats"] = "true"
            pass
        return root

class parentRDZ(object):
    """This is used to setup an RDZ-in-RDZ experiment and tells the inner
    RDZ how to contact the outer RDZ. This structure will be augmented with
    credential data during the instantiation process.
    """

    __ONCEONLY__ = True
    __WANTPARENT__ = True;

    def __init__(self, zmc_url=None, dst_url=None, identity_url=None):
        if not (zmc_url and dst_url and identity_url):
            raise Exception("Must provide zmc,dst,identity urls")
        self._enabled = True
        self.zmc_url = zmc_url
        self.dst_url = dst_url
        self.identity_url = identity_url
        self.request = None
    
    @property
    def _parent(self):
        return self.request

    @_parent.setter
    def _parent(self, request):
        self.request = request
        request.addOverride(
            Override("openzms_parent_zmc_url", value=self.zmc_url))
        request.addOverride(
            Override("openzms_parent_dst_url", value=self.dst_url))
        request.addOverride(
            Override("openzms_parent_identity_url", value=self.identity_url))
        pass

    #
    # This is going to tell the Powder instantiation path that special rdz-in-rdz
    # things need to be done. Most important, is the parent token.
    #
    def _write(self, root):
        if self._enabled:
            el = ET.SubElement(root, "{%s}rdz-in-rdz" % (Namespaces.EMULAB.name))
            pass
        return root

Request.EXTENSIONS.append(("parentRDZ", parentRDZ))
