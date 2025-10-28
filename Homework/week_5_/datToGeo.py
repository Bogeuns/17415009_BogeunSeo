import argparse
import re
import sys
from pathlib import Path

import numpy as np


def parse_naca_4digit(header: str):
    match = re.search(r"(\d{4})", header)
    if not match:
        raise ValueError("Expected a NACA 4-digit code in the first line of airfoil.dat")
    code = match.group(1)
    m = int(code[0]) / 100.0
    p = int(code[1]) / 10.0
    t = int(code[2:]) / 100.0
    return code, m, p, t


def cosine_spacing(n_points: int) -> np.ndarray:
    beta = np.linspace(0.0, np.pi, n_points)
    return 0.5 * (1.0 - np.cos(beta))


def generate_naca_profile(m: float, p: float, t: float, n_surface_pts: int) -> np.ndarray:
    x = cosine_spacing(n_surface_pts)
    yt = 5.0 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1036 * x**4
    )

    yc = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)
    for i, xi in enumerate(x):
        if xi < p:
            yc[i] = m / (p**2) * (2 * p * xi - xi**2)
            dyc_dx[i] = 2 * m / (p**2) * (p - xi)
        else:
            yc[i] = m / ((1 - p) ** 2) * ((1 - 2 * p) + 2 * p * xi - xi**2)
            dyc_dx[i] = 2 * m / ((1 - p) ** 2) * (p - xi)

    theta = np.arctan(dyc_dx)
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    upper = np.column_stack((xu[::-1], yu[::-1]))          # TE → LE
    lower = np.column_stack((xl[1:], yl[1:]))              # drop duplicate LE
    return np.vstack((upper, lower))


def prompt_points(default: int) -> int:
    while True:
        try:
            raw = input(
                f"Number of cosine-spaced points per surface (default {default}): "
            ).strip()
        except EOFError:
            return default  # cannot read input; fall back to default
        if not raw:
            return default
        try:
            value = int(raw)
            if value < 40:
                print("Please enter at least 40 to keep the curve smooth.")
                continue
            return value
        except ValueError:
            print("Enter an integer value, e.g. 120.")


def main():
    data_path = Path("airfoil.dat")
    if not data_path.exists():
        raise FileNotFoundError("airfoil.dat not found")

    header = data_path.read_text().splitlines()[0]
    code, m, p, t = parse_naca_4digit(header)

    parser = argparse.ArgumentParser(description="Generate a NACA airfoil .geo file.")
    parser.add_argument(
        "-n",
        "--points",
        type=int,
        help="Cosine-spaced points per surface (TE→LE).",
    )
    parser.add_argument(
        "--default",
        type=int,
        default=160,
        help="Fallback points per surface when no input is provided (default 160).",
    )
    args = parser.parse_args()

    n_surface_pts = args.points if args.points else prompt_points(args.default)
    coords = generate_naca_profile(m, p, t, n_surface_pts)

    with open("airfoil.geo", "w") as geo:
        for idx, (x, y) in enumerate(coords, 1):
            geo.write(f"Point({idx}) = {{{x:.6f}, {y:.6f}, 0.0}};\n")
        idx_list = ", ".join(str(i) for i in range(1, len(coords) + 1))
        geo.write(f"Spline(1) = {{{idx_list}, 1}};\n")

    total = len(coords)
    print(
        f"airfoil.geo regenerated using NACA {code} with {n_surface_pts} points per surface ({total} points total)."
    )


if __name__ == "__main__":
    main()
