import re, wrapt

class ConfigurationError(Exception):
    pass

def add_comment(action):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        def _execute(*args, **kwargs):
            return "echo " + action + " " + instance.description + "\n" + wrapped(*args, **kwargs)
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
        return ""
    @add_comment('destroying')
    def destroy(self):
        return ""
    def check_configuration(self):
        if self.name is None:
            raise ConfigurationError("name is missing")
    @property
    def entity_name(self):
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


class Container(Entity):
    pass

class Netns(Container):
    __shortname = 'ns'
    def __init__(self, name):
        super().__init__()
        self.name = name
    def create(self):
        return super().create() + "ip netns add {self.name}".format(self=self)
        #return "ovs-vsctl add-br {name} && ip link set dev {name} up && ip address add {ip_address}/{cidr} dev {name}".format(self=self)
    def destroy(self):
        return super().destroy() + "ip netns delete {self.name}".format(self=self)

class DockerContainer(Container):
    pass


class Bridge(Entity):
    pass
    # __shortname = 'br'
    # def check_configuration(self):
    #     super().check_configuration()
    #     if self.ip_address is None:
    #         raise ConfigurationError("ip_address is missing")

class OVS(Bridge):
    __shortname = 'ovs'
    def __init__(self, name=None, ip_address=None, cidr=24):
        super().__init__()
        self.name = name
        # self.ip_address = ip_address
        # self.cidr = cidr
    def create(self):
        return super().create() + "ovs-vsctl add-br {self.name}".format(self=self)
        #return "ovs-vsctl add-br {name} && ip link set dev {name} up && ip address add {ip_address}/{cidr} dev {name}".format(self=self)
    def destroy(self):
        return super().destroy() + "ovs-vsctl del-br {self.name}".format(self=self)


class Link:
    @staticmethod
    def declare(e1, e2, *args, **kwargs):
        if e1.__class__ is OVS and e2.__class__ is OVS:
            if 'type' not in kwargs:
                kwargs['type'] = 'patch'
            if kwargs['type'] == 'veth':
                return Link_OVS_OVS_veth(e1, e2, *args, **kwargs)
            elif kwargs['type'] == 'patch':
                return Link_OVS_OVS_patch(e1, e2, *args, **kwargs)
            else:
                raise ConfigurationError('unrecognized type: {}'.format(kwargs['type']))
        if (e1.__class__ is OVS and e2.__class__ is Netns) or (e1.__class__ is Netns and e2.__class__ is OVS):
            #make sure e1 is the OVS
            if e1.__class__ is Netns and e2.__class__ is OVS:
                e2, e1 = e1, e2
            if 'type' not in kwargs:
                kwargs['type'] = 'port'
            if kwargs['type'] == 'veth':
                return Link_OVS_Netns_veth(e1, e2, *args, **kwargs)
            elif kwargs['type'] == 'port':
                return Link_OVS_Netns_port(e1, e2, *args, **kwargs)
            else:
                raise ConfigurationError('unrecognized type: {}'.format(kwargs['type']))

    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2
        e1.links.append(self)
        e2.links.append(self)
    @add_comment('creating')
    def create(self):
        return ""
    @add_comment('destroying')
    def destroy(self):
        return ""
    @property
    def description(self):
        return "link between {} and {} of type {}".format(self.e1.name, self.e2.name, self.__class__.__name__)

    def __str__(self):
        return self.description
    def __repr__(self):
        return self.__str__()

    # ensure no double links are configured (they'll be skipped by Master)
    # links will be skipped EVEN IF they're of DIFFERENT TYPES
    def __key(self):
        return tuple( sorted([hash(self.e1), hash(self.e2)]) )
    def __hash__(self):
        return hash(self.__key())
    def __eq__(self, other):
        return self.__key() == other.__key()
    def __ne__(self, other):
        return not self.__eq__(other)

class Link_OVS_OVS_veth(Link):
    def __init__(self, e1, e2, name_1_to_2=None, name_2_to_1=None, **kwargs):
        super().__init__(e1, e2)
        self.name_1_to_2 = name_1_to_2
        self.name_2_to_1 = name_2_to_1
    def assign_attributes(self):
        # veth names are limited to 15 chars(!)
        if self.name_1_to_2 is None:
            self.name_1_to_2 = 'veth-ovs-{e1.name_id}-{e2.name_id}'.format(**self.__dict__)
        if self.name_2_to_1 is None:
            self.name_2_to_1 = 'veth-ovs-{e2.name_id}-{e1.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        #create the links
        cmds = "ip link add {name_1_to_2} type veth peer name {name_2_to_1} && \n"
        #configure one side
        cmds += "ovs-vsctl add-port {e1.name} {name_1_to_2} && "
        cmds += "ip link set {name_1_to_2} up"
        cmds += " && \n"
        #configure the other side
        cmds += "ovs-vsctl add-port {e2.name} {name_2_to_1} && "
        cmds += "ip link set {name_2_to_1} up"
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        self.assign_attributes()
        return super().destroy() + "ip link delete {name_1_to_2}".format(**self.__dict__)

class Link_OVS_OVS_patch(Link):
    def __init__(self, e1, e2, name_1_to_2=None, name_2_to_1=None, **kwargs):
        super().__init__(e1, e2)
        self.name_1_to_2 = name_1_to_2
        self.name_2_to_1 = name_2_to_1
    def assign_attributes(self):
        if self.name_1_to_2 is None:
            self.name_1_to_2 = 'patch-{e2.name}-{e1.name_id}'.format(**self.__dict__)
        if self.name_2_to_1 is None:
            self.name_2_to_1 = 'patch-{e1.name}-{e2.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        cmds = "ovs-vsctl add-port {e1.name} {name_1_to_2} -- set Interface {name_1_to_2} type=patch options:peer={name_2_to_1} && "
        cmds += "ovs-vsctl add-port {e2.name} {name_2_to_1} -- set Interface {name_2_to_1} type=patch options:peer={name_1_to_2}"
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        self.assign_attributes()
        return super().destroy() + "# destroyed by the bridge".format(**self.__dict__)


class Link_OVS_Netns_veth(Link):
    # e1 is the ovs, e2 is the netns
    def __init__(self, e1, e2, name_ovs_side=None, name_netns_side=None, ip_address=None, **kwargs):
        super().__init__(e1, e2)
        self.name_ovs_side = name_ovs_side
        self.name_netns_side = name_netns_side
        self.ip_address = ip_address
    def assign_attributes(self):
        if self.name_ovs_side is None:
            self.name_ovs_side = 'v-{}'.format(self.e2.name)
        if self.name_netns_side is None:
            self.name_netns_side = 'v-{}'.format(self.e1.name)
    def create(self):
        self.assign_attributes()
        #create the links
        cmds = "ip link add {name_ovs_side} type veth peer name {name_netns_side} && \n"
        #configure ovs side
        cmds += "ovs-vsctl add-port {e1.name} {name_ovs_side} && "
        cmds += "ip link set {name_ovs_side} up && \n"
        #configure namespace side
        cmds += "ip link set {name_netns_side} netns {e2.name} && "
        cmds += "ip netns exec {e2.name} ip link set dev {name_netns_side} up"
        if self.ip_address is not None:
            cmds += " && ip netns exec {e2.name} ip address add {ip_address}/24 dev {name_netns_side}"
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        self.assign_attributes()
        return super().destroy() + "ip link delete {name_ovs_side}".format(**self.__dict__)

class Link_OVS_Netns_port(Link):
    # e1 is the ovs, e2 is the netns
    def __init__(self, e1, e2, name_netns_side=None, ip_address=None, **kwargs):
        super().__init__(e1, e2)
        self.name_netns_side = name_netns_side
        self.ip_address = ip_address
    def assign_attributes(self):
        if self.name_netns_side is None:
            self.name_netns_side = 'p-{e1.name}-{e2.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        cmds = "ovs-vsctl add-port {e1.name} {name_netns_side} -- set Interface {name_netns_side} type=internal && "
        cmds += "ip link set {name_netns_side} netns {e2.name} && "
        cmds += "ip netns exec {e2.name} ip link set dev {name_netns_side} up"
        if self.ip_address is not None:
            cmds += " && ip netns exec {e2.name} ip address add {ip_address}/24 dev {name_netns_side}"
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        self.assign_attributes()
        return super().destroy() + "# destroyed by the bridge".format(**self.__dict__)

class Link_Netns_Netns_veth(Link):
    def __init__(self, e1, e2, name_1_to_2=None, name_2_to_1=None, **kwargs):
        super().__init__(e1, e2)
        self.name_1_to_2 = name_1_to_2
        self.name_2_to_1 = name_2_to_1
    def assign_attributes(self):
        # veth names are limited to 15 chars(!)
        if self.name_1_to_2 is None:
            self.name_1_to_2 = 'veth-ns-{e1.name_id}-{e2.name_id}'.format(**self.__dict__)
        if self.name_2_to_1 is None:
            self.name_2_to_1 = 'veth-ns-{e2.name_id}-{e1.name_id}'.format(**self.__dict__)
    def create(self):
        self.assign_attributes()
        #create the links
        cmds = "ip link add {name_1_to_2} type veth peer name {name_2_to_1} && \n"
        #configure one side
        cmds += "ip link set {name_1_to_2} netns {e1.name} && "
        cmds += "ip netns exec {e1.name} ip link set dev {name_1_to_2} up"
        cmds += " && \n"
        #configure the other side
        cmds += "ip link set {name_2_to_1} netns {e2.name} && "
        cmds += "ip netns exec {e2.name} ip link set dev {name_2_to_1} up"
        return super().create() + cmds.format(**self.__dict__)
    def destroy(self):
        self.assign_attributes()
        return super().destroy() + "ip link delete {name_1_to_2}".format(**self.__dict__)


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
            self.find_unique_attribute(entity, 'name', '{entity.entity_name}{n}')
            # self.find_unique_attribute(entity, 'ip_address', '10.112.{n}.1', 255)

    @property
    def links(self):
        links = []
        for e in self.entities:
            links += e.links
        return set(links)

    def __get_commands(self, collection, fn):
        commands = []
        for obj in collection:
            commands.append(getattr(obj, fn)())
        return commands
    def setup(self):
        self.assign_attributes()
        return self.__get_commands(self.entities, 'create') + self.__get_commands(self.links, 'create')
    def cleanup(self):
        return self.__get_commands(self.entities, 'destroy') + self.__get_commands(self.links, 'destroy')

    def get_script(self):
        return "\n".join(['function opg_setup {'] + self.setup() + ['}', ''] + ['function opg_cleanup {'] + self.cleanup()  + ['sleep 1', '}', ''])
