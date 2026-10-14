"""WGS84 ECEF / geodetic / local ENU coordinate transforms (radians, metres)."""

import math

import numpy as np

A = 6378137.0
F = 1 / 298.257223563
E2 = F * (2 - F)


def geodetic(xyz: np.ndarray) -> tuple[float, float, float]:
    x, y, z = map(float, xyz)
    p = math.hypot(x, y)
    lon = math.atan2(y, x)
    if p < 1e-9:
        return math.copysign(math.pi / 2, z), lon, abs(z) - A * (1 - F)
    lat = math.atan2(z, p * (1 - E2))
    for _ in range(12):
        n = A / math.sqrt(1 - E2 * math.sin(lat) ** 2)
        new_lat = math.atan2(z + E2 * n * math.sin(lat), p)
        if abs(new_lat - lat) < 1e-14:
            lat = new_lat
            break
        lat = new_lat
    n = A / math.sqrt(1 - E2 * math.sin(lat) ** 2)
    h = p / math.cos(lat) - n
    return lat, lon, h


def enu_rotation(xyz: np.ndarray) -> np.ndarray:
    lat, lon, _ = geodetic(xyz)
    s, c, sl, cl = math.sin(lat), math.cos(lat), math.sin(lon), math.cos(lon)
    return np.array([[-sl, cl, 0], [-s * cl, -s * sl, c], [c * cl, c * sl, s]])


def local_enu(xyz: np.ndarray, origin: np.ndarray) -> np.ndarray:
    return enu_rotation(origin) @ (xyz - origin)


def azimuth_elevation(receiver: np.ndarray, satellite: np.ndarray) -> tuple[float, float]:
    e, n, u = enu_rotation(receiver) @ (satellite - receiver)
    return math.atan2(e, n) % (2 * math.pi), math.atan2(u, math.hypot(e, n))
