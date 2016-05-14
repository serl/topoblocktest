from .topology import Master, OVS, Netns, Link
from collections import OrderedDict


def direct_veth(disable_offloading=False, **settings):
    m = Master()

    ns1 = Netns('x-ns1').add_to(m)
    ns2 = Netns('x-ns2').add_to(m)

    Link.declare((ns1, '10.112.1.1'), (ns2, '10.112.1.2'), disable_offloading=disable_offloading)

    return (m, ns1, ns2)
direct_veth.arguments = {}


def ovs_chain(disable_offloading=False, **settings):
    n_ovs = settings['chain_len']
    ovs_ovs_links = settings['ovs_ovs_links']
    ovs_ns_links = settings['ovs_ns_links']

    m = Master()

    ns1 = Netns('x-ns1').add_to(m)
    ns2 = Netns('x-ns2').add_to(m)

    if n_ovs < 1:
        raise ValueError("a chain needs at least one OvS")

    ovss = []
    for i_ovs in range(n_ovs):
        ovss.append(OVS().add_to(m))

    # and link them
    for ovs1, ovs2 in zip(ovss, ovss[1:]):
        Link.declare(ovs1, ovs2, link_type=ovs_ovs_links, disable_offloading=disable_offloading)

    Link.declare((ns1, '10.113.1.1'), ovss[0], link_type=ovs_ns_links, disable_offloading=disable_offloading)
    Link.declare((ns2, '10.113.1.2'), ovss[-1], link_type=ovs_ns_links, disable_offloading=disable_offloading)

    return (m, ns1, ns2)
ovs_chain.arguments = OrderedDict([
    ('chain_len', {'type': int, 'default': 1, 'help': 'number of switches to chain'}),
    ('ovs_ovs_links', {'default': 'patch', 'choices': ('patch', 'veth'), 'help': 'choses the link type between OvS switches'}),
    ('ovs_ns_links', {'default': 'port', 'choices': ('port', 'veth'), 'help': 'choses the link type between OvS and namespaces'}),
])


def unrouted_ns_chain(disable_offloading=False, **settings):
    n_ns = settings['chain_len']
    use_ovs = settings['use_ovs']
    ovs_ns_links = settings['ovs_ns_links']

    base_net = '10.114'
    m = Master()

    if n_ns < 2:
        raise ValueError("two namespaces at least")
    if n_ns > 255:
        raise ValueError("too many namespaces will break the ip addresses")

    nss = []
    for i_ns in range(n_ns):
        ns = Netns().add_to(m)
        ns.left = None
        ns.right = None
        nss.append(ns)

    # and link them
    subnet_number = 0
    for ns1, ns2 in zip(nss, nss[1:]):
        ip_address_base = '{}.{}.'.format(base_net, subnet_number)
        if not use_ovs:
            l = Link.declare((ns1, ip_address_base + '1'), (ns2, ip_address_base + '2'), disable_offloading=disable_offloading)
            ns1.right = l.e2
            ns2.left = l.e1
        else:
            ovs = OVS().add_to(m)
            l1 = Link.declare((ns1, ip_address_base + '1'), ovs, link_type=ovs_ns_links, disable_offloading=disable_offloading)
            ns2.left = l1.e2
            l2 = Link.declare((ns2, ip_address_base + '2'), ovs, link_type=ovs_ns_links, disable_offloading=disable_offloading)
            ns1.right = l2.e2

        subnet_number += 1

    return m, nss, base_net
unrouted_ns_chain.arguments = OrderedDict([
    ('chain_len', {'type': int, 'default': 2, 'help': 'number of namespaces to chain'}),
    ('use_ovs', {'default': False, 'action': 'store_true', 'help': 'use OvS switches to link the namespaces'}),
    ('ovs_ns_links', {'default': 'port', 'choices': ('port', 'veth'), 'help': 'choses the link type between OvS and namespaces, if OvS is enabled'}),
])


def ns_chain_add_routing(m, nss, base_net):
    # do the routing for intermediate namespaces
    for i, ns in enumerate(nss):
        for subnet_number in range(len(nss) - 1):
            if subnet_number in range(i - 1, i + 1):
                continue  # directly linked
            elif subnet_number < i:
                endpoint = ns.left
            elif subnet_number > i:
                endpoint = ns.right
            ns.add_route('{}.{}.0/24'.format(base_net, subnet_number), endpoint)


def ns_chain(disable_offloading=False, **settings):
    m, nss, base_net = unrouted_ns_chain(disable_offloading, **settings)
    ns_chain_add_routing(m, nss, base_net)
    return (m, nss[0], nss[-1])
ns_chain.arguments = unrouted_ns_chain.arguments


def ns_chain_iptables(disable_offloading=False, **settings):
    m, nss, base_net = unrouted_ns_chain(disable_offloading, **settings)
    ns_chain_add_routing(m, nss, base_net)

    if settings['iptables_type'] == 'stateful':
        max_int = 9223372036854775807  # see https://en.wikipedia.org/wiki/9223372036854775807 ...ok, it's that --connbytes takes 64bit integers.

        def generate_rule(x):
            return "iptables -w -A fakerules -m connbytes --connbytes {}:{} --connbytes-dir reply --connbytes-mode bytes -j ACCEPT".format(max_int - x - 1, max_int - x)
    else:
        def generate_rule(x):
            second_octet, remainder = divmod(x + 1, 255 * 255)
            third_octet, fourth_octet = divmod(remainder, 255)
            rule_ipaddr = '11.{}.{}.{}'.format(second_octet, third_octet, fourth_octet)
            return "iptables -w -A fakerules --source {} -j DROP".format(rule_ipaddr)

    for ns in nss:
        ns.add_configure_command("echo '  adding {iptables_rules_len} {iptables_type} iptables rules'".format(**settings))
        ns.add_configure_command("iptables -w -N fakerules")
        ns.add_configure_command("iptables -w -A INPUT -j fakerules")
        ns.add_configure_command("iptables -w -A FORWARD -j fakerules")
        ns.add_configure_command('last_ts="$(date +%s)"', False)
        for x in range(settings['iptables_rules_len']):
            if not ((x + 1) % 100) and x > 0:
                ns.add_configure_command('cur_ts="$(date +%s)"', False)
                ns.add_configure_command('echo "  inserted {} rules ($((cur_ts - last_ts))s from the last report)"'.format(x + 1), False)
                ns.add_configure_command('last_ts=$cur_ts', False)
            ns.add_configure_command(generate_rule(x))

    return (m, nss[0], nss[-1])
ns_chain_iptables.arguments = ns_chain.arguments.copy()
ns_chain_iptables.arguments['iptables_type'] = {'default': 'stateless', 'choices': ('stateless', 'stateful'), 'help': 'iptables rules type'}
ns_chain_iptables.arguments['iptables_rules_len'] = {'type': int, 'default': 0, 'help': 'number of useless iptables rules to inject'}


def ns_chain_qdisc(qdisc, tera, disable_offloading=False, **settings):
    m, nss, base_net = unrouted_ns_chain(disable_offloading, **settings)
    ns_chain_add_routing(m, nss, base_net)

    # 4294967295 is the maximum unsigned 32bit int (should fit on tc, according to docs)
    limit = 4294967295 if not tera else 10**12 / 8

    m.get_script()  # look, I'm hacking my code! (this will force autogeneration of endpoint names)
    for ns in nss:
        for endpoint in ns.endpoints:
            if qdisc == 'netem':
                packet_size = settings['packet_size']
                if packet_size == 'default':
                    packet_size = 2**16  # jumbo packets
                limit_burst = int(round(limit / (packet_size + 29), 0))  # to be fair with HTB, this should be the same (netem takes packets instead of bytes)
                limit_burst = limit_burst if limit_burst < 2147483647 else 2147483647
                # that is max signed 32bit int. not at all clear what netem does, this value seems to be well-swallowed
                ns.add_configure_command('tc qdisc replace dev {} root netem rate {}bps limit {} 2>&1'.format(endpoint.name, limit, limit_burst))
            elif qdisc == 'htb':
                ns.add_configure_command('tc qdisc replace dev {} root handle 1: htb default 1 2>&1'.format(endpoint.name))
                ns.add_configure_command('tc class replace dev {0} parent 1: classid 1:1 htb rate {1}bps burst {1}b 2>&1'.format(endpoint.name, limit))

    return (m, nss[0], nss[-1])


def ns_chain_qdisc_netem(disable_offloading=False, **settings):
    return ns_chain_qdisc('netem', False, disable_offloading, **settings)
ns_chain_qdisc_netem.arguments = ns_chain.arguments.copy()


def ns_chain_qdisc_htb(disable_offloading=False, **settings):
    return ns_chain_qdisc('htb', False, disable_offloading, **settings)
ns_chain_qdisc_htb.arguments = ns_chain.arguments.copy()


def ns_chain_qdisc_netem_tera(disable_offloading=False, **settings):
    return ns_chain_qdisc('netem', True, disable_offloading, **settings)
ns_chain_qdisc_netem.arguments = ns_chain.arguments.copy()


def ns_chain_qdisc_htb_tera(disable_offloading=False, **settings):
    return ns_chain_qdisc('htb', True, disable_offloading, **settings)
ns_chain_qdisc_htb.arguments = ns_chain.arguments.copy()
