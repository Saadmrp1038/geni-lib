

from lxml import etree as ET

from ..pg import Resource, Node, Link, Request, Namespaces

ANSIBLE_NAMESPACE = getattr(Namespaces, "ANSIBLE", None)
if not ANSIBLE_NAMESPACE:
    import geni.namespaces as GNS
    ANSIBLE_NAMESPACE = GNS.Namespace("ansible", "http://www.protogeni.net/resources/rspec/ext/ansible/1")

class Playbook(Resource):
    """
    An ansible playbook lists tasks.  Most commonly it is associated with a role or
    collection as a top-level method of pulling in per-role tasks; but it can also
    stand on its own as a task list.

    Playbook runs typically require inventory and variable overrides for customization.
    If you are integrating a classic role (e.g. the `emulab-docker` role), you can use
    the default inventory, which places all hosts into the `all` group, and further adds
    hosts to groups named for the applied roles.  If your role/playbook makes custom use
    of the `all` group, or otherwise cannot be part of global inventory/overrides files,
    you will need to set the `inventory_name` and/or `overrides_name` values so that our
    default generators create separate files, and our playbook runner uses them.

    If you require additional custom control of inventory or overrides generation, you
    can specify paths to generator executables, whose stdout will be sent to the
    `inventory_name` or `overrides_name` files you define.  Non-zero exit code will fail the
    playbook run and the entire experiment startup sequence.

    If you require control of playbook run, you can provide a custom runner.

    Note that all inventory/overrides/runner paths are relative to `path`, which itself is
    relative to the profile repository checkout dir.

    If `become` is None, the Emulab user who created the experiment will be the "become"
    user.  If you need `root` execution, set `become` to `root`, etc.
    """

    __NAMESPACES__ = [ ANSIBLE_NAMESPACE ]

    def __init__(self,name,path=None,inventory_name=None,overrides_name=None,
                 inventory_generator_path=None,overrides_generator_path=None,
                 runner_path=None,pre_hook=None,post_hook=None,become=None):
        super(Playbook, self).__init__()
        self.addNamespace(ANSIBLE_NAMESPACE)
        self.name = name
        self.path = path
        self.inventory_name = inventory_name
        self.overrides_name = overrides_name
        self.inventory_generator_path = inventory_generator_path
        self.overrides_generator_path = overrides_generator_path
        self.runner_path = runner_path
        self.pre_hook = pre_hook
        self.post_hook = post_hook
        self.become = become

    def _write(self,root):
        el = ET.SubElement(root,"{%s}playbook" % (ANSIBLE_NAMESPACE,))
        el.attrib["name"] = self.name
        el.attrib["path"] = self.path or ""
        el.attrib["inventory_name"] = self.inventory_name or ""
        el.attrib["overrides_name"] = self.overrides_name or ""
        el.attrib["inventory_generator_path"] = self.inventory_generator_path or ""
        el.attrib["overrides_generator_path"] = self.overrides_generator_path or ""
        el.attrib["runner_path"] = self.runner_path or ""
        el.attrib["pre_hook"] = self.pre_hook or ""
        el.attrib["post_hook"] = self.post_hook or ""
        el.attrib["become"] = self.become or ""
        super(Playbook, self)._write(el)
        return el

class addPlaybook(object):
    __NAMESPACES__ = [ ANSIBLE_NAMESPACE ]
    def __init__(self, playbook):
        self._playbook = playbook
    
    def _write(self, root):
        return self._role._write(root)
Request.EXTENSIONS.append(("addPlaybook",addPlaybook))

class Role(Resource):
    """
    An ansible role groups related tasks, files, vars, etc into a well-known directory
    structure (https://docs.ansible.com/ansible/latest/user_guide/playbooks_reuse_roles.html).
    It may have top-level playbooks that apply part or all of the overall role (e.g.,
    modularized member roles).

    The `group` parameter controls default inventory generation.  If None, the `name`
    of the role will be used as the sole group; if non-empty, this value will be used to
    group the The empty string should not be used.

    If `source` (a git clone value) is provided, that git repo will be cloned into the
    profile repository checkout dir in `path`.  Otherwise, `path` should point to a
    canonical Ansible `role` dir structure (e.g. https://docs.ansible.com/ansible/latest/user_guide/playbooks_reuse_roles.html).
    """

    __NAMESPACES__ = [ ANSIBLE_NAMESPACE ]

    def __init__(self,name,path=None,source=None,source_type=None,group=None,auto=True,playbooks=[]):
        super(Role, self).__init__()
        self.addNamespace(ANSIBLE_NAMESPACE)
        self.name = name
        self.path = path
        self.source = source
        self.source_type = source_type
        self.group = group
        self.auto = auto
        self.playbooks = playbooks or []

    def _write(self,root):
        el = ET.SubElement(root,"{%s}role" % (ANSIBLE_NAMESPACE,))
        el.attrib["name"] = self.name
        el.attrib["path"] = self.path or ""
        el.attrib["source"] = self.source or ""
        el.attrib["source_type"] = self.source_type or ""
        el.attrib["group"] = self.group or ""
        el.attrib["auto"] = str(self.auto)
        for p in self.playbooks:
            p._write(el)
        super(Role, self)._write(el)
        return el

class addRole(object):
    __NAMESPACES__ = [ ANSIBLE_NAMESPACE ]
    def __init__(self, role):
        self._role = role
    
    def _write(self, root):
        self._role._write(root)
Request.EXTENSIONS.append(("addRole",addRole))

class RoleBinding(object):
    """
    Binds a declared role name to a node.
    """

    __NAMESPACES__ = [ ANSIBLE_NAMESPACE ]

    def __init__(self, role):
        self.role = role

    def _write(self,root):
        el = ET.SubElement(root,"{%s}role_binding" % (ANSIBLE_NAMESPACE,))
        el.attrib["role"] = self.role
        return el

class bindRole(object):
    __NAMESPACES__ = [ ANSIBLE_NAMESPACE ]
    def __init__(self, binding):
        self._binding = binding
    
    def _write(self, root):
        self._binding._write(root)
Node.EXTENSIONS.append(("bindRole",bindRole))

class Override(Resource):
    """
    Override an Ansible variable, on a global or per-host basis.  You can set
    either a (computed) raw value, or bind to a parameter name (source="parameter",
    source_name="<param-fqn>") or password (source="password", source_name="<password-name>")
    Currently, the definition of the parameter binding is made at experiment runtime on the
    client side; this is necessary for per-experiment encrypted value support, and may
    inspire other cases.  :shrug:
    """

    __NAMESPACES__ = [ ANSIBLE_NAMESPACE ]

    def __init__(self,name,value=None,source=None,source_name=None,on_empty=True):
        super(Override, self).__init__()
        self.addNamespace(ANSIBLE_NAMESPACE)
        self.name = name
        self.value = value
        self.source = source
        self.source_name = source_name
        self.on_empty = on_empty

    def _write(self,root):
        el = ET.SubElement(root,"{%s}override" % (ANSIBLE_NAMESPACE,))
        el.attrib["name"] = self.name
        el.attrib["source"] = self.source or ""
        el.attrib["source_name"] = self.source_name or ""
        el.attrib["on_empty"] = str(self.on_empty)
        if self.value is not None:
            el.text = self.value
        super(Override, self)._write(el)
        return el

class addOverride(object):
    __NAMESPACES__ = [ ANSIBLE_NAMESPACE ]
    def __init__(self, override):
        self._override = override
    
    def _write(self, root):
        self._override._write(root)
Request.EXTENSIONS.append(("addOverride",addOverride))
Node.EXTENSIONS.append(("addOverride",addOverride))
