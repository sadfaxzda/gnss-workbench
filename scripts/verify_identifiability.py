"""Recompute a saved two-world diagnostic ambiguity example, without fitting truth.

This is an explanatory development counterexample, not an acceptance test or a
replacement for the teacher's metrics. The Gaussian bound concerns choosing one
of two fault identities with equal priors, not the course's horizontal P95.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from validate_six_satellite import simulate_range

from gnss_workbench.core.coordinates import geodetic, local_enu
from gnss_workbench.core.ephemeris import C, rotate_to_receive, transmit_state
from gnss_workbench.io import navigation_from
from gnss_workbench.settings import COURSE_ROOT, PROJECT_ROOT


def verify(case: dict, nav: dict) -> dict:
    satellites, sow = case["satellites"], case["time"]
    sigma = case["gaussian_sigma_m"]
    if sigma <= 0 or len(satellites) != len(set(satellites)):
        raise ValueError("Positive noise scale and distinct satellites are required")
    worlds = {}
    for name in ("world_a", "world_b"):
        world = case[name]
        xyz, clock = np.array(world["xyz"]), world["clock"]
        if abs(world["bias"]) < 30 or world["fault"] not in satellites:
            raise ValueError("Each world must have one observed strong fault")
        means, elevations, h, ages = [], [], [], []
        for sat in satellites:
            eph = nav["ephemerides"][sat]
            age = (nav["gps_week"] - eph["gps_week"]) * 604800 + sow - eph["toe"]
            if abs(age) > 7200 or eph.get("sv_health", 0) != 0:
                raise ValueError("Example outside course ephemeris domain")
            p, el = simulate_range(nav, sat, xyz, clock, sow)
            means.append(p + (world["bias"] if sat == world["fault"] else 0))
            elevations.append(math.degrees(el))
            ages.append(abs(age))
            satellite, code_clock = transmit_state(eph, sow, p)
            satellite = rotate_to_receive(satellite, (p + C * code_clock - clock) / C)
            delta = xyz - satellite
            h.append([*(delta / np.linalg.norm(delta)), 1])
        pdop = float(np.linalg.norm(np.linalg.pinv(np.array(h))[:3]))
        height = geodetic(xyz)[2]
        mean_change = float(np.max(np.abs(np.array(means) - world["means"])))
        if min(elevations) <= 3 or pdop > 30 or height < 0 or mean_change > 0.001:
            raise ValueError("Counterexample domain or saved observation check failed")
        worlds[name] = dict(
            means_m=means,
            min_elevation_deg=min(elevations),
            pdop=pdop,
            height_m=height,
            max_ephemeris_age_s=max(ages),
            max_saved_mean_difference_m=mean_change,
        )
    distance = float(
        np.linalg.norm(np.array(worlds["world_a"]["means_m"]) - worlds["world_b"]["means_m"])
    )
    # Projection onto the mean-difference direction gives two scalar normal
    # distributions. Their equal-prior decision boundary is their midpoint.
    success = 0.5 * (1 + math.erf(distance / (2 * sigma * math.sqrt(2))))
    separation = float(
        np.linalg.norm(
            local_enu(np.array(case["world_b"]["xyz"]), np.array(case["world_a"]["xyz"]))[:2]
        )
    )
    return dict(
        worlds=worlds,
        horizontal_separation_at_a_m=separation,
        mean_observation_distance_m=distance,
        gaussian_sigma_m=sigma,
        optimal_equal_prior_identity_success=success,
        scope="One isolated epoch; two known hypotheses; independent Gaussian noise with equal covariance. No universal horizontal-error bound, no teacher hidden-test claim.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Output already exists; preserve earlier evidence")
    nav_path = COURSE_ROOT / "data/navigation.json"
    result = verify(json.loads(args.case.read_text()), navigation_from(nav_path))
    paths = [
        Path(__file__),
        PROJECT_ROOT / "scripts/validate_six_satellite.py",
        args.case,
        nav_path,
    ]
    result["sha256"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
