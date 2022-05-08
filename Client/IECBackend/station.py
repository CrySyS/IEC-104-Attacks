from typing import List, Any


class Station:
    name: str = None
    input: int = 0
    output: int = 0
    required: int = 0
    is_functioning: bool = False
    connected_to = []

    def __init__(self, name, required):
        self.name = name
        self.required = required

    def set_connected_to(self, connected_to):
        self.connected_to = connected_to

    def step(self):
        if self.required > self.input:
            self.is_functioning = False
            self.output = 0
            self.input = 0
            for station in self.connected_to:
                station.input += 0
        else:
            self.output = self.input - self.required
            self.input = 0
            self.is_functioning = True
            out_for_connections = self.output / len(self.connected_to)
            for station in self.connected_to:
                station.input += out_for_connections
