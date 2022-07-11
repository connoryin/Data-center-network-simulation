unset BRIDGE_SETUP
docker rm src1 -f
docker rm src2 -f
docker rm dst1 -f
docker rm dst2 -f
docker rm fw0 -f
docker rm fw1 -f
docker rm nat0 -f
docker rm nat1 -f
docker rm nat2 -f
docker rm nat3 -f
sudo ovs-vsctl del-br ovs-br1
sudo ovs-vsctl del-br ovs-br2