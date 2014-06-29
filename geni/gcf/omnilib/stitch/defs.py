#----------------------------------------------------------------------
# Copyright (c) 2013-2014 Raytheon BBN Technologies
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and/or hardware specification (the "Work") to
# deal in the Work without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Work, and to permit persons to whom the Work
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Work.
#
# THE WORK IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE WORK OR THE USE OR OTHER DEALINGS
# IN THE WORK.
#----------------------------------------------------------------------

# XML tag constants
RSPEC_TAG = 'rspec'
LINK_TAG = 'link'
NODE_TAG = 'node'
STITCHING_TAG = 'stitching'
PATH_TAG = 'path'
EXPIRES_ATTRIBUTE = 'expires'
# Capabilities element names
CAPABILITIES_TAG = 'capabilities'
CAPABILITY_TAG = 'capability'
CONSUMER_VALUE = 'consumer'
PRODUCER_VALUE = 'producer'
VLANCONSUMER_VALUE = 'vlanconsumer'
VLANPRODUCER_VALUE = 'vlanproducer'

# see geni.util.rspec_schema for namespaces

# This should go away, its value is no longer used
LAST_UPDATE_TIME_TAG = "lastUpdateTime"

# Need the ExoSM URL, as ugly as that is
EXOSM_URL = "https://geni.renci.org:11443/orca/xmlrpc"

# schema paths for switching between v1 and v2
STITCH_V1_BASE = "hpn.east.isi.edu/rspec/ext/stitch/0.1"
STITCH_V2_BASE = "geni.net/resources/rspec/ext/stitch/2"
STITCH_V1_SCHEMA = "http://hpn.east.isi.edu/rspec/ext/stitch/0.1/ http://hpn.east.isi.edu/rspec/ext/stitch/0.1/stitch-schema.xsd"
STITCH_V1_NS = "http://hpn.east.isi.edu/rspec/ext/stitch/0.1"
STITCH_V2_SCHEMA = "http://www.geni.net/resources/rspec/ext/stitch/2/ http://www.geni.net/resources/rspec/ext/stitch/2/stitch-schema.xsd"
STITCH_V2_NS = "http://www.geni.net/resources/rspec/ext/stitch/2"
