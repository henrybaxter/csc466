#!/bin/bash -e

# NOTE
# class 5 is the 'treated' traffic
# class 10 is the 'default' traffic
# for both ingress and egress

JSON=`cat`

DELAY_TIME=$(echo "$JSON" | jq -r '.["delay-time"]')
DELAY_JITTER=$(echo $JSON | jq -r '.["delay-jitter"]')
DELAY_CORRELATION=$(echo $JSON | jq -r '.["delay-correlation"]')
DELAY_DISTRIBUTION=$(echo $JSON | jq -r '.["delay-distribution"]')
LOSS_P=$(echo $JSON | jq -r '.["loss-p"]')
LOSS_R=$(echo $JSON | jq -r '.["loss-r"]')
LOSS_1H=$(echo $JSON | jq -r '.["loss-h"]')
LOSS_1K=$(echo $JSON | jq -r '.["loss-k"]')
CORRUPT_PERCENT=$(echo $JSON | jq -r '.["corrupt-percent"]')
CORRUPT_CORRELATION=$(echo $JSON | jq -r '.["corrupt-correlation"]')
DUPLICATE_PERCENT=$(echo $JSON | jq -r '.["duplicate-percent"]')
DUPLICATE_CORRELATION=$(echo $JSON | jq -r '.["duplicate-correlation"]')


echo "Using:"
echo -e "\tDELAY_TIME=$DELAY_TIME"
echo -e "\tDELAY_JITTER=$DELAY_JITTER"
echo -e "\tDELAY_CORRELATION=$DELAY_CORRELATION"
echo -e "\tDELAY_DISTRIBUTION=$DELAY_DISTRIBUTION"
echo -e "\tLOSS_P=$LOSS_P"
echo -e "\tLOSS_R=$LOSS_R"
echo -e "\tLOSS_1H=$LOSS_1H"
echo -e "\tLOSS_1K=$LOSS_1K"
echo -e "\tCORRUPT_PERCENT=$CORRUPT_PERCENT"
echo -e "\tCORRUPT_CORRELATION=$CORRUPT_CORRELATION"
echo -e "\tDUPLICATE_PERCENT=$DUPLICATE_PERCENT"
echo -e "\tDUPLICATE_CORRELATION=$DUPLICATE_CORRELATION"

echo "Resetting iptables"
~/csc466/set_iptables.sh


# virtual interface module
echo 'Ensuring ifb module'
modprobe ifb numifbs=1

# cleanup
echo 'Cleaning up old qdisc information'
tc qdisc del dev eth0 handle ffff: ingress || true
tc qdisc del dev eth0 root || true
tc qdisc del dev ifb0 root || true
ip link set dev ifb0 down

echo 'Bringing up virtual ifb'
# virtual interface up
ip link set dev ifb0 up

echo 'Sending eth0 ingress through ifb0'
# ingress on eth0 is redirected through ifb0
tc qdisc add dev eth0 handle ffff: ingress
tc filter add dev eth0 parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0

echo 'Setting egress state on eth0'
# now egress on eth0 can be modified
tc qdisc add dev eth0 root handle 1: htb default 10
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit
tc class add dev eth0 parent 1:1 classid 1:10 htb rate 1000mbit
tc class add dev eth0 parent 1:1 classid 1:5 htb rate ${RATE_LIMIT}mbit ceil ${RATE_LIMIT}mbit
tc filter add dev eth0 protocol ip parent 1: prio 1 u32 match ip dport 23 0xfff flowid 1:5
tc filter add dev eth0 protocol ip parent 1: prio 1 u32 match ip dport 80 0xfff flowid 1:5
tc filter add dev eth0 protocol ip parent 1: prio 1 u32 match ip dport 443 0xfff flowid 1:5
tc filter add dev eth0 protocol ip parent 1: prio 1 u32 match ip dport 5001 0xfff flowid 1:5
tc qdisc add dev eth0 parent 1:5 handle 10: netem \
	limit 100000 \
	delay ${DELAY_TIME}ms ${DELAY_JITTER}ms ${DELAY_CORRELATION}% distribution ${DELAY_DISTRIBUTION} \
	loss gemodel ${LOSS_P} ${LOSS_R} ${LOSS_1H} ${LOSS_1K} \
	corrupt ${CORRUPT_PERCENT}% ${CORRUPT_CORRELATION}% \
	duplicate ${DUPLICATE_PERCENT}% ${DUPLICATE_CORRELATION}%

echo 'Setting egress state on ifb0 (eth0 ingress)'
# and ingress on eth0 (egress on ifb0) can be modified
tc qdisc add dev ifb0 root handle 1: htb default 10
tc class add dev ifb0 parent 1: classid 1:1 htb rate 1000mbit
tc class add dev ifb0 parent 1:1 classid 1:10 htb rate 1000mbit
tc class add dev ifb0 parent 1:1 classid 1:5 htb rate ${RATE_LIMIT}mbit ceil ${RATE_LIMIT}mbit
tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip sport 23 0xfff flowid 1:5
tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip sport 80 0xfff flowid 1:5
tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip sport 443 0xfff flowid 1:5
tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip sport 5001 0xfff flowid 1:5
tc qdisc add dev ifb0 parent 1:5 handle 10: netem  \
	limit 100000 \
	delay ${DELAY_TIME}ms ${DELAY_JITTER}ms ${DELAY_CORRELATION}% distribution ${DELAY_DISTRIBUTION} \
	loss gemodel ${LOSS_P} ${LOSS_R} ${LOSS_1H} ${LOSS_1K} \
	corrupt ${CORRUPT_PERCENT}% ${CORRUPT_CORRELATION}% \
	duplicate ${DUPLICATE_PERCENT}% ${DUPLICATE_CORRELATION}%

echo 'Finished'
