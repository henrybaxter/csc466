## Methodology

### Basic Structure

Two instances of Chrome are launched, one using TCP/IP, the other using QUIC, on a local machine. They make requests via an EC2 instance `csc466-router` to a second EC2 instance `csc466-server`. These two instances are on the same private VLAN.

Variations in the pages requested and the network conditions are made, and page load time is calculated for multiple runs of each treatment.

Treatment load time data is aggregated, plotted, and analyzed.

### Chrome

