#!/bin/sh -e

echo 1 > /proc/sys/net/ipv4/ip_forward

SERVER=10.0.0.59
ROUTER=10.0.0.139
SSH_PORT=5522 # cannot conflict with router's ssh port, 22

echo 'Flushing all tables'
iptables -F
iptables -t nat -F
iptables -t mangle -F

echo 'Deleting non-default chains'
iptables -X


echo 'Forwarding 23=>22'
# SSH (23 to 22)
iptables -t nat -A PREROUTING -p tcp --dport $SSH_PORT -j DNAT --to-destination $SERVER:22
iptables -t nat -A POSTROUTING -p tcp -d $SERVER --dport 22 -j SNAT --to-source $ROUTER

echo 'Forwarding 80=>80'
# HTTP (80)
iptables -t nat -A PREROUTING -p tcp --dport 80 -j DNAT --to-destination $SERVER:80
iptables -t nat -A POSTROUTING -p tcp -d $SERVER --dport 80 -j SNAT --to-source $ROUTER

echo 'Forwarding 443=>443'
# HTTPS (443)
iptables -t nat -A PREROUTING -p tcp --dport 443 -j DNAT --to-destination $SERVER:443
iptables -t nat -A POSTROUTING -p tcp -d $SERVER --dport 443 -j SNAT --to-source $ROUTER

echo 'Forwarding UDP 443=>443'
# HTTPS (443) UDP
iptables -t nat -A PREROUTING -p udp --dport 443 -j DNAT --to-destination $SERVER:443
iptables -t nat -A POSTROUTING -p udp -d $SERVER --dport 443 -j SNAT --to-source $ROUTER

echo 'Forwarding TCP 5001=>5001'
# iperf (5001) TCP
iptables -t nat -A PREROUTING -p tcp --dport 5001 -j DNAT --to-destination $SERVER:5001
iptables -t nat -A POSTROUTING -p tcp -d $SERVER --dport 5001 -j SNAT --to-source $ROUTER

echo 'Forwarding UDP 5001=>5001'
# iperf (5001) UDP
iptables -t nat -A PREROUTING -p udp --dport 5001 -j DNAT --to-destination $SERVER:5001
iptables -t nat -A POSTROUTING -p udp -d $SERVER --dport 5001 -j SNAT --to-source $ROUTER


