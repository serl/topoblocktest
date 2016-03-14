import re, wrapt
from .bash import CommandBlock

class ConfigurationError(Exception):
    pass

def add_comment(action):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        def _execute(*args, **kwargs):
            return CommandBlock() + '' + 'echo "{} {}"'.format(action, instance.description) + wrapped(*args, **kwargs)
        return _execute(*args, **kwargs)
    return wrapper

class Entity:
    __shortname = 'x'
    def __init__(self):
        self.links = []
    def add_to(self, master):
        master.entities.append(self)
        return self #chaining ;)
    @add_comment('creating')
    def create(self):
        self.check_configuration()
        return CommandBlock()
    @add_comment('configuring')
    def configure(self):
        return CommandBlock()
    @add_comment('destroying')
    def destroy(self):
        return CommandBlock()
    def check_configuration(self):
        if self.name is None:
            raise ConfigurationError("name is missing")
    @property
    def entity_type_name(self):
        hierarchy = []
        ccls = self.__class__
        while ccls is not object:
            try:
                hierarchy.append(getattr(ccls, '_'+ccls.__name__+'__shortname'))
            except AttributeError:
                pass
            ccls = ccls.__bases__[0]
        return '-'.join(reversed(hierarchy))
    @property
    def name(self):
        return self.__name
    @name.setter
    def name(self, value):
        self.__name = value
        try:
            self.name_id = re.search(r'(\d+)$', self.__name).group()
        except:
            self.name_id = None
    @property
    def description(self):
        return self.name

    def __str__(self):
        return self.description
    def __repr__(self):
        return self.__str__()


class Netns(Entity):
    __shortname = 'ns'
    def __init__(self, name=None):
        super().__init__()
        self.name = name
        self.routes = []
    def add_route(self, destination, endpoint):
        self.routes.append((destination, endpoint))
    def create(self):
        return super().create() + "ip netns add {self.name}".format(self=self)
    def configure(self):
        cmds = CommandBlock()
        for r in self.routes:
            cmds += "ip netns exec {self.name} ip route add "+r[0]+" via "+r[1].ip_address+" proto static"
        return super().configure() + cmds.format(self=self)
    def destroy(self):
        return super().destroy() + "ip netns delete {self.name}".format(self=self)

class DockerContainer(Entity):
    pass


class OVS(Entity):
    __shortname = 'ovs'
    def __init__(self, name=None):
        super().__init__()
        self.name = name
    def create(self):
        return super().create() + "ovs-vsctl add-br {self.name}".format(self=self)
    def configure(self):
        return None
    def destroy(self):
        return super().destroy() + "ovs-vsctl del-br {self.name}".format(self=self)


class Endpoint:
    @classmethod
    def get(cls, arg):
        if isinstance(arg, cls):
            return arg
        if isinstance(arg, Entity):
            return cls(arg)
        if isinstance(arg, tuple):
            return cls(*arg)
    def __init__(self, entity, ip_address=None, name=None):
        self.entity = entity
        self.name = name
        self.ip_address = None
        self.ip_size = None
        if ip_address is not None:
            if '/' in ip_address:
                parts = ip_address.split('/')
                self.ip_address = parts[0]
                self.ip_size = int(parts[1])
            else:
                self.ip_address = ip_address
                self.ip_size = 24
    def __str__(self):
        return '{self.name} ({self.ip_address}/{self.ip_size})'.format(self=self)
    def __repr__(self):
        return self.__str__()
    def disable_offloading(self):
        return 'ethtool -K {self.name} tx off gso off sg off gro off'.format(self=self)


class Link:
    @staticmethod
    def declare(e1, e2, link_type=None, **kwargs):
        e1 = Endpoint.get(e1)
        e2 = Endpoint.get(e2)

        if type(e1.entity) is OVS and type(e2.entity) is OVS:
            if link_type is None:
                link_type = 'patch'
            if link_type == 'veth':
                return Link_OVS_OVS_veth(e1, e2, **kwargs)
            elif link_type == 'patch':
                return Link_OVS_OVS_patch(e1, e2, **kwargs)
            else:
                raise ConfigurationError('unrecognized type: {}'.format(link_type))
        if (type(e1.entity) is OVS and type(e2.entity) is Netns) or (type(e1.entity) is Netns and type(e2.entity) is OVS):
            #make sure e1 is the OVS
            if type(e1.entity) is Netns and type(e2.entity) is OVS:
                e2, e1 = e1, e2
            if link_type is None:
                link_type = 'port'
            if link_type == 'veth':
                return Link_OVS_Netns_veth(e1, e2, **kwargs)
            elif link_type == 'port':
                return Link_OVS_Netns_port(e1, e2, **kwargs)
            else:
                raise ConfigurationError('unrecognized type: {}'.format(link_type))
        if type(e1.entity) is Netns and type(e2.entity) is Netns:
            if link_type is not None and link_type != 'veth':
                raise ConfigurationError('unrecognized type: {}'.format(link_type))
            return Link_Netns_Netns_veth(e1, e2, **kwargs)

    def __init__(self, e1, e2, disable_offloading=False, **kwargs):
        self.e1 = e1
        self.e2 = e2
        self.disable_offloading = disable_offloading
        e1.entity.links.append(self)
        e2.entity.links.append(self)
    @add_comment('creating')
    def create(self):
        return CommandBlock()
    @add_comment('destroying')
    def destroy(self):
        return CommandBlock()
    @property
    def description(self):
        return "link between {self.e1.entity.name} and {self.e2.entity.name} of type {self.__class__.__name__} ({self.e1.name} to {self.e2.name})".format(self=self)

    def __str__(self):
        return self.description
    def __repr__(self):
        return self.__str__()

    # ensure no double links are configured (they'll be skipped by Master)
    # links will be skipped EVEN IF they're of DIFFERENT TYPES
    # but they are NOT skipped if they have different ip addresses
    def __key(self):
        return tuple( sorted([hash(self.e1), hash(self.e2)]) )
    def __hash__(self):
        return hash(self.__key())
    def __eq__(self, other):
        return self.__key() == other.__key()
    def __ne__(self, other):
        return not self.__eq__(other)

class Link_OVS_OVS_veth(Link):
    def __init__(self, e1, e2, **kwargs):
        super().__init__(e1, e2, **kwargs)
    def assign_attributes(self):
        # veth names are limited to 15 chars(!)
        if self.e1.name is None:
            self.e1.name = 'veth-ovs-{e1.entity.name_id}-{e2.entity.name_id}'.format(**self.__dict__)
        if self.e2.name is None:
            self.e2.name = 'veth-ovs-{e2.entity.name_id}-{e1.entity.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        cmds = CommandBlock()
        #create the links
        cmds += "ip link add {e1.name} type veth peer name {e2.name}"
        #configure one side
        cmds += "ovs-vsctl add-port {e1.entity.name} {e1.name}"
        cmds += "ip link set {e1.name} up"
        if self.disable_offloading:
            cmds += self.e1.disable_offloading()
        #configure the other side
        cmds += "ovs-vsctl add-port {e2.entity.name} {e2.name}"
        cmds += "ip link set {e2.name} up"
        if self.disable_offloading:
            cmds += self.e2.disable_offloading()
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        self.assign_attributes()
        return super().destroy() + "ip link delete {e1.name}".format(**self.__dict__)

class Link_OVS_OVS_patch(Link):
    def __init__(self, e1, e2, **kwargs):
        super().__init__(e1, e2, **kwargs)
    def assign_attributes(self):
        if self.e1.name is None:
            self.e1.name = 'patch-{e2.entity.name}-{e1.entity.name_id}'.format(**self.__dict__)
        if self.e2.name is None:
            self.e2.name = 'patch-{e1.entity.name}-{e2.entity.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        cmds = CommandBlock()
        cmds += "ovs-vsctl add-port {e1.entity.name} {e1.name} -- set Interface {e1.name} type=patch options:peer={e2.name}"
        cmds += "ovs-vsctl add-port {e2.entity.name} {e2.name} -- set Interface {e2.name} type=patch options:peer={e1.name}"
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        return None # destroyed by the bridge


class Link_OVS_Netns_veth(Link):
    # e1 is the ovs, e2 is the netns
    def __init__(self, e1, e2, **kwargs):
        super().__init__(e1, e2, **kwargs)
    def assign_attributes(self):
        if self.e1.name is None:
            self.e1.name = 'v-ovs{e1.entity.name_id}-ns{e2.entity.name_id}'.format(**self.__dict__)
        if self.e2.name is None:
            self.e2.name = 'v-ns{e2.entity.name_id}-ovs{e1.entity.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        cmds = CommandBlock()
        #create the links
        cmds += "ip link add {e1.name} type veth peer name {e2.name}"
        #configure ovs side
        cmds += "ovs-vsctl add-port {e1.entity.name} {e1.name}"
        cmds += "ip link set {e1.name} up"
        if self.disable_offloading:
            cmds += self.e1.disable_offloading()
        #configure namespace side
        cmds += "ip link set {e2.name} netns {e2.entity.name}"
        cmds += "ip netns exec {e2.entity.name} ip link set dev {e2.name} up"
        if self.e2.ip_address is not None:
            cmds += "ip netns exec {e2.entity.name} ip address add {e2.ip_address}/{e2.ip_size} dev {e2.name}"
        if self.disable_offloading:
            cmds += ("ip netns exec {e2.entity.name} " + self.e2.disable_offloading())
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        self.assign_attributes()
        return super().destroy() + "ip link delete {e1.name}".format(**self.__dict__)

class Link_OVS_Netns_port(Link):
    # e1 is the ovs, e2 is the netns
    def __init__(self, e1, e2, **kwargs):
        super().__init__(e1, e2, **kwargs)
    def assign_attributes(self):
        if self.e2.name is None:
            self.e2.name = 'p-{e1.entity.name}-{e2.entity.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        cmds = CommandBlock()
        cmds += "ovs-vsctl add-port {e1.entity.name} {e2.name} -- set Interface {e2.name} type=internal"
        cmds += "ip link set {e2.name} netns {e2.entity.name}"
        cmds += "ip netns exec {e2.entity.name} ip link set dev {e2.name} up"
        if self.e2.ip_address is not None:
            cmds += "ip netns exec {e2.entity.name} ip address add {e2.ip_address}/{e2.ip_size} dev {e2.name}"
        if self.disable_offloading:
            cmds += ("ip netns exec {e2.entity.name} " + self.e2.disable_offloading())
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        return None # destroyed by the bridge

class Link_Netns_Netns_veth(Link):
    def __init__(self, e1, e2, **kwargs):
        super().__init__(e1, e2, **kwargs)
    def assign_attributes(self):
        # veth names are limited to 15 chars(!)
        if self.e1.name is None:
            self.e1.name = 'veth-ns-{e1.entity.name_id}-{e2.entity.name_id}'.format(**self.__dict__)
        if self.e2.name is None:
            self.e2.name = 'veth-ns-{e2.entity.name_id}-{e1.entity.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        cmds = CommandBlock()
        #create the links
        cmds += "ip link add {e1.name} type veth peer name {e2.name}"
        #configure one side
        cmds += "ip link set {e1.name} netns {e1.entity.name}"
        cmds += "ip netns exec {e1.entity.name} ip link set dev {e1.name} up"
        if self.e1.ip_address is not None:
            cmds += "ip netns exec {e1.entity.name} ip address add {e1.ip_address}/{e1.ip_size} dev {e1.name}"
        if self.disable_offloading:
            cmds += ("ip netns exec {e1.entity.name} " + self.e1.disable_offloading())
        #configure the other side
        cmds += "ip link set {e2.name} netns {e2.entity.name}"
        cmds += "ip netns exec {e2.entity.name} ip link set dev {e2.name} up"
        if self.e2.ip_address is not None:
            cmds += "ip netns exec {e2.entity.name} ip address add {e2.ip_address}/{e2.ip_size} dev {e2.name}"
        if self.disable_offloading:
            cmds += ("ip netns exec {e2.entity.name} " + self.e2.disable_offloading())
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        self.assign_attributes()
        return super().destroy() + "ip netns exec {e1.entity.name} ip link delete {e1.name}".format(**self.__dict__)


class Master:
    def __init__(self):
        self.entities = []
    def add(self, entity):
        self.entities.append(entity)

    def find_unique_attribute(self, entity, attribute_name, fmt, n_limit=None):
        if getattr(entity, attribute_name) is not None:
            return
        n = 1
        good_attr = False
        while not good_attr:
            proposed_attr = fmt.format(entity=entity, n=n)
            good_attr = all([getattr(e, attribute_name) != proposed_attr for e in self.entities])
            n += 1
            if n_limit is not None and n > n_limit:
                raise ConfigurationError('unable to find a good value')
        setattr(entity, attribute_name, proposed_attr)

    def assign_attributes(self):
        for entity in self.entities:
            self.find_unique_attribute(entity, 'name', '{entity.entity_type_name}{n}')
            # self.find_unique_attribute(entity, 'ip_address', '10.112.{n}.1', 255)

    @property
    def links(self):
        links = []
        links_set = set()
        links_set_add = links_set.add
        for e in self.entities:
            links += [l for l in e.links if not (l in links_set or links_set_add(l))]
        return links

    def __get_commands(self, collection, fn):
        commands = CommandBlock()
        for obj in collection:
            commands += getattr(obj, fn)()
        return commands
    def setup(self):
        self.assign_attributes()
        return self.__get_commands(self.entities, 'create') + self.__get_commands(self.links, 'create') + self.__get_commands(self.entities, 'configure')
    def cleanup(self):
        return self.__get_commands(self.links, 'destroy') + self.__get_commands(self.entities, 'destroy')

    def get_script(self, enable_routing=True, include_calls=True):
        res = CommandBlock.root_check()
        res += 'function opg_setup {'
        res += 'set -e'
        if enable_routing:
            res += 'sysctl -w net.ipv4.ip_forward=1'
        res += self.setup()
        res += ''
        res += 'set +e'
        res += 'sleep 1'
        res += '}'
        res += ''
        res += 'function opg_cleanup {'
        res += self.cleanup()
        res += ''
        if enable_routing:
            res += 'sysctl -w net.ipv4.ip_forward=0'
        res += 'sleep 1'
        res += '}'
        if include_calls:
            res += ''
            res += 'trap opg_cleanup EXIT'
            res += 'opg_setup'
        return res
