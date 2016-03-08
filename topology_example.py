from lib.topology import Master, OVS, Netns, Link

m = Master()

ovs1 = OVS().add_to(m)

ovs2 = OVS().add_to(m)

ovs3 = OVS().add_to(m)

ovs4 = OVS().add_to(m)

Link.declare(ovs1, ovs2, link_type='patch')
Link.declare(ovs2, ovs3, link_type='veth')
Link.declare(ovs3, ovs4, link_type='veth', disable_offloading=True)

ns1 = Netns().add_to(m)
Link.declare((ns1, '10.113.1.1'), ovs1, link_type='port')

ns2 = Netns('wonderful-ns2').add_to(m)
Link.declare((ns2,'10.113.1.2'), ovs3, link_type='veth')

ns3 = Netns('notoffld-ns3').add_to(m)
Link.declare((ns3,'10.113.1.3'), ovs4, link_type='port', disable_offloading=True)
Link.declare((ns3,'10.113.1.4'), ovs3, link_type='veth', disable_offloading=True)

Link.declare(ns1, ns2)
Link.declare(ns1, ns3, disable_offloading=True)

print(m.get_script())
