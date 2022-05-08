FROM ubuntu:18.04

RUN apt update -y && apt upgrade -y

# Setup IEC Server
RUN apt-get install -y openjdk-8-jdk
COPY server/j60870 /home/iec
WORKDIR /home/iec
RUN ./gradlew build

# Copy Flask Server
RUN apt install -y python3-pip
RUN pip3 install flask
COPY IECBackend /app

WORKDIR /
RUN apt install -y supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf


WORKDIR /home/iec
CMD /usr/bin/supervisord