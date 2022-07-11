# project 2

## Data Structure used to maintain *cluster state*

- `chains`

  format: `[{}, {}]`

  used to record information of hosts and switches for each chain in the `register_sfc` step.

- `port_num`

  format: `[4, 4]`

  used to allocate correct port to each network function. Increased by 1 when a new port is needed. Start from 4 since the four hosts would already took 4 ports away.

- `fws` / `nats`

  format: `[["IN_MAC", "OUT_MAC", "IN_PORT", "OUT_PORT"], []]`

  used to record mac and port of network functions in the `launch_sfc` step, just like the previous workshop.

- `self.IP_to_MAC`

  format: `{IP: MAC}`

  used to record IP to MAC mapping of hosts and network functions.

- `self.flow_to_transition`

  format: `{5-tuple: [{in-port: [out_port, eth_dst]}, {}]}`

  used to record seen flow to achieve both flow affinity and connection affinity. As you could see on the format, there are three layers of the mapping:

  1. The outside key is the so-called “5-tuple”, and actually we use the group of protocol, src/dst port and chain id (which is the same with src/dst ip but avoid the effect of NAT).
  2. The middle data structure is a list that has two parts and corresponds to two switches(dpid).
  3. And the inner part is another dictionary, which use `in_port` as the key, to show the certain host or network function this flow comes from.

- `self.indices`

  format: `[[0, 0], [0, 0]]`

  used to record the last index of certain network function of the certain chain is used

## Technique used to maintain connection affinity

1. For the first time we see a flow coming from src host, we would set up all the forwarding needed on both sides and between each possible pair in the path. So the reverse flow could directly use the previous setup.
2. Since our NAT would only change IP but not port, we could use chain id instead of src/dst ip in 5-tuple for the searching. And we could have at least one “real” src or dst ip to get the chain id.