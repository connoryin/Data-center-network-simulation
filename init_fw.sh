docker run -d --privileged --name=fw$1 --net=none nf:latest tail -f /dev/null
sudo ovs-docker add-port ovs-br1 eth0 fw$1 --macaddress=$2
sudo ovs-docker add-port ovs-br1 eth1 fw$1 --macaddress=$3

docker exec fw$1 sysctl net.ipv4.ip_forward=1
docker exec fw$1 ip route add $4 dev eth0
docker exec fw$1 ip route add $5 dev eth1

docker exec fw$1 iptables -A FORWARD -i eth1 -p tcp --destination-port 22 -j DROP
docker exec fw$1 iptables -A FORWARD -i eth0 -p tcp --destination-port 22 -j DROP