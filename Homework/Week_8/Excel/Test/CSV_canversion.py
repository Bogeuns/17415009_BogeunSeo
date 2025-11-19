import pandas as pd
import os

try:
    # 0. Ask user for input filename
    input_file = input("Enter the CSV file name (e.g., Point_02): ").strip()
    # Add .csv extension if not present
    if not input_file.lower().endswith('.csv'):
        input_file += '.csv'
    output_file = os.path.splitext(input_file)[0] + ".xlsx"
    
    # 1. Load the CSV file
    df = pd.read_csv(input_file)
    print(f"Successfully loaded '{input_file}' file.")
    
    # 2. Define required columns (M: Points_0, O: Points_2, R: Pressure_Coefficient)
    required_columns = ['Points_0', 'Points_2', 'Pressure_Coefficient']
    
    # 3. Check if all required columns exist
    if all(col in df.columns for col in required_columns):
        df_processed = df[required_columns].copy()
        
        # 4. Normalize Points_0 (scale between 0 and 1)
        min_x = df_processed['Points_0'].min()
        max_x = df_processed['Points_0'].max()
        
        if (max_x - min_x) == 0:
            df_processed['Points_0_Normalized'] = 0.5 # Avoid division by zero
        else:
            df_processed['Points_0_Normalized'] = (df_processed['Points_0'] - min_x) / (max_x - min_x)
        
        # 5. Separate upper and lower surfaces based on Points_2
        df_upper = df_processed[df_processed['Points_2'] >= 0].copy()
        df_lower = df_processed[df_processed['Points_2'] < 0].copy()
        
        print(f"Number of upper surface points: {len(df_upper)}")
        print(f"Number of lower surface points: {len(df_lower)}")

        # 6. Sort upper surface (ascending)
        # Pressure_Coefficient will move along with Points_0_Normalized
        upper_sorted = df_upper[['Points_0_Normalized', 'Pressure_Coefficient']].sort_values(by='Points_0_Normalized', ascending=True)
        upper_sorted['Surface'] = 'Upper'
        
        # 7. Sort lower surface (descending) as requested in your code
        lower_sorted = df_lower[['Points_0_Normalized', 'Pressure_Coefficient']].sort_values(by='Points_0_Normalized', ascending=False)
        lower_sorted['Surface'] = 'Lower'

        # 8. Combine the sorted dataframes (Upper first, then Lower)
        combined_data = pd.concat([upper_sorted, lower_sorted])

        # 9. Save all combined data to an Excel file with user-specified name
        combined_data.to_excel(output_file, index=False)
        
        print(f"\nData sorting and combination complete. Saved to '{output_file}'")
        
        # 10. Print a preview (this does not affect the saved file)
        print("\nFile content (top 5 rows):")
        print(combined_data.head())
        print("\nFile content (bottom 5 rows):")
        print(combined_data.tail())

    else:
        print(f"Error: Required columns {required_columns} not found in the file.")

except FileNotFoundError:
    print(f"Error: '{input_file}' file not found.")
except Exception as e:
    print(f"An error occurred during data processing: {e}")