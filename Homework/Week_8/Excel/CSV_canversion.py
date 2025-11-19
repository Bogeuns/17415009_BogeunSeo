import pandas as pd
import os

def process_file(input_file):
    # Add .csv extension if not present
    if not input_file.lower().endswith('.csv'):
        input_file += '.csv'
    output_file = os.path.splitext(input_file)[0] + ".xlsx"
    
    try:
        # Load the CSV file
        df = pd.read_csv(input_file)
        print(f"\nProcessing file: {input_file}")
        return df, output_file
    except FileNotFoundError:
        print(f"Error: '{input_file}' file not found.")
        return None, None

try:
    # Get input files one by one until user is done
    input_files = []
    print("Enter file names one by one. Press Enter without typing anything when done.")
    
    while True:
        filename = input(f"Enter file name (or press Enter to finish): ").strip()
        if not filename:  # If user presses Enter without typing anything
            if not input_files:  # If no files were entered
                print("No files entered. Please enter at least one file.")
                continue
            break
        input_files.append(filename)
        print(f"Added: {filename}.csv")
    
    print(f"\nProcessing {len(input_files)} files...")
    
    # Process each file
    for input_file in input_files:
        df, output_file = process_file(input_file)
        if df is None:
            continue  # Skip if file not found
    
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
            
            print(f"Data sorting and combination complete. Saved to '{output_file}'")
        
            # 10. Print a preview (this does not affect the saved file)
            print("\nFile content (top 5 rows):")
            print(combined_data.head())
            print("\nFile content (bottom 5 rows):")
            print(combined_data.tail())
        else:
            print(f"Error: Required columns {required_columns} not found in the file.")
    
        print("\n" + "="*50 + "\n")  # Add separator between files

except ValueError as ve:
    print(f"Error: {ve}")
except Exception as e:
    print(f"An error occurred during data processing: {e}")

print("\nAll files have been processed.")