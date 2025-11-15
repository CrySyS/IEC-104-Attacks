FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update -y && apt upgrade -y

RUN apt-get install -y iptables tcpdump dsniff iproute2 python3.8 python3-pip tmux dnsutils tshark wireshark
RUN apt-get install -y build-essential python-dev libnetfilter-queue-dev
RUN pip3 install scapy mitmproxy python-iptables scipy requests NetfilterQueue kamene typer colorama pyshark scapy
RUN apt-get install -y openjdk-8-jdk

COPY client/j60870 /home/iec
WORKDIR /home/iec
RUN ./gradlew build

COPY attacks /home/attacker
WORKDIR /home/attacker

ENV LANG=C.UTF-8
CMD tail -f /dev/random
