if [ -z "${BRIDGE_SETUP}" ]; then
  sudo ovs-vsctl add-br ovs-br1
  sudo ovs-vsctl add-br ovs-br2
  sudo ovs-vsctl set-controller ovs-br1 tcp:127.0.0.1:6633
  sudo ovs-vsctl set-fail-mode ovs-br1 secure
  sudo ovs-vsctl set-controller ovs-br2 tcp:127.0.0.1:6633
  sudo ovs-vsctl set-fail-mode ovs-br1 secure
  sudo ovs-vsctl set bridge ovs-br1 other-config:datapath-id=0000000000000001
  sudo ovs-vsctl set bridge ovs-br2 other-config:datapath-id=0000000000000002
  ovs-vsctl \
  -- add-port ovs-br1 patch0 \
  -- set interface patch0 type=patch options:peer=patch1 \
  -- add-port ovs-br2 patch1 \
  -- set interface patch1 type=patch options:peer=patch0
  export BRIDGE_SETUP="done"
fi

docker run -d --privileged --name=src$1 --net=none endpoint:latest tail -f /dev/null
docker run -d --privileged --name=dst$1 --net=none endpoint:latest tail -f /dev/null

sudo ovs-docker add-port ovs-br1 eth0 src$1 --ipaddress=$2/24 --macaddress=$3
sudo ovs-docker add-port ovs-br2 eth0 dst$1 --ipaddress=$4/24 --macaddress=$5

docker exec src$1 ip route add 145.12.131.0/24 dev eth0
docker exec dst$1 ip route add 192.168.1.0/24 dev eth0