from .topology import Master, OVS, Netns, Link

def ovs_chain(n_ovs, ovs_ovs_links, ovs_ns_links):
    m = Master()

    ns1 = Netns('x-ns1').add_to(m)
    ns2 = Netns('x-ns2').add_to(m)

    if n_ovs > 0:
        ovss = []
        for i_ovs in range(n_ovs):
            ovss.append(OVS().add_to(m))

        #and link them
        for ovs1, ovs2 in zip(ovss, ovss[1:]):
            Link.declare(ovs1, ovs2, link_type=ovs_ovs_links)

        Link.declare((ns1, '10.113.1.1'), ovss[0], link_type=ovs_ns_links)
        Link.declare((ns2, '10.113.1.2'), ovss[-1], link_type=ovs_ns_links)

    else:
        Link.declare((ns1, '10.113.1.1'), (ns2, '10.113.1.2'))

    return m
