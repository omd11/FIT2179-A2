import os
import zipfile
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
ZIP_FOLDER = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/bicycle_volume_speed_2024/"
OUTPUT_SPEED_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/commuter_speeds_sampled.csv"

# We will cap the output to 30,000 rows so Vega-Lite runs at 60fps in the browser
MAX_OUTPUT_ROWS = 30000 

print(f"Scanning for zip files in {ZIP_FOLDER}...")

all_peak_data = []

for filename in os.listdir(ZIP_FOLDER):
    if filename.endswith(".zip"):
        zip_path = os.path.join(ZIP_FOLDER, filename)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            for internal_file in z.namelist():
                if internal_file.endswith('.csv'):
                    
                    # 1. Extract Site ID from filename
                    parts = internal_file.replace('.csv', '').split('_')
                    site_part = next((p for p in parts if p.startswith('X')), None)
                    if not site_part:
                        continue 
                    site_id = site_part.replace('X', '')
                    
                    # 2. Extract only the required columns directly from the zip
                    with z.open(internal_file) as f:
                        try:
                            # Load only TIME and SPEED to save RAM
                            df = pd.read_csv(f, usecols=['TIME', 'SPEED'])
                            
                            # Drop errors or zero-speeds (stationary objects)
                            df = df.dropna(subset=['TIME', 'SPEED'])
                            df = df[(df['SPEED'] > 0) & (df['SPEED'] < 60)] # Filter anomalies over 60km/h
                            
                            # 3. Parse the hour from 'HH:MM:SS' string format
                            df['Hour'] = df['TIME'].str.split(':').str[0].astype(int)
                            
                            # 4. Filter for Peak Hours Only
                            am_mask = df['Hour'].isin([7, 8, 9])       # 7:00 AM - 9:59 AM
                            pm_mask = df['Hour'].isin([15, 16, 17, 18]) # 3:00 PM - 6:59 PM
                            
                            peak_df = df[am_mask | pm_mask].copy()
                            
                            if not peak_df.empty:
                                # Assign labels
                                peak_df['Time_Window'] = np.where(peak_df['Hour'].isin([7, 8, 9]), 'AM Peak', 'PM Peak')
                                peak_df['SITE_XN_ROUTE'] = site_id
                                
                                # Keep only the necessary columns for the final chart
                                all_peak_data.append(peak_df[['SITE_XN_ROUTE', 'Time_Window', 'SPEED']])
                                
                        except Exception as e:
                            # Catch files that might be completely empty or missing headers
                            pass

print("Merging speed data...")
if all_peak_data:
    master_speed_df = pd.concat(all_peak_data, ignore_index=True)
    
    # 5. Find the Top 10 Busiest Sites to keep the chart legible
    top_sites = master_speed_df['SITE_XN_ROUTE'].value_counts().nlargest(10).index
    master_speed_df = master_speed_df[master_speed_df['SITE_XN_ROUTE'].isin(top_sites)]
    
    # 6. Downsample the data for web performance
    if len(master_speed_df) > MAX_OUTPUT_ROWS:
        print(f"Downsampling from {len(master_speed_df)} to {MAX_OUTPUT_ROWS} rows for web performance...")
        final_df = master_speed_df.sample(n=MAX_OUTPUT_ROWS, random_state=42)
    else:
        final_df = master_speed_df
        
    final_df.to_csv(OUTPUT_SPEED_CSV, index=False)
    print(f"Success! Saved filtered boxplot data to {OUTPUT_SPEED_CSV}")
else:
    print("No valid speed data found. Check your zip files.")