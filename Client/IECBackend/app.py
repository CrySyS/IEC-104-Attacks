import time, threading
from flask import Flask, render_template, jsonify, request
from station import Station

app = Flask(__name__)

station_ioa_pairs = {
    "S": 0,
    "A": 1000,
    "B": 1001,
    "C": 1002,
    "E": 1003,
    "F": 1004,
    "G": 1005,
    "H": 1006,
    "I": 1007,
    "J": 1008,
    "K": 1009,
    "L": 1010,
    "D": 100,
}

S = Station("S", 1)
A = Station("A", 1)
B = Station("B", 1)
C = Station("C", 1)
E = Station("E", 1)
F = Station("F", 1)
G = Station("G", 1)
H = Station("H", 1)
I = Station("I", 1)
J = Station("J", 1)
K = Station("K", 1)
L = Station("L", 1)
D = Station("D", 1)

S.connected_to = [A, B]
A.connected_to = [C]
B.connected_to = [E, F]
C.connected_to = [G, H]
E.connected_to = [H]
F.connected_to = [I]
G.connected_to = [J]
H.connected_to = [I]
I.connected_to = [K]
J.connected_to = [L]
K.connected_to = [L]
L.connected_to = [D]

system = [S, A, B, C, E, F, G, H, I, J, K, L, D]

values = {"S": 0, "A": 0, "B": 0, "C": 0, "E": 0, "F": 0, "G": 0, "H": 0, "I": 0, "J": 0, "K": 0,  "L": 0, "D": 0}
public_values = {}

def set_public_values():
    global values
    global public_values

    threading.Timer(5.0, set_public_values).start()
    public_values = values.copy()


def step():
    global s_val
    global values

    threading.Timer(5.0, step).start()
    for element in system:
        element.step()


@app.route('/')
def hello_world():
    global public_values
    return render_template("index.html.jinja2", data=public_values)


@app.route('/pairs')
def get_pairs():
    return jsonify(station_ioa_pairs)


@app.route('/update', methods=['POST'])
def update_text():
    try:
        print(request.json)
        global values
        data = request.json
        print(data)
        for key in data.keys():
            station_id = list(station_ioa_pairs.keys())[list(station_ioa_pairs.values()).index(int(key))]
            print(station_id)
            print(data[key])
            if station_id in values.keys():
                values[station_id] = data[key]
        return jsonify({"success": True})
    except:
        return jsonify({"success": True})


if __name__ == '__main__':
    step()
    set_public_values()
    app.run(host='0.0.0.0')
