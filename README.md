# IEC-104 Attacks

This repository contains attacks against the IEC-104 protocol, which is often used in European electrical engineering and power system automation applications. We created Docker containers to help test the attacks, which have all the necessary tools prepared. This `README.md` guides you on how to reproduce each attack scenario for yourself. The theoretical background of the attacks is explained in our paper` Novel specific attack methods against the IEC 104 protocol`, which is yet to be published.

## Unauthorized access

1. Start the containers using `docker-compose build && docker-compose up`
2. Open 3 terminal and issue the following commands
   1. `docker exec -ti iecdocker-client-1 /bin/bash`
   2. `docker exec -ti iecdocker-server-1 /bin/bash`
   3. `docker exec -ti iecdocker-attacker-1 /bin/bash`
3. In the server container start the IEC-104 server using the `./run-scripts/j60870-sample-server` command.
4. In the client container start the IEC-104 client using the `./run-scripts/j60870-console-client -h server` command.
5. In your browser open the `http://localhost:5001` and the `http://localhost:5002` URLs.
6. In the attacker container use the `./a1_unauthenticated.sh` command to start the attack
   1. In the menu send a point-command using `p`.
   2. Set the `IOA` to `1000` and the value to `42`.
7. Refresh the pages in your browser. As you can see the attacker and the operator are in a race for controlling the station. They will continuously overwrite each-other's commands.

## IEC starvation

1. Start the containers using `docker-compose build && docker-compose up`
2. Open 3 terminal and issue the following commands
   1. `docker exec -ti iecdocker-client-1 /bin/bash`
   2. `docker exec -ti iecdocker-server-1 /bin/bash`
   3. `docker exec -ti iecdocker-attacker-1 /bin/bash`
3. In the server container start the IEC-104 server using the `./run-scripts/j60870-sample-server` command.
4. In the attacker container use the `python3 a2_starvation.py <server ip>` command. Use the `nslookup server` command to get the IP address of the server.
5. In the client container start the IEC-104 client using the `./run-scripts/j60870-console-client -h server` command.
6. All the available connections are exhausted, therefore the operator can not connect to the server.

## TCP Poisoning

1. Start the containers using `docker-compose build && docker-compose up`
2. Open 3 terminal and issue the following commands
   1. `docker exec -ti iecdocker-client-1 /bin/bash`
   2. `docker exec -ti iecdocker-server-1 /bin/bash`
   3. `docker exec -ti iecdocker-attacker-1 /bin/bash`
3. In the server container start the IEC-104 server using the `./run-scripts/j60870-sample-server` command.
4. In the client container start the IEC-104 client using the `./run-scripts/j60870-console-client -h server` command.
5. In the attacker container use the `./mitm && python3 a3_tcp_poison.py <client ip> <server ip>` command. Use the `nslookup server` command to get the IP address of the server and the `nslookup client` to get the IP address of the client.
6. After the application starts write `stop` to inject an RST packet and terminate the connection of the participants.

## IEC APCI Poisoning

1. Start the containers using `docker-compose build && docker-compose up`
2. Open 3 terminal and issue the following commands
   1. `docker exec -ti iecdocker-client-1 /bin/bash`
   2. `docker exec -ti iecdocker-server-1 /bin/bash`
   3. `docker exec -ti iecdocker-attacker-1 /bin/bash`
3. In the server container start the IEC-104 server using the `./run-scripts/j60870-sample-server` command.
4. In the client container start the IEC-104 client using the `./run-scripts/j60870-console-client -h server` command.
5. In the attacker container use the `./mitm && python3 a4_iec_poison.py <client ip> <server ip>` command. Use the `nslookup server` command to get the IP address of the server and the `nslookup client` to get the IP address of the client.
6. After the application starts write `stop` to modify the sequence number of the next IEC packet and terminate the connection of the participants.


## Packet injection

1. Start the containers using `docker-compose build && docker-compose up`
2. Open 3 terminal and issue the following commands
   1. `docker exec -ti iecdocker-client-1 /bin/bash`
   2. `docker exec -ti iecdocker-server-1 /bin/bash`
   3. `docker exec -ti iecdocker-attacker-1 /bin/bash`
3. In the server container start the IEC-104 server using the `./run-scripts/j60870-sample-server` command.
4. In the client container start the IEC-104 client using the `./run-scripts/j60870-console-client -h server` command.
5. In the attacker container use the `./mitm && python3 a5_injection.py <client ip> <server ip>` command. Use the `nslookup server` command to get the IP address of the server and the `nslookup client` to get the IP address of the client.
6. After the application starts write `1000:12` command to inject a new packet to to set the value of `IOA 1000` to `12`.
7. In your browser open the `http://localhost:5001` and the `http://localhost:5002` URLs.
8. You can see that the server and the client see different values on the station.
