import os
import zipfile
import pandas as pd

# Define paths
ZIP_FOLDER = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/raw_zips/"
OUTPUT_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/aggregated_bicycle_volume.csv"

import os
import zipfile
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
ZIP_FOLDER = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/bicycle_volume_speed_2024/"
TRAIN_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/annual_metropolitan_train_station_entries_fy_2024_2025.csv"

# Outputs
OUTPUT_BIKE_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/aggregated_bicycle_volume.csv" # For Idiom 5 (Scatter Plot)
OUTPUT_SHIFT_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/commuter_shift.csv"           # For Idiom 4 (Bar Chart)

all_bike_data = []

print(f"Phase 1: Scanning for zip files in {ZIP_FOLDER}...")

# ---------------------------------------------------------
# PHASE 1: Extract & Aggregate Bicycle Data by Day Type
# ---------------------------------------------------------
for filename in os.listdir(ZIP_FOLDER):
    if filename.endswith(".zip"):
        zip_path = os.path.join(ZIP_FOLDER, filename)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            for internal_file in z.namelist():
                if internal_file.endswith('.csv'):
                    
                    # 1. Parse the filename: IND_D208_X6411_NS_20240624.csv
                    clean_name = internal_file.replace('.csv', '')
                    parts = clean_name.split('_')
                    
                    # Extract Site ID (the part starting with 'X')
                    site_part = next((p for p in parts if p.startswith('X')), None)
                    if not site_part:
                        continue 
                    site_id = site_part.replace('X', '')
                    
                    # Extract Date string (the last part) and determine Day Type
                    date_str = parts[-1]
                    try:
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                        # weekday() returns 0 for Monday, 6 for Sunday. >= 5 is Weekend.
                        day_type = 'Weekend' if date_obj.weekday() >= 5 else 'Weekday'
                    except ValueError:
                        print(f"Skipping {internal_file}: Couldn't parse date {date_str}")
                        continue
                    
                    # 2. Read file and count volume
                    with z.open(internal_file) as f:
                        try:
                            # Read only a single column to save massive amounts of RAM
                            df = pd.read_csv(f, usecols=[0]) 
                            daily_count = len(df)
                            
                            all_bike_data.append({
                                'SITE_XN_ROUTE': site_id,
                                'Date': date_obj,
                                'Day_Type': day_type,
                                'Volume': daily_count
                            })
                        except Exception as e:
                            print(f"Error reading {internal_file}: {e}")

print("Structuring bicycle data...")
bike_df = pd.DataFrame(all_bike_data)

if bike_df.empty:
    print("No bicycle data found. Check your zip folder path.")
else:
    # 3. Calculate Overall Average + Day Type Averages per Site
    # Get Weekday vs Weekend averages
    site_day_avg = bike_df.groupby(['SITE_XN_ROUTE', 'Day_Type'])['Volume'].mean().unstack(fill_value=0).reset_index()
    site_day_avg.rename(columns={'Weekday': 'Avg_Weekday_Volume', 'Weekend': 'Avg_Weekend_Volume'}, inplace=True)
    
    # Get Overall Daily average (For Idiom 5)
    site_overall = bike_df.groupby('SITE_XN_ROUTE')['Volume'].mean().reset_index(name='Avg_Daily_Volume')
    
    # Merge them into a master bicycle lookup table
    master_bike_df = pd.merge(site_overall, site_day_avg, on='SITE_XN_ROUTE')
    
    # Round everything to whole numbers
    for col in ['Avg_Daily_Volume', 'Avg_Weekday_Volume', 'Avg_Weekend_Volume']:
        master_bike_df[col] = master_bike_df[col].round(0).astype(int)
        
    master_bike_df.to_csv(OUTPUT_BIKE_CSV, index=False)
    print(f"Success! Saved comprehensive bicycle data to {OUTPUT_BIKE_CSV}")


    # ---------------------------------------------------------
    # PHASE 2: Generate the Normalized Idiom 4 Commuter Shift CSV
    # ---------------------------------------------------------
    print("Phase 2: Generating Commuter Shift comparison...")
    
    # Sum total network bicycle volumes
    total_bike_weekday = master_bike_df['Avg_Weekday_Volume'].sum()
    total_bike_weekend = master_bike_df['Avg_Weekend_Volume'].sum()
    
    # Load and sum train volumes
    try:
        train_df = pd.read_csv(TRAIN_CSV)
        total_train_weekday = train_df['Pax_weekday'].sum()
        
        # Train weekend average is (Saturday + Sunday) / 2
        train_weekend_avg_per_station = (train_df['Pax_Saturday'] + train_df['Pax_Sunday']) / 2
        total_train_weekend = train_weekend_avg_per_station.sum()
        
        # Normalize Data (Scale to 100 for visual comparison)
        max_bike = max(total_bike_weekday, total_bike_weekend)
        max_train = max(total_train_weekday, total_train_weekend)
        
        shift_data = [
            {'Day_Type': 'Weekday', 'Transport_Mode': 'Bicycle', 'Normalized_Volume': (total_bike_weekday / max_bike) * 100},
            {'Day_Type': 'Weekend', 'Transport_Mode': 'Bicycle', 'Normalized_Volume': (total_bike_weekend / max_bike) * 100},
            {'Day_Type': 'Weekday', 'Transport_Mode': 'Metro Train', 'Normalized_Volume': (total_train_weekday / max_train) * 100},
            {'Day_Type': 'Weekend', 'Transport_Mode': 'Metro Train', 'Normalized_Volume': (total_train_weekend / max_train) * 100}
        ]
        
        shift_df = pd.DataFrame(shift_data)
        shift_df['Normalized_Volume'] = shift_df['Normalized_Volume'].round(1)
        
        shift_df.to_csv(OUTPUT_SHIFT_CSV, index=False)
        print(f"Success! Saved normalized comparison to {OUTPUT_SHIFT_CSV}")
        print("\n--- Idiom 4 Data Preview ---")
        print(shift_df)
        
    except FileNotFoundError:
        print(f"Could not locate {TRAIN_CSV}. Make sure the path is correct to generate the Idiom 4 data.")