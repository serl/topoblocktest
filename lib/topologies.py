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
        nss.append(Netns().add_to(m))

    #and link them
    subnet_number = 0
    for ns1, ns2 in zip(nss, nss[1:]):
        ip_address_base = '{}.{}.'.format(base_net, subnet_number)
        if not use_ovs:
            Link.declare((ns1, ip_address_base+'1'), (ns2, ip_address_base+'2'), disable_offloading=disable_offloading)
        else:
            ovs = OVS().add_to(m)
            Link.declare((ns1, ip_address_base+'1'), ovs, link_type=ovs_ns_links, disable_offloading=disable_offloading)
            Link.declare((ns2, ip_address_base+'2'), ovs, link_type=ovs_ns_links, disable_offloading=disable_offloading)

        subnet_number += 1

    #do the routing for intermediate namespaces
    for i, ns in enumerate(nss):
        left = None
        right = None
        for l in ns.links:
             if (l.e1.entity == ns):
                 right = l.e2
             elif (l.e2.entity == ns):
                 left = l.e1

        for subnet in range(0, n_ns):
            if subnet in range(i-1, i+2):
                continue #directly linked
            elif subnet < i:
                endpoint = left
            elif subnet > i:
                endpoint = right
            ns.add_route('{}.{}.0/24'.format(base_net, subnet), endpoint)

    return m
