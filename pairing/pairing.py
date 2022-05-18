from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
import numpy
import random
import string
from datetime import datetime
from alive_progress import alive_bar

STATION_COUNT = 100
CHANGE_RATE_MIN = 0.8
CHANGE_RATE_MAX = 1.2
VALUE_COUNT_MIN = 20
VALUE_COUNT_MAX = 20
MAX_VALUE = 1000
MIN_VALUE = -1000
ITERATION_COUNT = 10000
NOISE_MIN = 0.9
NOISE_MAX = 1.1
start = datetime.now()


def generate_dict():
    global STATION_COUNT
    ids = set()

    while len(ids) != STATION_COUNT:
        ids.add(get_random_string(8))

    ioas = set()
    while len(ioas) != STATION_COUNT:
        ioas.add(random.randint(0, 2000))
    return dict(zip(ids, ioas))


def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def match_pairs(ioa_data, station_data):
    a = numpy.array(ioa_data)
    b = numpy.array(station_data)
    out = cdist(a, b, 'sqeuclidean')
    row_ind, col_ind = linear_sum_assignment(out)
    res = {}
    for k in range(0, len(station_ids)):
        res[station_ids[col_ind[k]]] = ioas[row_ind[k]]
    return res


def generate_data(pairs):
    global VALUE_COUNT_MIN
    global VALUE_COUNT_MAX
    global CHANGE_RATE_MIN
    global CHANGE_RATE_MAX
    global MIN_VALUE
    global MAX_VALUE

    ioa_values = {}
    station_values = {}

    value_count = random.randint(VALUE_COUNT_MIN, VALUE_COUNT_MAX)
    for j in range(0, value_count):
        for sid, ioa in pairs.items():
            if sid in station_values.keys():
                station_values[sid].append(station_values[sid][j - 1] * random.uniform(CHANGE_RATE_MIN, CHANGE_RATE_MAX))
            else:
                station_values[sid] = [random.randint(MIN_VALUE, MAX_VALUE)]

            if ioa in ioa_values.keys():
                ioa_values[ioa].append(station_values[sid][j] * random.uniform(NOISE_MIN, NOISE_MAX))
            else:
                ioa_values[ioa] = [station_values[sid][j] * random.uniform(NOISE_MIN, NOISE_MAX)]

    return ioa_values, station_values

CORRECT = 0
CASES = 0
STATION_IOA_PAIRS = generate_dict()


with alive_bar(ITERATION_COUNT) as bar:
    for i in range(0, ITERATION_COUNT):
        bar()
        station_ids = list(STATION_IOA_PAIRS.keys())
        ioas = list(STATION_IOA_PAIRS.values())
        random.shuffle(station_ids)
        random.shuffle(ioas)
        pairs = dict(zip(station_ids, ioas))
        ioa_values, station_values = generate_data(pairs)
        station_data = []
        ioa_data = []
        for sid in station_values.keys():
            station_data.append(station_values[sid])

        for ioa in pairs.values():
            ioa_data.append(ioa_values[ioa])

        res = match_pairs(ioa_data, station_data)
        CASES += 1
        if res == pairs:
            CORRECT += 1

print(f"Correct: {CORRECT}")
print(f"Overall: {CASES}")
print(f"Ratio: {(CORRECT/CASES)*100}%")
print(f"Runtime: {datetime.now() - start}")
