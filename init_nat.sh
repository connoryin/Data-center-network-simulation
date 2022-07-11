docker run -d --privileged --name=nat$1 --net=none nf:latest tail -f /dev/null
sudo ovs-docker add-port ovs-br2 eth0 nat$1 --ipaddress=$2/24 --macaddress=$4
sudo ovs-docker add-port ovs-br2 eth1 nat$1 --ipaddress=$3/24 --macaddress=$5

docker exec nat$1 sysctl net.ipv4.ip_forward=1

docker exec nat$1 iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE
docker exec nat$1 iptables -A FORWARD -i eth0 -o eth1 -m state --state ESTABLISHED,RELATED -j ACCEPT
docker exec nat$1 iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT