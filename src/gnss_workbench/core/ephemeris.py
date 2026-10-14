"""GPS broadcast orbit and system clock, following the supplied model specification."""

import math
from typing import Any

import numpy as np

C = 299792458.0
MU = 3.986005e14
OMEGA_E = 7.2921151467e-5
RELATIVITY_F = -4.442807633e-10


def week_difference(t: float) -> float:
    return (t + 302400) % 604800 - 302400


def satellite_state(eph: dict[str, Any], tx: float) -> tuple[np.ndarray, float]:
    """Return transmit-frame ECEF and system clock seconds; TGD is NOT included."""
    a = eph["sqrt_a"] ** 2
    tk = week_difference(tx - eph["toe"])
    m = eph["m0"] + (math.sqrt(MU / a**3) + eph["delta_n"]) * tk
    e = float(eph["e"])
    eccentric = m
    for _ in range(20):
        step = (eccentric - e * math.sin(eccentric) - m) / (1 - e * math.cos(eccentric))
        eccentric -= step
        if abs(step) < 1e-14:
            break
    v = math.atan2(math.sqrt(1 - e * e) * math.sin(eccentric), math.cos(eccentric) - e)
    phi = v + eph["omega"]
    s2, c2 = math.sin(2 * phi), math.cos(2 * phi)
    u = phi + eph["cus"] * s2 + eph["cuc"] * c2
    r = a * (1 - e * math.cos(eccentric)) + eph["crs"] * s2 + eph["crc"] * c2
    inc = eph["i0"] + eph["idot"] * tk + eph["cis"] * s2 + eph["cic"] * c2
    omega = eph["omega0"] + (eph["omega_dot"] - OMEGA_E) * tk - OMEGA_E * eph["toe"]
    xp, yp = r * math.cos(u), r * math.sin(u)
    xyz = np.array(
        [
            xp * math.cos(omega) - yp * math.cos(inc) * math.sin(omega),
            xp * math.sin(omega) + yp * math.cos(inc) * math.cos(omega),
            yp * math.sin(inc),
        ]
    )
    tc = week_difference(tx - eph["toc"])
    clock = eph["af0"] + eph["af1"] * tc + eph["af2"] * tc**2
    clock += RELATIVITY_F * e * eph["sqrt_a"] * math.sin(eccentric)
    return xyz, float(clock)


def transmit_state(
    eph: dict[str, Any], receive_sow: float, pseudorange: float
) -> tuple[np.ndarray, float]:
    tx = receive_sow - pseudorange / C
    for _ in range(4):
        _, clock = satellite_state(eph, tx)
        tx = receive_sow - pseudorange / C - (clock - eph["tgd"])
    xyz, clock = satellite_state(eph, tx)
    return xyz, clock - eph["tgd"]


def rotate_to_receive(xyz: np.ndarray, tau: float) -> np.ndarray:
    w = OMEGA_E * tau
    c, s = math.cos(w), math.sin(w)
    return np.array([c * xyz[0] + s * xyz[1], -s * xyz[0] + c * xyz[1], xyz[2]])
