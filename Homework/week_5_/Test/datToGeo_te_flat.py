import argparse
import re
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


def generate_naca_profile(
    m: float,
    p: float,
    t: float,
    n_surface_pts: int,
    te_detail_points: int = 10,
) -> np.ndarray:
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
        if p != 0 and xi < p:
            yc[i] = m / (p**2) * (2 * p * xi - xi**2)
            dyc_dx[i] = 2 * m / (p**2) * (p - xi)
        elif p != 0 and p != 1:
            yc[i] = m / ((1 - p) ** 2) * ((1 - 2 * p) + 2 * p * xi - xi**2)
            dyc_dx[i] = 2 * m / ((1 - p) ** 2) * (p - xi)
        else:  # symmetric cases (m == 0 or p == 0/1)
            yc[i] = 0.0
            dyc_dx[i] = 0.0

    theta = np.arctan(dyc_dx)
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    upper = np.column_stack((xu[::-1], yu[::-1]))  # TE -> LE
    lower = np.column_stack((xl[1:], yl[1:]))  # LE -> TE (drop duplicate LE)

    def surface_at(xi: float) -> tuple[np.ndarray, np.ndarray]:
        yt_val = 5.0 * t * (
            0.2969 * np.sqrt(xi)
            - 0.1260 * xi
            - 0.3516 * xi**2
            + 0.2843 * xi**3
            - 0.1036 * xi**4
        )
        if m == 0.0 or p <= 0.0 or p >= 1.0:
            yc_val = 0.0
            dyc_dx_val = 0.0
        elif xi < p:
            denom = p**2
            yc_val = m / denom * (2 * p * xi - xi**2)
            dyc_dx_val = 2 * m / denom * (p - xi)
        else:
            denom = (1 - p) ** 2
            yc_val = m / denom * ((1 - 2 * p) + 2 * p * xi - xi**2)
            dyc_dx_val = 2 * m / denom * (p - xi)
        theta_val = np.arctan(dyc_dx_val)
        sin_theta = np.sin(theta_val)
        cos_theta = np.cos(theta_val)
        xu_val = xi - yt_val * sin_theta
        yu_val = yc_val + yt_val * cos_theta
        xl_val = xi + yt_val * sin_theta
        yl_val = yc_val - yt_val * cos_theta
        return np.array([xu_val, yu_val]), np.array([xl_val, yl_val])

    te_detail_points = max(int(te_detail_points), 0)
    if te_detail_points:
        near_te_x = x[-2] if len(x) > 1 else 1.0

        upper_sample_x = np.linspace(1.0, near_te_x, te_detail_points + 2, endpoint=True)[
            1:-1
        ]
        if upper_sample_x.size:
            upper_detail = np.array([surface_at(xi)[0] for xi in upper_sample_x])
            upper = np.vstack((upper[0], upper_detail, upper[1:]))

        lower_sample_x = np.linspace(near_te_x, 1.0, te_detail_points + 2, endpoint=True)[
            1:-1
        ]
        if lower_sample_x.size:
            lower_detail = np.array([surface_at(xi)[1] for xi in lower_sample_x])
            lower = np.vstack((lower[:-1], lower_detail, lower[-1]))

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
        help="Cosine-spaced points per surface (TE->LE).",
    )
    parser.add_argument(
        "--default",
        type=int,
        default=160,
        help="Fallback points per surface when no input is provided (default 160).",
    )
    parser.add_argument(
        "--te_detail",
        type=int,
        default=10,
        help="Additional points per surface inserted between the first trailing-edge pair.",
    )
    args = parser.parse_args()

    n_surface_pts = args.points if args.points else prompt_points(args.default)
    coords = generate_naca_profile(m, p, t, n_surface_pts, args.te_detail)

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
