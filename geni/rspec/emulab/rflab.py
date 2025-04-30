# Copyright (c) 2025 The University of Utah

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

from .. import pg
from ..pg import Link, Request

RFLAB_CM = "urn:publicid:IDN+emulab.net+authority+cm"

# Standalone USRP hardware types: those where the node incorporates
# BOTH the compute AND the radio hardware.
STANDALONE_USRP_TYPES = [ "nuc5300", "nuc8259", "nuc8559", "nuc8650" ]

# Hosted USRP hardware types: those where the node incorporates the
# radio hardware ONLY (so a link must be established to an independent
# compute host).
HOSTED_USRP_TYPES = [ "n310", "x310" ]

# Mapping of component IDs to node types.  While it's unfortunately
# fragile to encode this here, because the authoritative state is kept
# in the CM database, it's not possible for a profile script to query
# the state at the time the rspec is generated.  Luckily, even though the
# true state is dynamic, almost all updates either add new or rearrange
# existing nodes, so changes giving an old node a new type are very rare.
# It is preferable for profile scripts to refrain from including specific
# component IDs, but in some cases (in particular paired radio workbench
# nodes) it's unavoidable.
node_types = {
    "nuc1": "nuc5300",
    "nuc2": "nuc5300",
    "nuc3": "nuc5300",
    "nuc4": "nuc5300",
    "nuc5": "nuc5300",
    "nuc6": "nuc5300",
    "nuc7": "nuc5300",
    "nuc8": "nuc5300",
    "nuc9": "nuc5300",
    "nuc10": "nuc5300",
    "nuc12": "nuc5300",
    "nuc13": "nuc8559",
    "nuc14": "nuc5300",
    "nuc15": "nuc5300",
    "nuc16": "nuc5300",
    "nuc17": "nuc8559",
    "nuc22": "nuc8259",
    "nuc23": "nuc8650",
    "nuc27": "nuc8259",
    "ota-nuc1": "nuc8559",
    "ota-nuc2": "nuc8559",
    "ota-nuc3": "nuc8559",
    "ota-nuc4": "nuc8559",
    "n300-1": "n310",
    "n300-2": "n310",
    "n300-3": "n310",
    "n300-4": "n310",
    "c310-1": "x310",
    "oai-wb-a1": "x310",
    "oai-wb-a2": "x310",
    "oai-wb-b1": "x310",
    "oai-wb-b2": "x310",
    "oai-wb-c1": "x310",
    "oai-wb-c2": "x310"
}

# Representation of the topology of the paired radio workbench:
# (Required because the mapper doesn't maintain state or verify requests
# for RF links between PRW SDRs.)
#
# node1 and node2 are the component_id values for the linked nodes.
# They MUST be in the correct order (node1 < node2).
# multiplicity represents the number of available links.
prw_links = [
    { "node1": "oai-wb-a1", "node2": "oai-wb-a2", "multiplicity": 1 },
    { "node1": "oai-wb-b1", "node2": "oai-wb-b2", "multiplicity": 2 },
]

# Internal helper function for adding unique named interface to a node.
def mkiface( node, desc ):
    suffix = 0
    while True:
        name = node.client_id + ":" + desc + "-" + str( suffix )
        suffix += 1
                    
        for i in node.interfaces:
            if i.name == name:
                break
        else:
            break
    
    return node.addInterface( name )

class SDR( object ):
    # We don't inherit from the Node class, because in general an SDR
    # instance does not correspond to exactly one rspec element.

    """A class to represent the combination of SDR hardware combined with its controlling compute node.

    Args:
      client_id (str): The base name for any concrete nodes created to represent the hardware.  Depending on the `sdrtype`, this might or might not end up mapping to a single rspec node with the specified `client_id`.
      component_id (Optional[str]): The component ID of the desired SDR (i.e., the radio).  Depending on the `sdrtype`, this might or might not also correspond to the compute node component ID.
      sdrtype (Optional[str]): The type of SDR required.  Currently supported are "n310", "x310", "nuc5300", "nuc8259", "nuc8559", and "nuc8650".  Either `component_id` or `sdrtype` must be specified; it's generally preferable to supply only `sdrtype` if possible.
      environment (str): The specific POWDER RF lab hosting the SDR.  Currently supported are "attenuatormatrix" for the (previous PhantomNet) wired attenuator matrix, "otalab" for the indoor over-the-air lab, and "paired" for the wired paired radio workbench.
      disk_image (Optional[str]): Disk image requested on the compute node associated with the SDR.
      bandwidth (Optional[int]): Network bandwidth on the link between the compute and SDR hardware.  (Relevant only for Ethernet-linked USRPs.)
      computeaddr (Optional[int]): IP address assigned to the compute node interface on the link to the SDR hardware.  (Relevant only for Ethernet-linked USRPs.)
      radioaddr (Optional[int]): IP address assigned to the SDR node interface on the link to the compute node.  (Relevant only for Ethernet-linked USRPs.)
    """
    
    # We need to know the parent request, because we'll want to create
    # concrete nodes within the same context.
    __WANTPARENT__ = True
    
    def __init__( self, client_id, component_id=None, sdrtype=None,
                  environment=None, **params ):
        # Don't do anything if both component_id _and_ sdrtype are given;
        # while it might be nice to attempt a sanity check, we can't give
        # a warning on an apparent mismatch because there's no good channel
        # to report auxiliary output to the user, and raising a fatal error
        # would be too severe because the user might know something we don't.
        if component_id and component_id in node_types and not sdrtype:
            sdrtype = node_types[ component_id ]
            
        if sdrtype in STANDALONE_USRP_TYPES:
            # OK; we will later construct distinct compute/radio nodes
            pass
        elif sdrtype in HOSTED_USRP_TYPES:
            # OK; we will later construct one combined compute+radio node
            pass
        elif not sdrtype:
            raise Exception( "SDR: must specify sdrtype" )
        else:
            raise Exception( "SDR: unknown sdrtype " + sdrtype )

        self.sdrtype = sdrtype
        
        if environment == "attenuatormatrix":
            # OK; we will prepare to establish real links
            pass
        elif environment == "otalab":
            # OK; we will ignore links
            pass
        elif environment == "paired":
            # OK; we will later verify requested links
            pass
        elif not environment:
            raise Exception( "SDR: must specify environment" )
        else:
            raise Exception( "SDR: unknown environment " + environment )

        self.environment = environment

        self.client_id = client_id
        self.component_id = component_id
        self.params = params

        # That's all for now... wait until we hear about the parent
        # request to complete construction.

    @property
    def _parent( self ):
        return self.request

    @_parent.setter
    def _parent( self, request ):
        self.request = request
        
        if self.sdrtype in HOSTED_USRP_TYPES:
            self.compute = request.RawPC( self.client_id + "-c" )
            self.compute.setUseTypeDefaultImage()
            self.radio = request.RawPC( self.client_id + "-r",
                                        self.component_id )
            self.radio.hardware_type = self.sdrtype
            self.radio.setUseTypeDefaultImage()

            self.link = request.Link( self.client_id + "-ctrl" )

            # N3x0 and X3x0 USRPs use magic IP addresses on their
            # host interfaces:
            #
            # https://files.ettus.com/manual/page_usrp_x3x0.html
            #
            # For a 10 Gb link on the second SFP+ port,
            # it will boot with 192.168.40.2.
            ciface = mkiface( self.compute, "ctrl" )
            ciface.addAddress( pg.IPv4Address(
                self.params[ "computeaddr" ] if "computeaddr" in self.params \
                else "192.168.40.1",
                "255.255.255.0" ) )
            self.link.addInterface( ciface )
            riface = mkiface( self.radio, "ctrl" )
            riface.addAddress( pg.IPv4Address(
                self.params[ "radioaddr" ] if "radioaddr" in self.params \
                else "192.168.40.2",
                "255.255.255.0" ) )
            self.link.addInterface( riface )

            self.link.bandwidth = self.params[ "bandwidth" ] if \
                "bandwidth" in self.params else 10000000
            self.link.setNoBandwidthShaping()
            
            nodes = [ self.compute, self.radio ]
        elif self.sdrtype in STANDALONE_USRP_TYPES:
            self.compute = self.radio = request.RawPC( self.client_id,
                                                       self.component_id )
            self.radio.hardware_type = self.sdrtype
            self.radio.setUseTypeDefaultImage()

            nodes = [ self.radio ]

        if "disk_image" in self.params:
            self.compute.disk_image = self.params[ "disk_image" ]
            
        for n in nodes:
            if self.environment == "attenuatormatrix":
                n.component_manager_id = RFLAB_CM
                n.Desire( "rf-controlled", 1 )
            elif self.environment == "otalab":
                n.component_manager_id = RFLAB_CM
                # NB: we probably should be requesting rf-radiated
                # for OTA lab nodes.  But that will currently fail
                # to map, because nodes don't seem to have the
                # feature added in the database...
                # n.Desire( "rf-radiated", 1 )
            elif self.environment == "paired":
                n.component_manager_id = RFLAB_CM
                n.Desire( "rf-paired", 1 )
            
    def addInterface( **params ):
        return self.compute.addInterface( **params )
    
    def addService( **params ):
        return self.compute.addService( **params )
    
    def installDotFiles( **params ):
        return self.compute.installDotFiles( **params )
    
    def installRootKeys( **params ):
        return self.compute.installRootKeys( **params )
    
    def startVNC( **params ):
        return self.compute.startVNC( **params )
    
    def setFailureAction( **params ):
        self.compute.setFailureAction( **params )
        self.radio.setFailureAction( **params )
    
    def _write( self, root ):
        # A no-op: the concrete nodes do all the work.
        pass

Request.EXTENSIONS.append( ( "SDR", SDR ) )

class rflink( object ):
    # We don't inherit from the Link class, because some rflinks (e.g.,
    # logical links between OTA lab nodes) don't actually correspond
    # to concrete links at all, and so we don't want rspec link
    # elements.
    
    """A class to represent RF links between SDR instances.

    Args:
      node1 (SDR): One of the nodes to connect.
      node2 (SDR): The other node to connect.  Must belong to the same RF environment as node1.
      name (Optional[str]): An identifier to associate with the link.  If not provided, a unique name will be generated.
    """
    
    # We need to know the parent request, because we might want to create
    # concrete nodes within the same context.
    __WANTPARENT__ = True
    
    def __init__( self, node1, node2, name=None, **params ):
        if node1.environment != node2.environment:
            raise Exception( "rflink: nodes must belong to same environment" )

        if node1.environment == "attenuatormatrix":
            # we really will want a link object, but we need to know the
            # request context before we can construct it.
            pass
        elif node1.environment == "otalab":
            # this will be a no-op; OTA lab SDR interfaces are all inherently
            # linked to each other whether you specify that or not.
            pass
        elif node1.environment == "paired":
            # we won't actually include link elements in the rspec (the
            # mapper won't know what to do with them), but we will sanity
            # check the requested topology with what we know about the
            # paired radio workbench hardware.
            pass

        self.node1 = node1
        self.node2 = node2
        self.name = name
        self.params = params
        
        # That's all for now... wait until we hear about the parent
        # request to complete construction.
    
    @property
    def _parent( self ):
        return self.request

    @_parent.setter
    def _parent( self, request ):
        self.request = request

        if self.node1.environment == "attenuatormatrix":
            # The attenuator matrix nodes define one "interface" per
            # peer (which physically corresponds to a single RF port,
            # connected through a channel reaching multiple peers via
            # the internal dividers in the attenuator matrix).  Therefore,
            # each additional peer requires us to request a new
            # interface.
            if not self.name:
                suffix = 0
                while True:
                    self.name = self.node1.client_id + "-" + \
                        self.node2.client_id + "-" + str( suffix )
                    suffix += 1
                    
                    for r in request.resources:
                        if hasattr( r, "client_id" ) and \
                           r.client_id == self.name:
                            break
                    else:
                        break

            self.link = request.Link( self.name )
            self.link.bandwidth = 10000
            self.link.protocol = "P2PLTE"
            
            self.link.addInterface( mkiface( self.node1.radio,
                                             "to-" + self.node2.client_id ) )
            self.link.addInterface( mkiface( self.node2.radio,
                                             "to-" + self.node1.client_id ) )
        elif self.node1.environment == "ota":
            # don't need to do anything; OTA lab SDR interfaces are all
            # inherently linked to each other whether you specify that or not.
            pass
        elif self.node1.environment == "paired":
            if not self.node1.component_id or not self.node2.component_id:
                raise Exception( "rflink: paired node requires component_id" )

            if self.node1.component_id < self.node2.component_id:
                n1 = self.node1.component_id
                n2 = self.node2.component_id
            else:
                n1 = self.node2.component_id
                n2 = self.node1.component_id

            for pl in prw_links:
                if pl[ "node1" ] == n1 and pl[ "node2" ] == n2:
                    if not pl[ "multiplicity" ]:
                        raise Exception( "rflink: exhausted all RF links " +
                                         "between paired nodes " + n1 +
                                         " and " + n2 )

                    pl[ "multiplicity" ] -= 1

                    break
            else:
                raise Exception( "rflink: no RF links between paired nodes " +
                                 n1 + " and " + n2 )
        
    def _write( self, root ):
        # A no-op: the concrete nodes do all the work.
        pass

Request.EXTENSIONS.append( ( "rflink", rflink ) )
