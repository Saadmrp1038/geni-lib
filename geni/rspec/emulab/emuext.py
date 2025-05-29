# Copyright (c) 2016-2023 The University of Utah

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Common set of RSpec extensions supported by many Emulab-based aggregates
"""



from ..pg import Request, Namespaces, Link, Node, Service, Command, RawPC
from ..pg import NodeType, Execute, Install, DuplicateExtensionError
from ..igext import Password
import geni.namespaces as GNS
from lxml import etree as ET

class setCollocateFactor(object):
    """Added to a top-level Request object, this extension limits the number
    of VMs from one experiment that Emulab will collocate on each physical
    host.
    """
    __ONCEONLY__ = True
    
    def __init__(self, mfactor):
        """mfactor is an integer, giving the maximum number of VMs to multiplex
        on each physical host."""
        self.mfactor = mfactor
    
    def _write(self, root):
        el = ET.SubElement(root,
                           "{%s}collocate_factor" % (Namespaces.EMULAB.name))
        el.attrib["count"] = str(self.mfactor)
        return root

Request.EXTENSIONS.append(("setCollocateFactor", setCollocateFactor))

class setPackingStrategy(object):
    """Added to a top-level Request object, this extension controls the
    strategy used for distributing VMs across physical hosts
    """
    __ONCEONLY__ = True

    def __init__(self, strategy):
        self.strategy = strategy
    
    def _write(self, root):
        el = ET.SubElement(root,
                           "{%s}packing_strategy" % (Namespaces.EMULAB.name))
        el.attrib["strategy"] = str(self.strategy)
        return root

Request.EXTENSIONS.append(("setPackingStrategy", setPackingStrategy))
    
class setRoutingStyle(object):
    """Added to a top-level Request object, this extension controls the
    routing that is automatically configured on the experiment (data-plane)
    side of the network.
    """
    __ONCEONLY__ = True
    
    def __init__(self, style):
        self.style = style
    
    def _write(self, root):
        el = ET.SubElement(root,
                           "{%s}routing_style" % (Namespaces.EMULAB.name))
        el.attrib["style"] = str(self.style)
        return root

Request.EXTENSIONS.append(("setRoutingStyle", setRoutingStyle))

class setDelayImage(object):
    """Added to a top-level Request object, this extension sets the disk image
    that will be used for all delay nodes configured for the experiment.
    """
    __ONCEONLY__ = True
    
    def __init__(self, urn):
        """urn: URN of any image - to perform the intnded function, the 
        image must be capable of setting up bridging and/or traffic shaping.
        """
        self.urn = urn
    
    def _write(self, root):
        el = ET.SubElement(root,
                           "{%s}delay_image" % (Namespaces.EMULAB.name))
        el.attrib["urn"] = str(self.urn)
        return root

Request.EXTENSIONS.append(("setDelayImage", setDelayImage))

class setForceShaping(object):
    """Added to a Link or LAN object, this extension forces Emulab link
    shaping to be enabled, even if it is not strictly necessary. This
    allows the link properties to be changed dynamically via the Emulab event
    system.
    """
    __ONCEONLY__ = True
    
    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root, "{%s}force_shaping" % (Namespaces.EMULAB.name))
        el.attrib["enabled"] = "true"
        return root

Link.EXTENSIONS.append(("setForceShaping", setForceShaping))

class setNoBandwidthShaping(object):
    """Added to a Link or LAN object, this extension forces Emulab link
    shaping to be disabled for bandwidth, even if it is necessary. This
    is ignored if the link must be shaped for other reason (delay, loss).
    """
    __ONCEONLY__ = True
    
    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root,
                           "{%s}force_nobwshaping" % (Namespaces.EMULAB.name))
        el.attrib["enabled"] = "true"
        return root

Link.EXTENSIONS.append(("setNoBandwidthShaping", setNoBandwidthShaping))

class setNoInterSwitchLinks(object):
    """Added to a Link or LAN object, this extension forces the Emulab mapper
    to disallow mapping a link in the request topology to an inter-switch
    link.  This allows users to require that specific nodes in their
    topology be attached to the same switch(es).
    """
    __ONCEONLY__ = True
    
    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root, "{%s}interswitch" % (Namespaces.EMULAB.name))
        el.attrib["allow"] = "false"
        return root

Link.EXTENSIONS.append(("setNoInterSwitchLinks", setNoInterSwitchLinks))

class setJumboFrames(object):
    """Added to a Link or LAN object, this extension enables jumbo frames
    on the link (9000 byte MTU). Not all clusters support this option.
    """
    __ONCEONLY__ = True
    
    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root, "{%s}jumboframes" % (Namespaces.EMULAB.name))
        el.attrib["enabled"] = "true"
        return root

Link.EXTENSIONS.append(("setJumboFrames", setJumboFrames))

class createSharedVlan(object):
    """Added to a Link or LAN object, turns the new vlan into a shared
    vlan that can be shared between independent experiments. 
    """
    __ONCEONLY__ = True
    
    def __init__(self, name):
        self._enabled = True
        self._name = name
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root, "{%s}create_shared_vlan" % (GNS.SVLAN.name))
        el.attrib["name"] = self._name
        return root

Link.EXTENSIONS.append(("createSharedVlan", createSharedVlan))

class connectSharedVlan(object):
    """Added to a Link or LAN object, it connects the new vlan to a shared
    vlan created by another experiment.
    """
    __ONCEONLY__ = True
    
    def __init__(self, name):
        self._enabled = True
        self._name = name
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root, "{%s}link_shared_vlan" % (GNS.SVLAN.name))
        el.attrib["name"] = self._name
        return root

Link.EXTENSIONS.append(("connectSharedVlan", connectSharedVlan))

class enableSharedVlan(object):
    """Added to a Link or LAN object, it connects the new vlan to a shared
    vlan created by another experiment.
    """
    __ONCEONLY__ = True
    
    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root, "{%s}link_shared_vlan" % (GNS.SVLAN.name))
        el.attrib["placeholder"] = "true"
        return root

Link.EXTENSIONS.append(("enableSharedVlan", enableSharedVlan))

class setVlanTag(object):
    """Added to a Link or LAN object, request a specific vlan tag 
    """
    __ONCEONLY__ = True
    
    def __init__(self, tag):
        self._tag = tag
    
    def _write(self, root):
        root.attrib["vlantag"] = str(self._tag)
        return root

Link.EXTENSIONS.append(("setVlanTag", setVlanTag))

class setProperties(object):
    """Added to a Link or LAN object, this extension tells Emulab based
    clusters to set the symmetrical properties of the entire link/lan to
    the desired characteristics (bandwidth, latency, plr). This produces
    more efficient XML then setting a property on every source/destination
    pair, especially on a very large lan. Bandwidth is in Kbps, latency in
    milliseconds, plr a floating point number between 0 and 1. Use keyword
    based arguments, all arguments are optional:
    
        link.setProperties(bandwidth=100000, latency=10, plr=0.5)
    
    """
    __ONCEONLY__ = True
    
    def __init__(self, bandwidth=None, latency=None, plr=None):
        self._bandwidth = bandwidth
        self._latency   = latency
        self._plr       = plr
    
    def _write(self, root):
        if (self._bandwidth == None and self._latency == None and
            self._plr == None):
            return root
        el = ET.SubElement(root, "{%s}properties" % (Namespaces.EMULAB.name))
        if self._bandwidth != None:
            el.attrib["capacity"] = str(self._bandwidth)
        if self._latency != None:
            el.attrib["latency"] = str(self._latency)
        if self._plr != None:
            el.attrib["packet_loss"] = str(self._plr)
        return root

Link.EXTENSIONS.append(("setProperties", setProperties))

class setUseTypeDefaultImage(object):
    """Added to a node that does not specify a disk image, this extension
    forces Emulab to use the hardware type default image instead of the
    standard geni default image. Useful with special hardware that should
    run a special image.
    """
    __ONCEONLY__ = True
    
    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root, "{%s}use_type_default_image"
                           % (Namespaces.EMULAB.name))
        el.attrib["enabled"] = "true"
        return root

Node.EXTENSIONS.append(("setUseTypeDefaultImage", setUseTypeDefaultImage))

class setFailureAction(object):
    """Added to a node this extension will tell Emulab based aggregates to
    ignore errors booting this node when starting an experiment. This allows
    the experiment to proceed so that the user has time to debug."""
    __ONCEONLY__ = True
    
    def __init__(self, action):
        self.action = action
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == False:
            return root
        el = ET.SubElement(root, "{%s}failure_action" % (Namespaces.EMULAB.name))
        el.attrib["action"] = self.action
        return root

Node.EXTENSIONS.append(("setFailureAction", setFailureAction))

#
# Emulab Program Agents.
#
class ProgramAgent(Service):
    """Add an Emulab Program Agent, which can be controlled via the Emulab
    event system. Optional argument 'directory' specifies where to invoke
    the command from. Optional argument 'onexpstart' says to invoke the
    command when the experiment starts (time=0 in event speak). This is
    different than the Execute service, which runs every time the node boots.
    """
    def __init__ (self, name, command, directory = None, onexpstart = False):
        super(ProgramAgent, self).__init__()
        self.name = name
        self.command = command
        self.directory = directory
        self.onexpstart = onexpstart

    def _write (self, element):
        exc = ET.SubElement(element,
                            "{%s}program-agent" % (Namespaces.EMULAB.name))
        exc.attrib["name"] = self.name
        if isinstance(self.command, Command):
            exc.attrib["command"] = self.command.resolve()
        else:
            exc.attrib["command"] = self.command
        if self.directory:
            exc.attrib["directory"] = self.directory
        if self.onexpstart:
            exc.attrib["onexpstart"] = "true"
        return exc

class InstantiateOn(object):
    """Added to a node to specify that it a Xen VM should be bound to
    (instantiated on) another node in the topology.  Argument is the
    node instance or the client id of another node in the topology.
    """
    class InvalidParent(Exception):
        def __init__ (self, parent):
            super(InstantiateOn.InvalidParent, self).__init__()
            self.parent = parent
            def __str__ (self):
                return "%s is not a Raw PC" % (self.parent.name)
    
    __ONCEONLY__ = True
    
    def __init__(self, parent):
        if isinstance(parent, Node):
            # Xen VMs have to be bound to a raw PC.
            if not isinstance(parent, RawPC):
                raise InvalidParent(parent)
            self._parent = parent.name
        else:
            # Allow plain name to be used. At the moment the NS converter
            # is not trying to order nodes, so the vhost might not be
            # first. 
            self._parent = parent
            
    def _write(self, root):
        if self._parent == None:
            return root
        el = ET.SubElement(root, "{%s}relation" % (GNS.REQUEST.name))
        el.attrib["type"] = "instantiate_on"
        el.attrib["client_id"] = self._parent
        return root

Node.EXTENSIONS.append(("InstantiateOn", InstantiateOn))

class SubNodeOf(object):
    class InvalidParent(Exception):
        def __init__ (self, parent):
            super(InstantiateOn.InvalidParent, self).__init__()
            self.parent = parent
            def __str__ (self):
                return "%s is not a Raw PC" % (self.parent.name)
    
    __ONCEONLY__ = True
    
    def __init__(self, parent):
        if isinstance(parent, Node):
            # Must be bound to a raw PC.
            if not isinstance(parent, RawPC):
                raise InvalidParent(parent)
            self._parent = parent.name
        else:
            # Allow plain name to be used. At the moment the NS converter
            # is not trying to order nodes, so the vhost might not be
            # first. 
            self._parent = parent
            
    def _write(self, root):
        if self._parent == None:
            return root
        el = ET.SubElement(root, "{%s}relation" % (GNS.REQUEST.name))
        el.attrib["type"] = "subnode_of"
        el.attrib["client_id"] = self._parent
        return root

Node.EXTENSIONS.append(("SubNodeOf", SubNodeOf))

#
# A Bridged Link is syntatic sugar for two links separated by a bridge
# node acting as a delay node.
#
# Unfortunately, there is no way to get a handle on the parent object
# of an extension, so we need to get that explicitly.
#
class BridgedLink(object):
  """A bridged link is syntactic sugar used to create two links
separated by an Emulab delay (bridge) node. The BridgedLink class will
create the following topology:

	.      left-link          right-link
	node1 =========== bridge ============ node2

The bridge is a special node type (sliver_type="delay") that tells the
CM to insert an Emulab delay node instead of a plain (router) node. A
delay node is a transparent Ethernet bridge between the left and right
segments above, but on which the traffic can be shaped wrt. bandwidth,
latency, and loss. For example:

        # Create the bridged link between the two nodes.
        link = request.BridgedLink("link")
        # Add two interfaces
        link.addInterface(iface1)
        link.addInterface(iface2)
        # Give the link (bridge) some shaping parameters.
        link.bandwidth = 10000
        link.latency   = 15
        link.plr       = 0.01"""

  # This tells the Request class to set the _parent member after creating the
  # object
  __WANTPARENT__ = True;
  
  def __init__ (self, name = None):
    if name is None:
      self.name = Link.newLinkID()
    else:
      self.name = name

    self.bridge_name = name + "_bridge"
    self.left_name   = name + "_left"
    self.right_name  = name + "_right"
    self.left_iface  = None
    self.right_iface = None

    self._bandwidth  = Link.DEFAULT_BW
    self._latency    = Link.DEFAULT_LAT
    self._plr        = Link.DEFAULT_PLR

    # This needs to get set with the setter; this helps us remember that we
    # have not been attached to a parent
    self.request = None

    # These will be set later when we know the parent
    self.bridge = None
    self.left_link = None
    self.right_link = None

  @property
  def _parent(self):
    return self.request

  @_parent.setter
  def _parent(self, request):
    self.request     = request
    self.bridge      = request.Bridge(self.bridge_name)
    self.left_link   = request.Link(self.left_name)
    self.left_link.addInterface(self.bridge.iface0);
    self.right_link  = request.Link(self.right_name)
    self.right_link.addInterface(self.bridge.iface1);

  def addInterface(self, interface):
      if self.left_iface == None:
          self.left_link.addInterface(interface)
          self.left_iface = interface
      else:
          self.right_link.addInterface(interface)
          self.right_iface = interface

  @property
  def bandwidth (self):
    return self._bandwidth

  @bandwidth.setter
  def bandwidth (self, val):
    self.bridge.pipe0.bandwidth = val;
    self.bridge.pipe1.bandwidth = val;
    self._bandwidth = val

  @property
  def latency (self):
    return self._latency

  @latency.setter
  def latency (self, val):
    self.bridge.pipe0.latency = val;
    self.bridge.pipe1.latency = val;
    self._latency = val

  @property
  def plr (self):
    return self._plr

  @plr.setter
  def plr (self, val):
    self.bridge.pipe0.lossrate = val;
    self.bridge.pipe1.lossrate = val;
    self._plr = val

  def _write(self, root):
      return root

Request.EXTENSIONS.append(("BridgedLink", BridgedLink))

class ShapedLink(BridgedLink):
  """A ShapedLink is a synonym for BridgedLink"""

  def __init__ (self, name = None):
    super(ShapedLink, self).__init__(name=name)

Request.EXTENSIONS.append(("ShapedLink", ShapedLink))


class installRootKeys(object):
    """Added to a node this extension will tell Emulab based aggregates to
    to install private and/or public ssh keys for root so that root can ssh
    between nodes in your experiment without having to provide a password.
    By default both the private and public key are installed on each node.
    Use this extension to restrict where keys are installed in order to
    customize which nodes are trusted to initiate a root ssh to another node.
    For example:

            # Install a private/public key on node1
            node1.installRootKeys(True, True)
            # Install just the public key on node2
            node2.installRootKeys(False, True)
    """
    
    def __init__(self, private = True, public = True):
        self._include = True
        self._private = private
        self._public  = public
    
    def _write(self, root):
        if self._include == False:
            return root
        el = ET.SubElement(root, "{%s}rootkey" % (Namespaces.EMULAB.name))
        if self._private:
            el.attrib["private"] = "true";
        else:
            el.attrib["private"] = "false";
        if self._public:
            el.attrib["public"] = "true";
        else:
            el.attrib["public"] = "false";
        return root

Node.EXTENSIONS.append(("installRootKeys", installRootKeys))

class disableRootKeys(object):
    """Added to a request this extension will tell Emulab based aggregates to
    to not install private and/or public ssh keys for root.
    """
    __ONCEONLY__ = True

    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == True:
            el = ET.SubElement(root,
                               "{%s}disablerootkey" % (Namespaces.EMULAB.name))
        return root

Request.EXTENSIONS.append(("disableRootKeys", disableRootKeys))

class skipVlans(object):
    """Added to a request this extension will tell Emulab based aggregates to
    to not setup or tear down vlans. You should not use this!
    """
    __ONCEONLY__ = True

    def __init__(self):
        self._enabled = True
    
    def _write(self, root):
        if self._enabled == True:
            el = ET.SubElement(root, "{%s}skipvlans" % (Namespaces.EMULAB.name))
        return root

Request.EXTENSIONS.append(("skipVlans", skipVlans))

class Attribute(object):
    """Added to a node, this Emulab extension becomes a node_attribute.
    """
    def __init__ (self, key, value):
        self.key = key
        self.value = value

    def _write (self, node):
        at = ET.SubElement(node,
                           "{%s}node_attribute" % (Namespaces.EMULAB.name))
        at.attrib["key"] = self.key
        at.attrib["value"] = self.value
        return node

Node.EXTENSIONS.append(("Attribute", Attribute))

class wirelessSite(object):
    """A simple extension to mark a node as being part of a given wireless aggregate.
    """
    def __init__(self, id, type, urn):
        self.id = id
        self.type = type
        self.urn = urn

    def _write(self, node):
        el = ET.SubElement(
            node,"{%s}wireless-site" % (Namespaces.EMULAB.name))
        el.attrib['id'] = self.id
        el.attrib['type'] = self.type
        el.attrib['urn'] = self.urn
        return node

Node.EXTENSIONS.append(("wirelessSite", wirelessSite))

class ExperimentFirewall(Node):
    """Added to a request this extension will tell Emulab to add a firewall
    to the control network. You may supply optional rules in iptables syntax.
    """
    __ONCEONLY__ = True

    class Style(object):
        OPEN     = "open"
        CLOSED   = "closed"
        BASIC    = "basic"
    
    def __init__ (self, name, style):
        super(ExperimentFirewall, self).__init__(name, "firewall")
        self.style = style
        self.rules = []

    def addRule(self, rule):
        self.rules.append(rule)

    def _write (self, root):
        nd = super(ExperimentFirewall, self)._write(root)
        st = nd.find("{%s}sliver_type" % (GNS.REQUEST.name))
        fw = ET.SubElement(st, "{%s}firewall_config" % (Namespaces.EMULAB.name))
        fw.attrib["style"] = self.style
        for rule in self.rules:
            el = ET.SubElement(fw, "{%s}rule" % (Namespaces.EMULAB.name))
            el.text = rule
        return nd

Request.EXTENSIONS.append(("ExperimentFirewall", ExperimentFirewall))

class L1Link(Link):
  def __init__ (self, name = None):
    super(L1Link, self).__init__(name, "layer1")

Request.EXTENSIONS.append(("L1Link", L1Link))

class Switch(Node):
  def __init__ (self, name, component_id = None):
    super(Switch, self).__init__(name, NodeType.RAW,
                                 component_id = component_id, exclusive = True)
    self.setUseTypeDefaultImage()

Request.EXTENSIONS.append(("Switch", Switch))

class initVNC(object):
    """Added to a top-level Request object, this extension adds required
    initialization to run VNC consoles on your nodes.
    """
    __ONCEONLY__ = True
    __WANTPARENT__ = True;
    
    def __init__(self):
        self.password = Password("vncpasswd")
    
    @property
    def _parent(self):
        return self.request

    @_parent.setter
    def _parent(self, request):
        self.request = request
        request.addResource(self.password)        

    # Add an emulab extension for the WEB UI.
    def _write(self, root):
        return root

Request.EXTENSIONS.append(("initVNC", initVNC))

class startVNC(object):
    """Added to a node this extension will tell Emulab based aggregates to
    install and start a VNC server."""
    __ONCEONLY__ = True
    __WANTPARENT__ = True;

    STARTVNC = "(cd /var/tmp && \
        (test -e /var/tmp/novnc-setup || \
         git clone https://gitlab.flux.utah.edu/emulab/novnc-setup.git) && \
        /bin/bash /var/tmp/novnc-setup/startvnc.sh)"

    def __init__(self, nostart=False):
        self.nostart = nostart
    
    @property
    def _parent(self):
        return self.node

    @_parent.setter
    def _parent(self, node):
        self.node = node
        if self.nostart == False:
            node.addService(Execute(shell="sh", command=self.STARTVNC))
            pass
        #
        # Add the top level init. Watch for a duplicate error, ignore
        # since we try to add it for every node, rather then figure
        # out if its already done. 
        try:
            node._parent.initVNC()
        except DuplicateExtensionError:
            pass
        pass
        
    # Add an emulab extension for the WEB UI.
    # Eventually allow port number.
    def _write(self, node):
        at = ET.SubElement(node, "{%s}x11vnc" % (Namespaces.EMULAB.name))
        return node

Node.EXTENSIONS.append(("startVNC", startVNC))

class mountCephFS(object):
    """Added to a node this extension will tell Emulab based aggregates to
    install Ceph client-side packages, customize for the project, and
    mount a subdirectory of theC eph filesystem."""
    __ONCEONLY__ = True
    __WANTPARENT__ = True;

    STARTCEPH = "(cd /var/tmp && \
        (test -e /var/tmp/powder-ceph-client || \
         git clone https://gitlab.flux.utah.edu/hibler/powder-ceph-client.git) && \
        sudo bash /var/tmp/powder-ceph-client/scripts/startup.sh)"

    def __init__(self, nostart=False):
        self.nostart = nostart
    
    @property
    def _parent(self):
        return self.node

    @_parent.setter
    def _parent(self, node):
        self.node = node
        # Join this node with the Ceph shared lan
        lan = node._parent.LAN()
        lan.addInterface(node.addInterface())
        lan.best_effort = True
        lan.link_multiplexing = True
        lan.setJumboFrames()
        lan.connectSharedVlan("powder-ceph");
        # Schedule the startup script
        if self.nostart == False:
            # N.B. we add our service at the beginning
            node.addService(Execute(shell="sh", command=self.STARTCEPH), True)
            pass
        pass
        
    def _write(self, root):
        return root

Node.EXTENSIONS.append(("mountCephFS", mountCephFS))

class installDotFiles(object):
    """Added to a node this extension will tell Emulab based aggregates to
    download and unpack a tarfile of your .dot files in your home directory.
    Your .dot files (and directories if you like) should be at the top
    level of the tarfile so they can be unpacked directly into your home
    directory. The tarfile should be on a public web server.

    DO NOT PUT SSH/SSL PRIVATE KEYS IN THE TARFILE!

    More generally, you should not put a .ssh directory in the tarfile
    since that can interfere with account setup and make it impossible
    for you to log in at all.
    """
    __ONCEONLY__ = True
    __WANTPARENT__ = True;

    INSTALL = "(cd /var/tmp && \
        (test -e /var/tmp/install-dotfiles.sh || \
         wget -O install-dotfiles.sh https://www.emulab.net/downloads/install-dotfiles.sh) && \
        /bin/sh /var/tmp/install-dotfiles.sh)"

    def __init__(self, tarfile):
        self.tarfile = tarfile
    
    @property
    def _parent(self):
        return self.node

    @_parent.setter
    def _parent(self, node):
        self.node = node
        node.addService(Install(path="/var/tmp/dots", url=self.tarfile))
        node.addService(Execute(shell="sh", command=self.INSTALL))
        pass
        
    def _write(self, node):
        return node

Node.EXTENSIONS.append(("installDotFiles", installDotFiles))

