"""Klobuchar and the exact standard-meteorology teaching Saastamoinen model."""

import math

from .ephemeris import C


def ionosphere(
    lat: float, lon: float, az: float, el: float, sow: float, alpha: list[float], beta: list[float]
) -> float:
    phi_u, lam_u, elev = lat / math.pi, lon / math.pi, el / math.pi
    psi = 0.0137 / (elev + 0.11) - 0.022
    phi_i = max(-0.416, min(0.416, phi_u + psi * math.cos(az)))
    lam_i = lam_u + psi * math.sin(az) / math.cos(math.pi * phi_i)
    phi_m = phi_i + 0.064 * math.cos(math.pi * (lam_i - 1.617))
    local_time = (43200 * lam_i + sow) % 86400
    amp = max(0.0, sum(a * phi_m**j for j, a in enumerate(alpha)))
    period = max(72000.0, sum(b * phi_m**j for j, b in enumerate(beta)))
    x = 2 * math.pi * (local_time - 50400) / period
    mapping = 1 + 16 * (0.53 - elev) ** 3
    delay = 5e-9 + amp * (1 - x * x / 2 + x**4 / 24) if abs(x) < 1.57 else 5e-9
    return C * mapping * delay


def troposphere(lat: float, height: float, el: float) -> float:
    if el <= 0 or height > 20000 or height < -20000:
        return 0.0
    h = max(0.0, height)
    pressure = 1013.25 * (1 - 2.2557e-5 * h) ** 5.2568
    temp = 15 - 6.5e-3 * h + 273.16
    vapor = 6.108 * 0.7 * math.exp((17.15 * temp - 4684) / (temp - 38.45))
    dry = (
        0.0022768 * pressure / (1 - 0.00266 * math.cos(2 * lat) - 0.00028 * h / 1000) / math.sin(el)
    )
    wet = 0.002277 * (1255 / temp + 0.05) * vapor / math.sin(el)
    return dry + wet
