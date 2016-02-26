from lib.topology import Master, OVS, Netns, Link

m = Master()

ovs1 = OVS().add_to(m)

ovs2 = OVS().add_to(m)

#Link.declare(ovs1, ovs2, type='veth')
Link.declare(ovs1, ovs2, type='patch')

ns1 = Netns('test-ns1').add_to(m)
Link.declare(ns1, ovs1, type='port', ip_address='10.113.1.1')

ns2 = Netns('test-ns2').add_to(m)
Link.declare(ns2, ovs2, type='veth', ip_address='10.113.1.2')

print(m.get_script())
