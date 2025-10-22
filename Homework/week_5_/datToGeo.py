import numpy as np
import os

try:
    # Read the airfoil data (skip the first 3 lines: title and leading edge point)
    data = np.loadtxt('airfoil.dat', skiprows=3)
    
    # Write to output file
    with open('airfoil.geo', 'w') as f:
        # Write all points in sequence
        for i, (x, y) in enumerate(data, 1):
            f.write(f'Point({i}) = {{{x:.6f}, {y:.6f}, 0.0}};\n')
        
        # Write line connecting all points in order
        total_points = len(data)
        point_indices = ', '.join(str(i) for i in range(1, total_points + 1))
        f.write(f'Line(1) = {{{point_indices}}};')
        
    print(f"Successfully created airfoil.geo with {total_points} points in sequence")
    
except FileNotFoundError:
    print("Error: airfoil.dat not found in the current directory")
except Exception as e:
    print(f"An error occurred: {str(e)}")
    if 'f' in locals() and not f.closed:
        f.close()
