import json
import subprocess
from ryu.app.wsgi import ControllerBase, route, WSGIApplication
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet.packet import Packet
from ryu.lib.packet.ethernet import ethernet
from ryu.lib.packet.arp import arp
from ryu.lib.packet.tcp import tcp
from ryu.lib.packet.ipv4 import ipv4
from ryu.lib.packet.ipv6 import ipv6
from ryu.lib.packet.vlan import vlan
from ryu.ofproto import ether
from webob import Response

from workshop_parent import WorkshopParent
from threading import Lock

mutex = Lock()

chains = [{}, {}]
port_num = [4, 4]
fws = [[], []]
nats = [[], []]

class SimpleSwitchController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(SimpleSwitchController, self).__init__(req, link, data, **config)
        self.simple_switch_app = data['instance']

    @route('simpleswitch', '/register_sfc', methods=['PUT'])
    def register(self, req, **kwargs):
        print('register')
        try:
            new_entry = req.json
        except ValueError:
            raise Response(status=400)

        chain_id = new_entry['chain_id']
        chains[chain_id - 1] = new_entry
        print(chains)
        subprocess.run(
            './setup_topology.sh ' + str(chain_id) + ' ' + new_entry['SRC']['IP'] + ' ' +
            new_entry['SRC']['MAC'] + ' ' + new_entry['DST']['IP'] + ' ' +
            new_entry['DST']['MAC'], capture_output=True, check=True, shell=True)

        self.simple_switch_app.IP_to_MAC[new_entry['SRC']['IP']] = new_entry['SRC']['MAC']
        self.simple_switch_app.IP_to_MAC[new_entry['DST']['IP']] = new_entry['DST']['MAC']

        return Response(status=200)

    @route('simpleswitch', '/launch_sfc', methods=['PUT'])
    def launch(self, req, **kwargs):
        print('launch')
        mutex.acquire()
        try:
            input = req.json
        except ValueError:
            raise Response(status=400)
        chain = chains[input['chain_id'] - 1]
        if 'fw' in input:
            for fw in input['fw']:
                subprocess.run(
                    '.' + chain['fw']['init_script'] + ' ' +
                    str(len(fws[0]) + len(fws[1])) + ' ' +
                    fw['mac']['eth0'] + ' ' + fw['mac']['eth1'] + ' ' +
                    fw['args'][0] + ' ' + fw['args'][1], capture_output=True, check=True,
                    shell=True)
                fws[input['chain_id'] - 1].append({
                    "IN_MAC": fw['mac']['eth0'],
                    "OUT_MAC": fw['mac']['eth1'],
                    "IN_PORT": port_num[0],
                    "OUT_PORT": port_num[0] + 1
                })
                port_num[0] += 2
        if 'nat' in input:
            for nat in input['nat']:
                subprocess.run(
                    '.' + chain['nat']['init_script'] + ' ' +
                    str(len(nats[0]) + len(nats[1])) + ' ' +
                    nat['ip']['eth0'] + ' ' +
                    nat['ip']['eth1'] + ' ' + nat['mac']['eth0'] + ' ' +
                    nat['mac']['eth1'], capture_output=True, check=True, shell=True)
                nats[input['chain_id'] - 1].append({
                    "IN_MAC": nat['mac']['eth0'],
                    "OUT_MAC": nat['mac']['eth1'],
                    "IN_PORT": port_num[1],
                    "OUT_PORT": port_num[1] + 1
                })
                port_num[1] += 2
        mutex.release()
        return Response(status=200)


class Workshop4(WorkshopParent):
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(Workshop4, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(SimpleSwitchController,
                      {'instance': self})

        print("Initializing RYU controller app for Workshop 4")
        # self.flowToID = {}
        # self.IDToTransition = {}
        self.IP_to_MAC = {}
        self.flow_to_transition = {}
        self.indices = [[0, 0], [0, 0]]

    # Function to handle packets belonging to ARP protocol
    def handle_arp(self, datapath, packet, ether_frame, in_port):
        print('handle arp')
        arp_packet = packet.get_protocol(arp)

        if arp_packet.opcode == 1:  # Send an ARP Response for the incoming Request
            # Determine the MAC Address for IP Address being looked up
            # Determine the out port to send the ARP Response 

            ''' Your code here '''
            dst_mac = None
            if arp_packet.dst_ip in self.IP_to_MAC:
                dst_mac = self.IP_to_MAC[arp_packet.dst_ip]
            else:
                raise Exception("Cannot find IP", arp_packet.src_ip, arp_packet.dst_ip)
            # Call helper function to create and send ARP Response
            self.send_arp_reply(datapath, dst_mac, arp_packet.dst_ip, ether_frame.src,
                                arp_packet.src_ip, in_port)

        else:
            # We don't expect to receive ARP replies, so do nothing
            pass

    # Function to handle non-ARP packets
    def handle_packet(self, msg):
        ''' Your code here '''
        print('handle_packet')
        mutex.acquire()
        # global packetID
        dpid = msg.datapath.id
        pkt = Packet(msg.data)
        eth = pkt.get_protocol(ethernet)
        parser = msg.datapath.ofproto_parser

        in_port = msg.match['in_port']

        ip_pkt_6 = pkt.get_protocol(ipv6)
        ip_pkt = pkt.get_protocol(ipv4)
        tcp_pkt = pkt.get_protocol(tcp)
        src_port = None
        dst_port = None
        if tcp_pkt:
            src_port = tcp_pkt.src_port
            dst_port = tcp_pkt.dst_port
        ip_proto = None
        src_ip = None
        dst_ip = None
        if isinstance(ip_pkt_6, ipv6):
            ip_proto = ip_pkt_6.proto
            src_ip = ip_pkt_6.src
            dst_ip = ip_pkt_6.dst
        else:
            ip_proto = ip_pkt.proto
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst

        chainID = None
        if src_ip == chains[0]['SRC']['IP'] or src_ip == chains[0]['DST']['IP'] or dst_ip == chains[0]['DST'][
            'IP'] or dst_ip == chains[0]['SRC']['IP']:
            chainID = 0
        else:
            chainID = 1

        # print('chainID: ', chainID)

        chain = chains[chainID]

        sport, dport = src_port, dst_port
        if src_ip == chains[0]['DST']['IP'] or src_ip == chains[1]['DST']['IP'] or dst_ip == chains[1]['SRC'][
            'IP'] or dst_ip == chains[0]['SRC']['IP']:
            sport, dport = dst_port, src_port

        info = [ip_proto, chainID, sport, dport]
        info_strings = ','.join(map(str, info))

        out_port = None
        eth_dst = None
        actions = []

        self.IP_to_MAC[src_ip] = eth.src

        if info_strings in self.flow_to_transition:
            print('seen')
            out_port, eth_dst = self.flow_to_transition[info_strings][dpid - 1][in_port]

        else:
            fwIndex = None
            if 'fw' in chain['NF_CHAIN']:
                self.indices[chainID][0] = (self.indices[chainID][0] + 1) % len(
                    fws[chainID])
                fwIndex = self.indices[chainID][0]

            natIndex = None
            if 'nat' in chain['NF_CHAIN']:
                self.indices[chainID][1] = (self.indices[chainID][1] + 1) % len(
                    nats[chainID])
                natIndex = self.indices[chainID][1]

            transition = [{}, {}]

            if 'fw' in chain['NF_CHAIN']:
                # print('have fw')
                transition[0][chain['SRC']['PORT']] = [fws[chainID][fwIndex]['IN_PORT'],
                                                       fws[chainID][fwIndex]['IN_MAC']]
                transition[0][fws[chainID][fwIndex]['IN_PORT']] = [chain['SRC']['PORT'],
                                                                   chain['SRC']['MAC']]
                transition[0][fws[chainID][fwIndex]['OUT_PORT']] = [1,
                                                                    nats[chainID][natIndex]['IN_MAC'] if 'nat' in chain[
                                                                        'NF_CHAIN'] else
                                                                    chain['DST']['MAC']]
                transition[0][1] = [fws[chainID][fwIndex]['OUT_PORT'],
                                    fws[chainID][fwIndex]['OUT_MAC']]

            else:
                transition[0][chain['SRC']['PORT']] = [1,
                                                       nats[chainID][natIndex]['IN_MAC']]
                transition[0][1] = [chain['SRC']['PORT'], chain['SRC']['MAC']]

            if 'nat' in chain['NF_CHAIN']:
                # print('have nat')
                transition[1][1] = [nats[chainID][natIndex]['IN_PORT'],
                                    nats[chainID][natIndex]['IN_MAC']]
                transition[1][nats[chainID][natIndex]['IN_PORT']] = [1, fws[chainID][
                    fwIndex]['OUT_MAC'] if 'fw' in chain['NF_CHAIN'] else chain['SRC'][
                    'MAC']]
                transition[1][nats[chainID][natIndex]['OUT_PORT']] = [chain['DST'][
                                                                          'PORT'],
                                                                      chain['DST'][
                                                                          'MAC']]
                transition[1][chain['DST']['PORT']] = [
                    nats[chainID][natIndex]['OUT_PORT'],
                    nats[chainID][natIndex]['OUT_MAC']]

            else:
                transition[1][1] = [chain['DST']['PORT'], chain['DST']['MAC']]
                transition[1][chain['DST']['PORT']] = [1,
                                                       fws[chainID][fwIndex]['OUT_PORT']]

            self.flow_to_transition[info_strings] = transition

            out_port, eth_dst = transition[dpid - 1][in_port]

        actions.append(parser.OFPActionSetField(eth_dst=eth_dst))
        actions.append(parser.OFPActionOutput(out_port))
        match = None
        if tcp_pkt:

            if isinstance(ip_pkt_6, ipv6):
                match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src,
                                        eth_type=eth.ethertype, ip_proto=ip_proto,
                                        ipv6_src=src_ip, ipv6_dst=dst_ip,
                                        tcp_src=src_port,
                                        tcp_dst=dst_port)
            else:
                match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src,
                                        eth_type=eth.ethertype, ip_proto=ip_proto,
                                        ipv4_src=src_ip, ipv4_dst=dst_ip,
                                        tcp_src=src_port,
                                        tcp_dst=dst_port)

        else:
            if isinstance(ip_pkt_6, ipv6):
                match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src,
                                        eth_type=eth.ethertype, ip_proto=ip_proto,
                                        ipv6_src=src_ip, ipv6_dst=dst_ip)
            else:
                match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src,
                                        eth_type=eth.ethertype, ip_proto=ip_proto,
                                        ipv4_src=src_ip, ipv4_dst=dst_ip)

        print(match, actions)
        self.add_flow_init(msg.datapath, 1, match, actions)

        out = msg.datapath.ofproto_parser.OFPPacketOut(
            datapath=msg.datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data)
        msg.datapath.send_msg(out)
        mutex.release()
