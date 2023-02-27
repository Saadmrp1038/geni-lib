# Copyright (c) 2014-2019 The University of Utah and Barnstormer Softworks, Ltd.

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Library for dealing with scripts that are run in the context of a portal."""

from __future__ import absolute_import

import sys
import os
import atexit
import warnings
import json
import argparse
from argparse import Namespace
import logging
import os.path

import six

from .rspec import igext
from .rspec import pgmanifest
from .rspec.pg import Request

# Default to something sane for our package
LOG = logging.getLogger('geni.portal')

dodebug = False
debugLogHandler = None
if 'GENILIB_PORTAL_DEBUG' in os.environ:
    dodebug = True
    debugLogHandler = logging.StreamHandler(stream=sys.stderr)
    debugLogHandler.setFormatter(logging.Formatter(
        fmt="%(levelname)s:%(name)s:%(lineno)s:%(funcName)s: %(message)s "))
    LOG.addHandler(debugLogHandler)
    LOG.setLevel(logging.DEBUG)
else:
    LOG.addHandler(logging.NullHandler())

class DictNamespace(dict,Namespace):
  """
  A simple class that is similar to argparse.Namespace, but is also an
  iterable dictionary, and allows key/value deletion.
  """
  def __setattr__(self,attr,value):
    self.__setitem__(attr,value)

  def __getattr__(self,attr):
    if attr in self.keys():
      return self.__getitem__(attr)
    else:
      return dict.__getattribute__(self,attr)

  def __delattr__(self,attr):
    if attr in self.keys():
      return self.__delitem__(attr)
    else:
      return dict.__delattribute__(self,attr)

def parseBool(b):
  """
  Extract a bool from `b` as a string (any type), or by using `bool()`.
  """
  if isinstance(b,six.string_types):
    if b == "False" or b == "false":
      return False
    elif b == "True" or b == "true":
      return True
  return bool(b)

class ParameterType (object):
  """Parameter types understood by Context.defineParameter()."""

  INTEGER     = "integer"       #: Simple integer
  STRING      = "string"        #: Any string
  BOOLEAN     = "boolean"       #: True/False
  IMAGE       = "image"         #: URN specifying a particular image
  AGGREGATE   = "aggregate"     #: URN specifying an Aggregate Manger
  NODETYPE    = "nodetype"      #: String specifying a type of node
  BANDWIDTH   = "bandwidth"     #: Floating-point number to be used for bandwidth
  LATENCY     = "latency"       #: Floating-point number to be used for latency
  SIZE        = "size"          #: Integer for size (eg. MB, GB, etc.)
  PUBKEY      = "pubkey"        #: An RSA public key.
  LOSSRATE    = "lossrate"      #: Floating-point number 0.0 <= N < 1.0
  # Dynamically created drop down menus of Powder specific resources
  FIXEDENDPOINT = "fixedendpoint" #: Fixed Endpoints
  BASESTATION   = "basestation"   #: Base Stations
  
  argparsemap = { INTEGER: int, STRING: str, BOOLEAN: parseBool, IMAGE: str,
                  AGGREGATE: str, NODETYPE: str, BANDWIDTH: float,
                  LATENCY: float, SIZE: int, PUBKEY: str, LOSSRATE: float,
                  FIXEDENDPOINT: str, BASESTATION: str}

  # Other parameter types known to the system, but not exposed via the
  # defineParameter API.
  STRUCT      = "struct"        #: A StructParameter with member parameters; may be a JSON string that encodes a dict, or a raw dict.

class Parameter(object):
  """
  A class containing the definition of a basic parameter where type is
  specified as a ParameterType field (e.g., not multi-valued, not a
  struct type).  Do not instantiate this class directly; use the method
  wrappers in the Context class to declare parameters when possible.

  Parameters must have a defaultValue.  They may have a list of
  legalValues.  All values in the latter must be type-correct, and the
  former must be both type-correct and a member of _legalValues.  A
  legalValues list may be a flat list of type-correct values, or a list
  of 2-tuples, where the first element of each tuple is a type-correct
  value, and the second element is a display name for frontends.
  """

  def __init__(self,name,description,type,defaultValue,legalValues=None,
               longDescription=None,inputFieldHint="",groupId=None,hide=False,
               prefix="emulab.net.parameter.",inputConstraints=None,
               _skipInitialChecks=False):
    self.name = name
    self.description = description
    self.longDescription = longDescription
    self.inputFieldHint = inputFieldHint
    self.inputConstraints = inputConstraints
    self.type = type
    self.groupId = groupId
    self.hide = hide
    self.prefix = prefix
    self._value = None
    self._legalValues = legalValues or None
    self._defaultValue = defaultValue
    if not _skipInitialChecks:
      if self.legalValues:
        for x in self.legalValues:
          self._parseValue(x)
      self.setDefaultValue(defaultValue)
    LOG.debug(str(self))

  def __repr__(self):
    return "%s(%s=%s,default=%s)" % (
        self.__class__.__name__,self.name,self.value,self.defaultValue)

  # NB: this is here for naughty profiles that used to reach into
  # pc._parameters[paramName][field]; this is not intended to be a
  # general dict-like interface.
  def __getitem__(self,item):
    return self.__getattribute__(item)

  @property
  def defaultValue(self):
    """
    Return the default value of this parameter.
    """
    return self._defaultValue

  @property
  def legalValues(self):
    """
    Returns None if there are no legal value restrictions.  Otherwise,
    returns a list of legal values.  (NB: self._legalValues itself may
    be either a list of strings, or a list of 2-tuples, where the
    actual value is the first element of the tuple, and the display hint
    is the second element.)
    """
    if not self._legalValues:
      return None
    return [x if not isinstance(x, tuple) else x[0] for x in self._legalValues]

  @property
  def value(self):
    """
    Returns this parameter's bound value, after values have been bound
    to this parameter's portal Context object.
    """
    return self._value

  def _parseValue(self,value):
    """
    Extracts/converts a parameter value of the correct type, if
    possible, from the supplied `value`.  To support the variety of
    input formats of parameters, we support conversion from strings to
    the proper ParameterType; see ParameterType.argparsemap; see also
    other Parameter subclasses (StructParameter) and mixins (Multi),
    since those accept JSON strings.
    """
    LOG.debug("%s(%s)" % (str(self.name),str(value)))
    if value == None:
      raise IllegalParameterValueError(value,self)
    nvalue = ParameterType.argparsemap[self.type](value)
    LOG.debug("%s(%s) -> %s"
              % (str(self.name),str(value),str(nvalue)))
    return nvalue

  def _checkValue(self,value):
    """
    Checks that a type-correct value (e.g. extracted by _parseValue) is
    also a member of _legalValues.
    """
    LOG.debug("%s(%s)" % (self.name,str(value)))
    if self.legalValues and value not in self.legalValues:
      raise IllegalParameterValueError(value,self)
    if value == None:
      raise IllegalParameterValueError(value,self)

  def setValue(self,value):
    """
    Invoked by `Context` to bind a value to this parameter.  This both
    parses the value and checks it for legality.
    """
    v = self._parseValue(value)
    self._checkValue(v)
    self._value = v
    return v

  def setDefaultValue(self,defaultValue):
    """
    Sets this parameter's default value, after invoking its _parseValue
    (type correctness) and _checkValue (constraint legality) methods.
    """
    LOG.debug("%s(%s)" % (self.name,str(defaultValue)))
    # NB: the defaultValue may be a tuple present in self._legalValues; it
    # need not be the first value of a tuple.
    if type(defaultValue) == tuple and defaultValue in self._legalValues:
      defaultValue = defaultValue[0]
    v = self._parseValue(defaultValue)
    self._checkValue(v)
    self._defaultValue = v

  def toParamdef(self):
    """
    Converts this Parameter's metadata to a JSON dict used by the portal
    frontend.
    """
    fields = [ "name","description","longDescription","inputFieldHint","type",
               "_legalValues","_defaultValue","groupId","hide",
               "inputConstraints" ]
    d = dict()
    for f in fields:
      fname = f
      if fname.startswith('_'):
        fname = fname[1:]
      d[fname] = getattr(self,f)
    return d

  def validate(self):
    """
    A wrapper that checks both the defaultValue and legalValues for
    type- and constraint-correctness.
    """
    LOG.debug(self.name)
    self._parseValue(self.defaultValue)
    self._checkValue(self.defaultValue)
    if self.legalValues:
      for v in self.legalValues:
        self._parseValue(v)

class Multi(object):
  """
  When this class is added to a subclass of Parameter as the *first*
  multiply-inherited class, the subclass will accept lists as its
  values.  The second multiply-inherited class specifies the member
  parameter type.  We call this a multi-value parameter.  Multi-value
  parameters have additional constraints (min/max member count).

  Note that a defaultValue for a multi-value parameter is a list.  Thus,
  multi-value parameters have a new field, the `itemDefaultValue` key,
  which is the default value of a new list member when unspecified.
  This allows the user to simply specify min/max/itemDefaultValue *in
  lieu* of the defaultValue, and an appropriate defaultValue of length
  min will be created by cloning the itemDefaultValue min times.

  Given the "wrapping" nature of this class, it overrides every method
  in the Parameter class except for validate, because it effectively
  overrides all value parsing/checking and calls the second-level
  multiply-inherited class's parse/check methods for member values.
  """

  def __init__(self,min=None,max=None,itemDefaultValue=None,
               multiValueTitle=None):
    self.multiValue = True
    self.min = min
    self.max = max
    self.multiValueTitle = multiValueTitle
    self._itemDefaultValue = itemDefaultValue
    self.setItemDefaultValue(itemDefaultValue)
    # Fill in self.defaultValue from itemDefaultValue iff
    # len(self.defaultValue) == 0, and if there's an item default value.
    if self.defaultValue is not None \
      and not isinstance(self.defaultValue,list):
      raise PortalError("invalid multivalue parameter '%s' defaultValue (%s):"
                        " not a list" % (str(self.defaultValue),self.name))
    if self.min is not None and self.min > 0 \
      and (self.defaultValue is None or self.defaultValue == []): # or len(self.defaultValue) < self.min):
      if self.itemDefaultValue is None:
        raise PortalError(
          "invalid multivalue parameter '%s' with min=%d:"
          " 0-length defaultValue (%s) and no itemdefaultValue specified!"
          % (self.name,self.min,str(self.defaultValue)))
      else:
        self._defaultValue = [ self.itemDefaultValue for x in range(0,self.min) ]

  @property
  def itemDefaultValue(self):
    """
    Returns the new item default value.  If a frontend can dynamically
    add member values to this Multi value parameter, this should be the
    value it autofills for the new member.
    """
    return self._itemDefaultValue

  def setItemDefaultValue(self,value):
    LOG.debug("%s(%s)" % (self.name,str(value)))
    v = super(Multi,self)._parseValue(value)
    super(Multi,self)._checkValue(v)
    self._itemDefaultValue = v
    LOG.debug("%s(%s) -> %s"
              % (self.name,str(value),str(self._itemDefaultValue)))

  def _checkValue(self,value):
    if value is None and (self.min == None or self.min == 0):
      return
    if not isinstance(value,list):
      raise IllegalParameterValueError(value,param=self)
    for x in value:
      LOG.debug("%s(%s)" % (str(super(Multi,self)._checkValue),str(x)))
      super(Multi,self)._checkValue(x)

  def _parseValue(self,value):
    LOG.debug("%s(%s)" % (str(self.name),str(value)))
    if value == None:
      value = []
    elif isinstance(value,six.string_types):
      if value == "":
        value = []
      else:
        try:
          value = json.loads(value)
        except:
          raise PortalError(
            "invalid multivalue parameter JSON string (%s=%s)"
            % (self.name,str(value)))
    if not isinstance(value,list):
      raise PortalError("invalid multivalue parameter JSON value ('%s'): not list" % (str(value),))
    for x in value:
      LOG.debug("x = %s" % (str(x)))
    nvalue = [ super(Multi,self)._parseValue(x) for x in value ]
    LOG.debug("%s(%s) -> %s" % (str(self.name),str(value),str(nvalue)))
    return nvalue

  def setValue(self,value):
    LOG.debug("%s(%s)" % (str(self.name),str(value)))
    self._checkValue(value)
    self._value = value
    return self.value

  def setDefaultValue(self,value):
    LOG.debug("%s(%s)" % (self.name,str(value)))
    if self.min is not None and self.min > 0 \
      and (value is None or len(value) < self.min):
      raise PortalError(
        "invalid multivalue parameter '%s' with min=%d:"
        " insufficient default value (%s) specified!"
        % (self.name,self.min,str(value)))
    if value == None:
      self._defaultValue = []
      return
    newValue = []
    for v in value:
      LOG.debug("%s(%s)" % (self.name,str(v)))
      v = super(Multi,self)._parseValue(v)
      super(Multi,self)._checkValue(v)
      newValue.append(v)
    self._defaultValue = newValue
    LOG.debug("%s -> %s" % (self.name,str(newValue)))

  def validate(self):
    LOG.debug(self.name)
    self.setItemDefaultValue(self.itemDefaultValue)
    self.setDefaultValue(self.defaultValue)
    #self._parseValue(self.defaultValue)
    #self._checkValue(self.defaultValue)
    if self.legalValues:
      for v in self.legalValues:
        super(Multi,self)._parseValue(v)

  def toParamdef(self):
    d = super(Multi,self).toParamdef()
    fields = [ "multiValue","min","max","itemDefaultValue","multiValueTitle" ]
    for f in fields:
      d[f] = getattr(self,f)
    return d

class MultiParameter(Multi,Parameter):
  def __init__(self,name,description,type,defaultValue,legalValues=None,
               longDescription=None,groupId=None,hide=False,
               prefix="emulab.net.parameter.",inputFieldHint=None,
               inputConstraints=None,
               min=None,max=None,itemDefaultValue=None,multiValueTitle=None):
    Parameter.__init__(
      self,name,description,type,defaultValue,legalValues=legalValues,
      longDescription=longDescription,groupId=groupId,hide=hide,
      prefix=prefix,inputFieldHint=inputFieldHint,
      inputConstraints=inputConstraints,_skipInitialChecks=True)
    Multi.__init__(
      self,min=min,max=max,itemDefaultValue=itemDefaultValue,
      multiValueTitle=multiValueTitle)
    # NB: we _skipInitialChecks because of interactions between the
    # Multi and Parameter methods, so both parent constructors must be
    # called before we validate.  However, we need not wait to check
    # default/legal/itemDefault values.
    self.validate()

#  def validate(self):
#    Parameter.validate(self)
#    self.setItemDefaultValue(self.itemDefaultValue)
#    self.setDefaultValue(self.defaultValue)

class StructParameter(Parameter):

  def __init__(self,name,description,defaultValue=None,members=[],
               longDescription=None,groupId=None,hide=False,
               prefix="emulab.net.parameter.",
               inputConstraints=None,_skipInitialChecks=False):
    self.parameters = {}
    self.parameterOrder = []
    for m in members:
       self.addParameter(m)
    super(StructParameter,self).__init__(
      name,description,ParameterType.STRUCT,defaultValue,
      longDescription=longDescription,groupId=groupId,hide=hide,prefix=prefix,
      inputConstraints=inputConstraints,_skipInitialChecks=_skipInitialChecks)

  def addParameter(self,p):
    self.parameterOrder.append(p.name)
    self.parameters[p.name] = p

  @property
  def defaultValue(self):
    if self._defaultValue is not None:
      return self._defaultValue
    v = {}
    for x in self.parameterOrder:
      v[x] = self.parameters[x].defaultValue
    return v

  @property
  def legalValues(self):
    """
    Struct parameters do not have legal values; those must be set on
    each member parameter.
    """
    return None

  def _checkValue(self,value):
    if not isinstance(value,dict):
      raise PortalError("invalid struct parameter '%s' value '%s': not a dict"
                        % (self.name,str(value)))
    for x in sorted(value.keys()):
      if not x in self.parameters:
        raise MissingParameterMemberError(self,x)
      self.parameters[x]._checkValue(value[x])

  def _parseValue(self,value):
    LOG.debug("%s(%s)" % (self.name,str(value)))
    if value == None or value == "":
      value = {}
    elif isinstance(value,six.string_types):
      try:
        value = json.loads(value)
      except:
        raise PortalError("invalid struct parameter JSON string")
    if not isinstance(value,dict):
      raise PortalError("invalid struct parameter '%s' value: not dict (%s)"
                        % (self.name,str(value)))
    nvalue = {}
    # Process supplied parameters (and error on anything extra).
    for x in sorted(value.keys()):
      if not x in self.parameters:
        raise PortalError("unknown struct member '%s' in value" % (x))
      nvalue[x] = self.parameters[x]._parseValue(value[x])
    # Process default values for child params that were not supplied.
    for x in sorted(self.parameters.keys()):
      if x in nvalue:
        continue
      nvalue[x] = self.parameters[x]._parseValue(self.parameters[x].defaultValue)
    for x in self.parameters:
      if not x in value.keys():
        nvalue[x] = self.parameters[x].defaultValue
    LOG.debug("%s(%s) -> %s" % (self.name,str(value),str(nvalue)))
    return DictNamespace(nvalue)

  def setValue(self,value):
    self._checkValue(value)
    for x in sorted(value.keys()):
      self.parameters[x].setValue(value[x])
    self._value = value
    return self.value

  def toParamdef(self):
    fields = [ "name","description","longDescription","type","_defaultValue",
               "groupId","hide","parameterOrder","inputConstraints" ]
    d = dict()
    for f in fields:
      fname = f
      if fname.startswith('_'):
        fname = fname[1:]
      d[fname] = getattr(self,f)
    d["parameters"] = {}
    for name in self.parameters:
      d["parameters"][name] = self.parameters[name].toParamdef()
    return d

  def validate(self):
    for x in self.parameterOrder:
      self.parameters[x].validate()

class MultiStructParameter(Multi,StructParameter):
  def __init__(self,name,description,defaultValue=None,members=[],
               longDescription=None,groupId=None,hide=False,
               min=None,max=None,itemDefaultValue=None,
               multiValueTitle=None,
               prefix="emulab.net.parameter.",inputConstraints=None):
    StructParameter.__init__(
      self,name,description,defaultValue,members=members,
      longDescription=longDescription,groupId=groupId,hide=hide,prefix=prefix,
      inputConstraints=inputConstraints,_skipInitialChecks=True)
    Multi.__init__(
      self,min=min,max=max,itemDefaultValue=itemDefaultValue,
      multiValueTitle=multiValueTitle)
    self.validate()

  def validate(self):
    for x in self.parameterOrder:
      self.parameters[x].validate()
    self._checkValue(self.defaultValue)
    self._parseValue(self.defaultValue)

class Context (object):
  """Handle context for scripts being run inside a portal.

  This class handles context for the portal, including where to put output
  RSpecs and handling parameterized scripts.

  Scripts using this class can also be run "standalone" (ie. not by the
  portal), in which case they take parameters on the command line and put
  RSpecs on the standard output.

  This class is a singleton. Most programs should access it through the
  portal.context variable; any additional "instances" of the object will
  be references to this."""

  """This is a singleton class; only one can exist at a time

  This is implemented by overriding __new__"""
  _instance = None
  _initialized = False
  def __new__(cls, *args, **kwargs):
    if not cls._instance:
      cls._instance = super(Context, cls).__new__(cls, *args, **kwargs)
    return cls._instance

  def __init__ (self):
    # If someone accidentally calls the constructor on the singleton, this
    # prevents us for wiping out its previous state
    if self.__class__._initialized:
      return

    self._request = None
    self._suppressAutoPrint = False
    self._parameters = {}
    self._parameterGroups = { "advanced": "Advanced" }
    self._parameterOrder = []
    self._parameterErrors = []
    self._parameterWarnings = []
    self._parameterWarningsAreFatal = False
    self._bindingDone = False
    self._envParams = {}
    if 'GENILIB_PORTAL_MODE' in os.environ:
      self._standalone = False
      self._portalRequestPath = os.environ.get('GENILIB_PORTAL_REQUEST_PATH',None)
      self._dumpParamsPath = os.environ.get('GENILIB_PORTAL_DUMPPARAMS_PATH',None)
      self._readParamsPath = os.environ.get('GENILIB_PORTAL_PARAMS_PATH',None)
      self._parameterWarningsAreFatal = \
        bool(os.environ.get('GENILIB_PORTAL_WARNINGS_ARE_FATAL',None))
    else:
      self._standalone = True
      self._portalRequestPath = None
    self.__class__._initialized = True

  def bindRequestRSpec (self, rspec):
    """Bind the given request RSpec to the context, so that it can be
    automatically used with methods like printRequestRSpec.

    At the present time, only one request can be bound to a context"""
    if self._request is None:
      self._request = rspec
      # This feature removed until we can think through all the corner cases
      # better
      #sys.excepthook = self._make_excepthook()
      #atexit.register(self._autoPrintRequest)
    else:
      raise MultipleRSpecError

  def makeRequestRSpec (self):
    """Make a new request RSpec, bind it to this context, and return it"""
    rspec = Request()
    self.bindRequestRSpec(rspec)
    return rspec

  def printRequestRSpec (self, rspec = None):
    """Print the given request RSpec, or the one bound to this context if none
    is given.

    If run standalone (not in the portal), the request will be printed to the
    standard output; if run in the portal, it will be placed someplace the
    portal can pick it up.

    If the given rspec does not have a Tour object, this will attempt to
    build one from the file's docstring"""
    self.verifyParameters()

    if rspec is None:
      if self._request is not None:
        rspec = self._request
      else:
        raise NoRSpecError("None supplied or bound to context")

    if not rspec.hasTour():
      tour = igext.Tour()
      if tour.useDocstring():
        rspec.addTour(tour)

    if any(self._parameters):
      rspec.ParameterData(self._parameters)

    self._suppressAutoPrint = True

    rspec.writeXML(self._portalRequestPath)

  def defineParameter (self, name, description, typ, defaultValue, legalValues = None,
                       longDescription = None, inputFieldHint = None, inputConstraints = None, advanced = False, groupId = None, hide=False,
                       multiValue=False,min=None,max=None,itemDefaultValue=None,multiValueTitle=None,
                       prefix="emulab.net.parameter."):
    """Define a new paramter to the script.

    The given name will be used when parameters are bound. The description is
    brief help text that will be shown to the user when making his/her selection. The
    type should be one of the types defined by ParameterType. defaultValue is
    required, but legalValues (a list) is optional; the defaultValue must be
    one of the legalValues. Entries in the legalValues list may be either
    simple strings (eg. "m400"), in which case they will be show directly to
    the user, or 2-element tuples (eg. ("m400", "ARM64"),), in which the second
    entry is what is shown to the user. defaultValue may be a tuple, so that
    one can pass, say, 'legalvalues[0]' for the option. The longDescription is
    an optional, detailed description of this parameter and how it relates to
    other parameters; it will be shown to the user if they ask to see the help,
    or as a pop-up/tooltip.  advanced, group, and groupName all provide parameter
    group abstractions.  Parameter groups are hidden by default from the user,
    and the user can expand them to view and modify them if desired.  By setting
    advanced to True, you create a parameter group named "Advanced Parameters";
    this group will not exist or be shown if none of your parameters set the
    'advanced' argument to True.

    After defining parameters, bindParameters() must be called exactly once."""

    if isinstance(defaultValue, tuple):
      defaultValue = defaultValue[0]

    # Backwards compat for the advanced key.
    if advanced and groupId == None:
      groupId="advanced"

    if multiValue:
      p = MultiParameter(
        name,description,typ,defaultValue,legalValues=legalValues,
        longDescription=longDescription,groupId=groupId,hide=hide,
        min=min,max=max,prefix=prefix,inputFieldHint=inputFieldHint,
        itemDefaultValue=itemDefaultValue,multiValueTitle=multiValueTitle,
        inputConstraints=inputConstraints)
    else:
      p = Parameter(
        name,description,typ,defaultValue,legalValues=legalValues,
        longDescription=longDescription,groupId=groupId,hide=hide,
        prefix=prefix,inputFieldHint=inputFieldHint,
        inputConstraints=inputConstraints)
    self.addParameter(p)
    return p

  def defineStructParameter(self,name,description,defaultValue=None,
                            longDescription=None,advanced=False,groupId=None,hide=False,
                            members=[],multiValue=False,min=None,max=None,
                            itemDefaultValue=None,multiValueTitle=None,
                            inputConstraints=None,
                            prefix="emulab.net.parameter."):
    # Backwards compat for the advanced key.
    if advanced and groupId == None:
      groupId="advanced"

    if multiValue:
      p = MultiStructParameter(
        name,description,defaultValue,longDescription=longDescription,
        groupId=groupId,hide=hide,min=min,max=max,itemDefaultValue=itemDefaultValue,
        multiValueTitle=multiValueTitle,prefix=prefix,members=members,
        inputConstraints=inputConstraints)
    else:
      p = StructParameter(
        name,description,defaultValue,longDescription=longDescription,
        groupId=groupId,hide=hide,prefix=prefix,members=members)
    self.addParameter(p)
    return p

  def addParameter(self,parameter):
    self._parameterOrder.append(parameter.name)
    self._parameters[parameter.name] = parameter
    if len(self._parameters) == 1:
      atexit.register(self._checkBind)

  def defineParameterGroup(self, groupId, groupName):
    """
    Define a parameter group.  Parameters may be added to this group, which has
    an identifying token composed of alphanumeric characters (groupId), and a
    human-readable name (groupName).  Groups are intended to be used for advanced
    parameters; in the portal UI, they hidden in an expandable panel with the
    groupName --- and the user can choose to see and modify them, or not.  You
    do not need to specify any groups; you can simply stuff all your parameters
    into the "Advanced Parameters" group by setting the 'advanced' argument of
    defineParameter to True.  If you need multiple groups, define your own
    groups this way.
    """
    self._parameterGroups[groupId] = groupName

  def bindParameters (self,altParamSrc=None):
    """Returns values for the parameters defined by defineParameter().

    Returns a Namespace (like argparse), so if you call foo = bindParameters(), a
    parameter defined with name "bar" is accessed as foo.bar . Since defaults
    are required, all parameters are guaranteed to have values in the Namespace

    If run standaline (not in the portal), parameters are pulled from the command
    line (try running with --help); if run in the portal, they are pulled from
    the portal itself.  Or, if you provide the altParamSrc argument, you can
    specify your own parameters.  If altParamSrc is a dict, we will bind the
    params as a dict, using the keys as parameter names, and the values as
    parameter values.  If altParamSrc is a geni.rspec.pgmanifest.Manifest, we
    will extract the parameters and their values from the Manifest.  Finally,
    if altParamSrc is a string, we'll try to parse it as a PG manifest xml
    document.  No other forms of altParamSrc are currently specified."""
    for paramName in self._parameterOrder:
      self._parameters[paramName].validate()
    self._bindingDone = True
    if altParamSrc:
      if isinstance(altParamSrc, dict):
        return self._bindParametersDict(altParamSrc)
      elif isinstance(altParamSrc, pgmanifest.Manifest):
        return self._bindParametersManifest(altParamSrc)
      elif isinstance(altParamSrc, (six.string_types)):
        try:
          manifestObj = pgmanifest.Manifest(xml=altParamSrc)
          return self._bindParametersManifest(manifestObj)
        except:
          ex = sys.exc_info()[0]
          raise ParameterBindError("assumed str altParamSrc was xml manifest, but"
                                   " parse error: %s" % (str(ex),))
      else:
        raise ParameterBindError("unknown altParamSrc type: %s"
                                 % (str(type(altParamSrc)),))
    elif self._standalone:
      return self._bindParametersCmdline()
    else:
      if self._dumpParamsPath:
        self._dumpParamsJSON()
      return self._bindParametersEnv()

  def makeParameterWarningsFatal (self):
    """
    Enable this option if you want to return an error to the user for
    incorrect parameter values, even if they can be autocorrected.  This can
    be useful to show the user that
    """
    self._parameterWarningsAreFatal = True

  def reportError (self,parameterError,immediate=False):
    """
    Report a parameter error to the portal.  @parameterError is an
    exception object of type ParameterError.  If @immediate is True,
    your script will exit immediately at this point with a dump of the
    errors (and fatal warnings, if enabled via
    Context.makeParameterWarningsFatal) in JSON format.  If @immediate
    is False, the errors will accumulate until Context.verifyParameters
    is called (and the errors will then be printed).
    """
    self._parameterErrors.append(parameterError)
    if immediate:
      self.verifyParameters()

  def reportWarning (self,parameterError):
    """
    Record a parameter warning.  Warnings will be printed if there are
    other errors or if warnings have been set to be fatal, when
    Context.verifyParameters() is called, or when there is another
    subsequent immediate error.
    """
    self._parameterWarnings.append(parameterError)

  def _splitParamPathIntoComponents(self,paramPath):
    s1 = paramPath.split('.')
    s2 = []
    for c in s1:
      sidx = c.find('[')
      if sidx > -1:
        try:
          idx = int(c[sidx+1:-1])
        except:
          raise PortalError("invalid parameter path '%s': malformed index in component '%s'" % (paramPath,c))
        s2.append(c[:sidx])
        s2.append(idx)
      else:
        s2.append(c)
    return s2

  def _getEnvParamForPath(self,paramPath):
    if self._standalone:
      raise PortalError("not in portal mode; cannot call _getEnvParamForPath")
    if isinstance(paramPath,six.string_types):
      paramPath = self._splitParamPathIntoComponents(paramPath)
    # Try to find the original value dict specified by the path,
    # probably because we want to annotate it:
    v = self._envParams["bindings"]
    lv = None
    for comp in paramPath:
      try:
        lv = v[comp]
        LOG.debug("lv = %s" % (str(lv)))
        v = lv["value"]
        LOG.debug("v = %s" % (str(v)))
      except:
        if dodebug:
          import traceback
          traceback.print_exc()
        raise PortalError(
          "nonexistent parameter value at component '%s' in path '%s'"
          % (str(comp),str(paramPath)))
    return lv

  def verifyParameters (self):
    """
    If there have been calls to Context.parameterError, and/or to
    Context.parameterWarning (and Context.makeParameterWarningsFatal has
    been called, making warnings fatal), this function will spit out some
    nice JSON-formatted exception info on stderr
    """
    if len(self._parameterErrors) == 0 \
      and (len(self._parameterWarnings) == 0 \
        or not self._parameterWarningsAreFatal):
      return 0

    if not self._standalone and self._readParamsPath is not None:
      #
      # Return the same blob to the frontend that we received, but
      # annotate it with errors/warnings and changed values:
      #
      erridx = 1
      if len(self._parameterErrors):
        self._envParams["errors"] = {}
      for err in self._parameterErrors:
        self._envParams["errors"][str(erridx)] = {}
        for param in err.params:
          try:
            v = self._getEnvParamForPath(param)
            LOG.debug("v = %s" % (str(v)))
          except Exception as e:
            newmsg = "Double fault: while trying to generate error (%s, %s), encountered malformed parameter path: %s" % (str(param),err.message,e.message)
            self._envParams["errors"][str(erridx)] = dict(message=newmsg)
            erridx += 1
            continue
          else:
            if not "errors" in v:
              v["errors"] = []
            v["errors"].append(str(erridx))
        for param in err.fixedValues.keys():
          try:
            v = self._getEnvParamForPath(param)
            LOG.debug("v = %s" % (str(v)))
          except Exception as e:
            newmsg = "Double fault: while trying to update value (%s, %s), encountered malformed parameter path: %s" % (str(param),err.message,e.message)
            self._envParams["errors"][str(erridx)] = dict(message=newmsg)
            erridx += 1
            continue
          else:
            v["fixedValue"] = err.fixedValues[param]
        self._envParams["errors"][str(erridx)] = dict(message=err.message)
        erridx += 1
      if len(self._parameterWarnings):
        self._envParams["warnings"] = {}
      for err in self._parameterWarnings:
        self._envParams["warnings"][str(erridx)] = {}
        for param in err.params:
          try:
            v = self._getEnvParamForPath(param)
          except Exception as e:
            newmsg = "Double fault: while trying to generate warning (%s, %s), encountered malformed parameter path: %s" % (str(param),err.message,e.message)
            self._envParams["warnings"][str(erridx)] = dict(message=newmsg)
            erridx += 1
            continue
          else:
            if not "warnings" in v:
              v["warnings"] = []
            v["warnings"].append(str(erridx))
        for param in err.fixedValues.keys():
          try:
            v = self._getEnvParamForPath(param)
            LOG.debug("v = %s" % (str(v)))
          except Exception as e:
            newmsg = "Double fault: while trying to update value (%s, %s), encountered malformed parameter path: %s" % (str(param),err.message,e.message)
            self._envParams["errors"][str(erridx)] = dict(message=newmsg)
            erridx += 1
            continue
          else:
            v["fixedValue"] = err.fixedValues[param]
        self._envParams["warnings"][str(erridx)] = dict(message=err.message)
        erridx += 1
      json.dump(self._envParams,sys.stderr,cls=PortalJSONEncoder)
    else:
      #
      # Dump a JSON list of typed errors.
      #
      ea = []
      ea.extend(self._parameterErrors)
      ea.extend(self._parameterWarnings)
      json.dump(ea,sys.stderr,cls=PortalJSONEncoder)

    #
    # Exit with a count of errors and (fatal) warnings, added to 100 ...
    # try to distinguish ourselves meaningfully!
    #
    retcode = len(self._parameterErrors)
    if self._parameterWarningsAreFatal:
      retcode += len(self._parameterWarnings)
    sys.exit(100+retcode)

  def suppressAutoPrint (self):
    """
    Suppress the automatic printing of the bound RSpec that normally happens
    when the program exits.
    """
    self._suppressAutoPrint = True

  def _bindParametersCmdline (self):
    parser = argparse.ArgumentParser()
    for name in self._parameterOrder:
      p = self._parameters[name]
      LOG.debug("%s = %s" % (str(p.name),str(p.defaultValue)))
      # Brutal hack to force p._parseValue to be called.  Argparse will
      # only invoke the `type` function for the unsupplied default case
      # if the value is any type of string.
      default = p.defaultValue
      if isinstance(default,dict) or isinstance(default,list):
        default = json.dumps(default,sort_keys=True, separators=(',',':'))
      parser.add_argument("--" + name,
                          type    = p._parseValue,
                          default = default,
                          choices = p.legalValues,
                          help    = p.description)
    args = parser.parse_args()
    for name in self._parameterOrder:
      self._parameters[name].setValue(getattr(args, name))
    return DictNamespace(args.__dict__)

  def _flattenEnvParams(self,p):
    """
    The parameter block we get back from the frontend may be a giant
    dict with metadata and values specified as "value": <value> pairs
    within each parameter descriptor.  So "flatten" the value pairs into
    the right data structure.
    """
    if not isinstance(p,list) and not isinstance(p,dict):
      return p
    elif isinstance(p,dict):
      if "value" in p:
        return self._flattenEnvParams(p["value"])
      ret = {}
      for k in p.keys():
        ret[k] = self._flattenEnvParams(p[k])
      LOG.debug("ret -> %s" % (str(ret)))
    elif isinstance(p,list):
      ret = []
      for x in p:
        ret.append(self._flattenEnvParams(x))
      LOG.debug("ret -> %s" % (str(ret)))
    return ret

  def _bindParametersEnv (self):
    """
    Read parameter values from the environment (e.g., from the
    frontend).  You should only use this path if you understand the
    representation(s) the frontend uses to send parameter values.
    """
    if self._readParamsPath:
      f = open(self._readParamsPath, "r")
      self._envParams = json.load(f)
      f.close()
    if len(self._envParams):
      self._flattenedEnvParams = self._flattenEnvParams(self._envParams["bindings"])
    else:
      self._flattenedEnvParams = {}
    LOG.debug("flattened: %s" % (str(self._flattenedEnvParams)))
    return self._bindParametersDict(self._flattenedEnvParams)
    
  def _bindParametersDict(self,paramValues):
    """
    This is the generic parameter value parse/bind function.  For each
    defined parameter (self._parameters.keys()), in definition order
    (self._parameterOrder), extract a value from the supplied value.
    Each Parameter subclass provides a _parseValue method to perform the
    extraction, and can thus define the range of input values it
    supports.  Once a value is extracted, we set that value (via the
    setValue method) on the unbound parameter, so that
    self._parameters[name].value contains the extracted value.  Note
    that setValue may throw an error even if _parseValue did not, since
    there may be additional constraints other than type correctness
    (e.g., a range of allowed values.)
    """
    namespace = DictNamespace()
    for name in self._parameterOrder:
      p = self._parameters[name]
      val = paramValues.get(name, p.defaultValue)
      LOG.debug("paramValue(%s): %s" % (str(p),str(val)))
      try:
        val = p._parseValue(val)
      except ParameterError as e:
        if dodebug:
          import traceback
          traceback.print_exc()
        self.reportError(e)
        continue
      except Exception as e:
        if dodebug:
          import traceback
          traceback.print_exc()
        self.reportError(
          ParameterError("Could not parse '%s' value '%s': %s"
                         % (name,str(val),str(e)),[name]))
        continue
      try:
        p.setValue(val)
      except ParameterError as e:
        if dodebug:
          import traceback
          traceback.print_exc()
        self.reportError(e)
        continue
      except Exception as e:
        if dodebug:
          import traceback
          traceback.print_exc()
        self.reportError(
          ParameterError("Illegal value '%s' for parameter '%s': %s"
                         % (str(val),name,str(e)),[name]))
        continue
      setattr(namespace, name, val)
    # This might not return. 
    self.verifyParameters()
    self._bindingDone = True
    return namespace

  def _bindParametersManifest(self,manifest):
    """
    This method extracts parameter values from a
    `geni.rspec.pgmanifest.Manifest` class, places them in a dict, and
    invokes self._bindParametersDict.
    """
    pdict = {}
    for manifestParameter in manifest.parameters:
      pdict[manifestParameter.name] = manifestParameter.value
    return self._bindParametersDict(pdict)

  def _dumpParamsJSON (self):
    #
    # Output the parameter dict in sorted order (sorted in terms of parameter
    # definition order).  This is correct, identical to json.dump (other than
    # key order), and much easier than subclassing json.JSONEncoder :).
    #
    didFirst = False
    f = open(self._dumpParamsPath, "w+")
    f.write('{')
    for name in self._parameterOrder:
      if didFirst:
        f.write(', ')
      else:
        didFirst = True
      p = self._parameters[name]
      pd = p.toParamdef()
      # A little backwards-compat hack.
      if p.groupId and p.groupId in self._parameterGroups:
        pd['groupName'] = self._parameterGroups[p.groupId]
      json.dump(name,f)
      f.write(': ')
      json.dump(pd,f)
    f.write('}')
    f.close()
    return

  def _checkBind (self):
    if len(self._parameters) > 0 and not self._bindingDone:
      warnings.warn("Parameters were defined, but never bound with " +
                    " bindParameters()", RuntimeWarning)

  def _autoPrintRequest (self):
    if not self._suppressAutoPrint:
      self.printRequestRSpec()

  def _make_excepthook (self):
    old_excepthook = sys.excepthook
    def _excepthook(type, value, traceback):
      self.suppressAutoPrint()
      return old_excepthook(type, value, traceback)
    return _excepthook

context = Context()
"""
Module-global Context object - most users of this module should simply use
this rather than trying to create a new Context object
"""

def get_context():
  return context

class PortalJSONEncoder(json.JSONEncoder):
  def default(self, o):
    if isinstance(o,PortalError):
      return o.__objdict__()
    else:
      # First try the default encoder:
      try:
        return json.JSONEncoder.default(self, o)
      except Exception:
        try:
          # Then try to return a string, at least
          return str(o)
        except Exception:
          # Let the base class default method raise the TypeError
          return json.JSONEncoder.default(self, o)

#
# Define some exceptions.  Everybody should subclass PortalError.
#
class PortalError (Exception):
  def __init__(self,message):
    super(PortalError, self).__init__()
    self.message = message

  def __str__(self):
    return self.__class__.__name__ + ": " + self.message

  def __objdict__(self):
    retval = dict({ 'errorType': self.__class__.__name__, })
    for k in self.__dict__.keys():
      if k == 'errorType':
        continue
      if k.startswith('_'):
        continue
      retval[k] = self.__dict__[k]
    return retval


class ParameterError (PortalError):
  """
  A simple class to describe a parameter error.  If you need to report
  an error with a user-specified parameter value to the Portal UI,
  please create (don't throw) one of these error objects, and tell the
  Portal about it by calling Context.reportError.
  """
  def __init__(self,message,paramList,fixedValues={}):
    """
    Create a ParameterError.  @message is the overall error message;
    in the Portal Web UI, it will be displayed near each involved
    parameter for maximal impact.  @paramList is a list of the
    parameters that are involved in the error (often it is the
    combination of parameters that creates the error condition).
    The Portal UI will show this error message near *each* involved
    parameter to increase user understanding of the error.
    """
    super(ParameterError, self).__init__(message)
    self.params = paramList or []
    self.fixedValues = fixedValues or {}


class ParameterWarning (PortalError):
  """
  A simple class to describe a parameter warning.  If you need to
  report an warning with a user-specified parameter value to the
  Portal UI, please create (don't throw) one of these error objects,
  and tell the Portal about it by calling Context.reportWarning .  The
  first time the Portal UI runs your geni-lib script with a user's
  parameter values, it turns on the "warnings are fatal" mode (and
  then warnings are reported as errors).  This gives you a chance to
  warn the user that they might be about to do something stupid,
  and/or suggest a set of modified values that will improve the
  situation.  .
  """
  def __init__(self,message,paramList,fixedValues={}):
    """
    Create a ParameterWarning.  @message is the overall error
    message; in the Portal Web UI, it will be displayed near each
    involved parameter for maximal impact.  @paramList is a list of
    the parameters that are involved in the warning (often it is the
    combination of parameters that creates the error condition).
    The Portal UI will show this warning message near *each*
    involved parameter to increase user understanding of the error.
    If you supply the @fixedValue dict, the Portal UI will change
    the values the user submitted to those you suggest (and it will
    tell them it did so).  You might want to supply @fixedValues for
    a proper warning, because if something is only a warning, that
    implies your script can and will proceed in the absence of
    further user input.  But sometimes we want to let the user know
    that a parameter change will occur, so we warn them and
    autocorrect!
    """
    super(ParameterWarning, self).__init__(message)
    self.params = paramList or []
    self.fixedValues = fixedValues or {}

class MissingParameterMemberError(PortalError):
  def __init__(self,param,memberName):
    super(MissingParameterMemberError, self).__init__(
      memberName + " not in " + param.name)
    self._param = param

class IllegalParameterDefaultError (PortalError):
  def __init__ (self,val,param=None):
    super(IllegalParameterDefaultError, self).__init__("no message?")
    self._val = val
    self._param = param

  def __str__ (self):
    namestr = ""
    if self._param:
      namestr = " for parameter '%s'" % (str(self._param.name))
    return "%s given as a default value%s, but is not listed as a legal value" % (str(self._val),namestr)


class IllegalParameterValueError (PortalError):
  def __init__ (self,val,param=None):
    super(IllegalParameterValueError, self).__init__("no message?")
    self._val = val
    self._param = param

  def __str__ (self):
    namestr = ""
    if self._param:
      namestr = " for parameter '%s'" % (str(self._param.name))
    return "value '%s'%s is not a legal value" % (str(self._val),namestr)


class ParameterBindError (PortalError):
  def __init__ (self,val,param=None):
    super(ParameterBindError, self).__init__("no message?")
    self._val = val
    self._param = param

  def __str__ (self):
    namestr = ""
    if self._param:
      namestr = " for parameter '%s'" % (str(self._param.name))
    return "bad parameter binding: %s%s" % (str(self._val),namestr)


class NoRSpecError (PortalError):
  def __init__ (self,val):
    super(NoRSpecError, self).__init__("no message?")
    self._val = val

  def __str__ (self):
    return "No RSpec given: %s" % str(self._val,)

class MultipleRSpecError (PortalError):
  def __init__ (self,val):
    super(MultipleRSpecError, self).__init__("no message?")
    self._val = val

  def __str__ (self):
    return "Only one RSpec can be bound to a portal.Context"
