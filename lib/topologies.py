from .topology import Master, OVS, Netns, Link

def ovs_chain(n_ovs, ovs_ovs_links, ovs_ns_links, disable_offloading=False):
    m = Master()

    ns1 = Netns('x-ns1').add_to(m)
    ns2 = Netns('x-ns2').add_to(m)

    if n_ovs > 0:
        ovss = []
        for i_ovs in range(n_ovs):
            ovss.append(OVS().add_to(m))

        #and link them
        for ovs1, ovs2 in zip(ovss, ovss[1:]):
            Link.declare(ovs1, ovs2, link_type=ovs_ovs_links, disable_offloading=disable_offloading)

        Link.declare((ns1, '10.113.1.1'), ovss[0], link_type=ovs_ns_links, disable_offloading=disable_offloading)
        Link.declare((ns2, '10.113.1.2'), ovss[-1], link_type=ovs_ns_links, disable_offloading=disable_offloading)

    else:
        Link.declare((ns1, '10.113.1.1'), (ns2, '10.113.1.2'), disable_offloading=disable_offloading)

    return m

def ns_chain(n_ns=2, use_ovs=False, ovs_ns_links='port', disable_offloading=False):
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

    #and link them
    subnet_number = 0
    for ns1, ns2 in zip(nss, nss[1:]):
        ip_address_base = '{}.{}.'.format(base_net, subnet_number)
        if not use_ovs:
            l = Link.declare((ns1, ip_address_base+'1'), (ns2, ip_address_base+'2'), disable_offloading=disable_offloading)
            ns1.right = l.e2
            ns2.left = l.e1
        else:
            ovs = OVS().add_to(m)
            l1 = Link.declare((ns1, ip_address_base+'1'), ovs, link_type=ovs_ns_links, disable_offloading=disable_offloading)
            ns2.left = l1.e2
            l2 = Link.declare((ns2, ip_address_base+'2'), ovs, link_type=ovs_ns_links, disable_offloading=disable_offloading)
            ns1.right = l2.e2

        subnet_number += 1

    #do the routing for intermediate namespaces
    for i, ns in enumerate(nss):
        for subnet_number in range(n_ns-1):
            if subnet_number in range(i-1, i+1):
                continue #directly linked
            elif subnet_number < i:
                endpoint = ns.left
            elif subnet_number > i:
                endpoint = ns.right
            ns.add_route('{}.{}.0/24'.format(base_net, subnet_number), endpoint)

    return m
