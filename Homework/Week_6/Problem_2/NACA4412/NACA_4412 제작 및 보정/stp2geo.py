import gmsh
import os
import math

# -------------------------------
# 설정값
# -------------------------------
DENSE_FACTOR = 20   # 내부에서 먼저 만드는 조밀한 포인트 개수 배수
LC_DEFAULT = 0.001  # .geo에서 쓸 기본 mesh size
TE_MERGE_FACTOR = 1e-4  # 코드 길이의 이 비율보다 짧으면 TE 끝점을 병합
NORMALIZE_TO_UNIT = True  # 좌표를 단위 길이로 정규화
# -------------------------------

def merge_trailing_edge(coords, factor=TE_MERGE_FACTOR):
    # coords : [(x, y, z), ...]
    # factor : chord * factor 보다 짧으면 TE를 하나의 점으로 병합
    if len(coords) < 2:
        return coords

    xs = [p[0] for p in coords]
    chord = max(xs) - min(xs)
    if chord <= 0.0:
        return coords

    x0, y0, z0 = coords[0]
    x1, y1, z1 = coords[-1]
    dist = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2)

    tol = factor * chord
    if dist < tol:
        xm = 0.5 * (x0 + x1)
        ym = 0.5 * (y0 + y1)
        zm = 0.5 * (z0 + z1)
        coords[0] = (xm, ym, zm)
        coords[-1] = (xm, ym, zm)

    return coords


def downsample_coords(coords, target_n):
    # coords   : 조밀한 포인트 리스트
    # target_n : 최종 출력할 포인트 개수
    # → 인덱스를 균등 간격으로 골라서 다운샘플링
    m = len(coords)
    if target_n >= m or target_n <= 0:
        return coords

    result = []
    step = (m - 1) / float(target_n - 1)
    for i in range(target_n):
        idx = int(round(i * step))
        if idx >= m:
            idx = m - 1
        result.append(coords[idx])
    return result


# 0. 현재 폴더에서 STEP / STP 파일 자동 탐색
folder = os.getcwd()
stp_files = [f for f in os.listdir(folder) if f.lower().endswith((".stp", ".step"))]
if not stp_files:
    print("❌ No .stp or .step file found in this folder!")
    raise SystemExit

stp_path = os.path.join(folder, stp_files[0])
geo_out = os.path.splitext(stp_path)[0] + "_sampled.geo"

print(f"STEP file : {stp_path}")
print(f"Output GEO: {geo_out}")

# 1. 최종 포인트 개수 입력
try:
    target_pts = int(input("최종 포인트 수를 입력하세요 (예: 120): "))
except Exception:
    target_pts = 120

if target_pts < 4:
    target_pts = 4

# 내부에서 먼저 만들 조밀한 포인트 개수
total_pts_dense = target_pts * DENSE_FACTOR
print(f"최종 포인트 {target_pts}개, 내부 조밀 포인트 {total_pts_dense}개로 샘플링합니다.")

# 2. Gmsh 초기화 + STEP 로드
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.model.add("airfoil_from_step")
gmsh.merge(stp_path)

# 3. 모든 1D edge 가져오기
edges = gmsh.model.getEntities(1)
if not edges:
    print("❌ STEP 파일에 1D edge가 없습니다.")
    gmsh.finalize()
    raise SystemExit

print(f"\n=== Edge list (디버그 출력) : 총 {len(edges)}개 edge ===")
for i, (dim, tag) in enumerate(edges):
    umin_arr, umax_arr = gmsh.model.getParametrizationBounds(dim, tag)
    umin, umax = umin_arr[0], umax_arr[0]
    x1, y1, z1 = gmsh.model.getValue(dim, tag, [umin])
    x2, y2, z2 = gmsh.model.getValue(dim, tag, [umax])
    du = abs(umax - umin)
    length_xy = math.hypot(x2 - x1, y2 - y1)

    print(
        f"{i:2d}: tag={tag:3d}, |u|={du:.4e}, "
        f"length≈{length_xy:.4e}, "
        f"start=({x1:.5f},{y1:.5f}), end=({x2:.5f},{y2:.5f})"
    )
print("=== 디버그 출력 끝 ===\n")

# 3-1. edge별 파라미터 범위 길이 (du)로 비율 배분 → 조밀 포인트 개수
du_list = []
total_du = 0.0
for dim, tag in edges:
    umin_arr, umax_arr = gmsh.model.getParametrizationBounds(dim, tag)
    umin = umin_arr[0]
    umax = umax_arr[0]
    du = abs(umax - umin)
    du_list.append((dim, tag, umin, umax, du))
    total_du += du

if total_du <= 0:
    print("❌ 파라미터 길이가 0입니다. STEP 형상을 확인하세요.")
    gmsh.finalize()
    raise SystemExit

pts_per_edge = []
sum_n = 0
for (_, _, _, _, du) in du_list:
    n = max(2, int(round(total_pts_dense * du / total_du)))
    pts_per_edge.append(n)
    sum_n += n

# 조밀 포인트 총합을 total_pts_dense에 맞추도록 보정
diff = total_pts_dense - sum_n
i = 0
while diff != 0 and len(pts_per_edge) > 0:
    if diff > 0:
        pts_per_edge[i] += 1
        diff -= 1
    else:
        if pts_per_edge[i] > 2:
            pts_per_edge[i] -= 1
            diff += 1
    i = (i + 1) % len(pts_per_edge)

# 4. 곡선 파라미터 따라 조밀 샘플링 (edge 순서 + 방향 맞춰서 이어붙이기)
coords_dense = []
last_x = last_y = last_z = None
first_point = True

for idx, (info, n) in enumerate(zip(du_list, pts_per_edge)):
    dim, tag, umin, umax, du = info

    x1, y1, z1 = gmsh.model.getValue(dim, tag, [umin])
    x2, y2, z2 = gmsh.model.getValue(dim, tag, [umax])

    # 이전 edge의 끝점과 더 가까운 쪽을 시작으로 (방향 맞추기)
    forward = True
    if not first_point:
        d_start = math.hypot(x1 - last_x, y1 - last_y)
        d_end = math.hypot(x2 - last_x, y2 - last_y)
        if d_end < d_start:
            forward = False

    # 파라미터 분배
    if n < 2:
        us = [umin]
    else:
        us = []
        for k in range(n):
            t = float(k) / float(n - 1)
            if forward:
                u = umin + (umax - umin) * t
            else:
                u = umax + (umin - umax) * t
            us.append(u)

    for k, u in enumerate(us):
        # edge 사이 연결점 첫 점은 중복 방지
        if not first_point and idx > 0 and k == 0:
            continue
        x, y, z = gmsh.model.getValue(dim, tag, [u])
        coords_dense.append((x, y, z))
        last_x, last_y, last_z = x, y, z
        first_point = False

try:
    if gmsh.isInitialized():
        gmsh.finalize()
except Exception as e:
    print(f"Warning: Could not finalize Gmsh properly: {e}")

print(f"조밀 포인트 개수: {len(coords_dense)}")

# 4.5 조밀 포인트 → 다운샘플링
coords = downsample_coords(coords_dense, target_pts)
print(f"다운샘플링 후 포인트 개수: {len(coords)}")

# 4.6 좌표 정규화 (최대 x, y 값이 1이 되도록 스케일링)
if NORMALIZE_TO_UNIT:
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    # 최대 차원이 1이 되도록 스케일링
    scale_x = max_x - min_x
    scale_y = max_y - min_y
    scale = max(scale_x, scale_y)
    
    if scale > 0:
        coords = [((x - min_x) / scale, (y - min_y) / scale, z) for x, y, z in coords]
        print(f"좌표 정규화 완료: x=[{min_x:.4f}, {max_x:.4f}] -> [0, {scale_x/scale:.4f}], y=[{min_y:.4f}, {max_y:.4f}] -> [0, {scale_y/scale:.4f}]")
    
# 4.7 TE 끝단 병합 (필요 없으면 이 줄 주석 처리)
coords = merge_trailing_edge(coords, factor=TE_MERGE_FACTOR * (1.0 if not NORMALIZE_TO_UNIT else scale))

# 5. GEO 작성 (Point + Line polyline 한 루프)
lc = LC_DEFAULT

with open(geo_out, "w") as f:
    # Write points
    f.write(f"lc = {lc};\n")
    for i, (x, y, z) in enumerate(coords):
        f.write(f"Point({i+1}) = {{{x}, {y}, {z}, lc}};\n")
    
    # Create a single line connecting all points
    n = len(coords)
    all_pts = ",".join(str(i) for i in range(1, n+1))
    f.write(f"Line(1) = {{{all_pts},1}};\n")  # Close the loop by connecting back to the first point
    
    # Create curve loop and surface
    f.write("Curve Loop(1) = {1};\n")
    f.write("Plane Surface(1) = {1};\n")
    
    print(f"✅ 완료: {geo_out}")
    print(f"   최종 Point 개수: {len(coords)}")

# Cleanup
try:
    if 'gmsh' in locals() and gmsh.isInitialized():
        gmsh.finalize()
except Exception as e:
    print(f"Warning: Error during cleanup: {e}")
