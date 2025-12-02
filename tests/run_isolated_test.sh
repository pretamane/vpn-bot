#!/bin/bash
set -e

NS="vpn_test_ns"
VETH_HOST="veth_host"
VETH_NS="veth_ns"
IP_HOST="10.200.1.1/24"
IP_NS="10.200.1.2/24"
GW_NS="10.200.1.1"
INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)

echo "Creating network namespace: $NS"
sudo ip netns add $NS

echo "Creating veth pair"
sudo ip link add $VETH_HOST type veth peer name $VETH_NS
sudo ip link set $VETH_NS netns $NS

echo "Configuring interfaces"
sudo ip addr add $IP_HOST dev $VETH_HOST
sudo ip link set $VETH_HOST up

sudo ip netns exec $NS ip addr add $IP_NS dev $VETH_NS
sudo ip netns exec $NS ip link set $VETH_NS up
sudo ip netns exec $NS ip link set lo up
sudo ip netns exec $NS ip route add default via $GW_NS

echo "Enabling IP forwarding"
sudo sysctl -w net.ipv4.ip_forward=1 > /dev/null

echo "Setting up NAT on interface: $INTERFACE"
sudo iptables -t nat -A POSTROUTING -s 10.200.1.0/24 -o $INTERFACE -j MASQUERADE
sudo iptables -A FORWARD -i $INTERFACE -o $VETH_HOST -j ACCEPT
sudo iptables -A FORWARD -o $INTERFACE -i $VETH_HOST -j ACCEPT

echo "Running verification script inside namespace..."
# We need to pass the current directory to the namespace
CWD=$(pwd)
# We need to make sure python and dependencies are available. 
# Assuming system python is fine.
sudo ip netns exec $NS python3 "$CWD/tests/verify_protocols.py" || echo "Verification failed inside NS"

echo "Cleaning up..."
sudo ip netns delete $NS
sudo ip link delete $VETH_HOST 2>/dev/null || true
# Remove iptables rules (simple cleanup, might delete too much if concurrent, but safe for dev env)
sudo iptables -t nat -D POSTROUTING -s 10.200.1.0/24 -o $INTERFACE -j MASQUERADE 2>/dev/null || true
sudo iptables -D FORWARD -i $INTERFACE -o $VETH_HOST -j ACCEPT 2>/dev/null || true
sudo iptables -D FORWARD -o $INTERFACE -i $VETH_HOST -j ACCEPT 2>/dev/null || true

echo "Done."
