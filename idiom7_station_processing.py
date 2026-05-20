import pandas as pd
import numpy as np

# --- CONFIGURATION ---
INPUT_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/annual_metropolitan_train_station_entries_fy_2024_2025.csv"
OUTPUT_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/sankey_commuter_flow.csv"

# 1. Define the core Inner City / CBD Hubs explicitly
CBD_STATIONS = [
    'Flinders Street', 'Southern Cross', 'Melbourne Central', 
    'Parliament', 'Flagstaff', 'Richmond', 'North Melbourne'
]

# 2. Define the geographic center of Melbourne (roughly State Library)
MELB_CENTER_LAT = -37.8100
MELB_CENTER_LON = 144.9630

def classify_region(row):
    """Classifies a station into a region based on its coordinates relative to the CBD."""
    name = str(row['Stop_name']).strip()
    lat = float(row['Stop_lat'])
    lon = float(row['Stop_long'])
    
    # Check if it's a designated CBD hub first
    if name in CBD_STATIONS:
        return 'CBD Hubs'
    
    # Calculate coordinate delta from the center
    d_lat = lat - MELB_CENTER_LAT
    d_lon = lon - MELB_CENTER_LON
    
    # West: Significantly lower longitude
    if d_lon < -0.035:
        return 'West (e.g., Sunbury, Werribee)'
    # East: Higher longitude, generally above the South-Eastern bay curve
    elif d_lon > 0.035 and d_lat > -0.15:
        return 'East (e.g., Ringwood, Glen Waverley)'
    # North: Higher latitude (less negative)
    elif d_lat > 0:
        return 'North (e.g., Craigieburn, Upfield)'
    # South: Lower latitude, clinging to the bay
    else:
        return 'South (e.g., Frankston, Sandringham)'

print("Loading dataset...")
try:
    df = pd.read_csv(INPUT_CSV)
    
    # 3. Apply the geographic classification
    print("Classifying stations into regional sectors...")
    df['Region'] = df.apply(classify_region, axis=1)
    
    # 4. Filter out the CBD entries for the inbound flow calculation 
    # (We only want Suburb -> CBD for this specific inbound AM Peak idiom)
    suburb_df = df[df['Region'] != 'CBD Hubs'].copy()
    
    # 5. Aggregate the AM Peak volume by Region
    aggregated_flow = suburb_df.groupby('Region')['Pax_AM_peak'].sum().reset_index()
    
    # 6. Structure the data for a Sankey Diagram (Source, Target, Volume)
    sankey_df = pd.DataFrame({
        'Source': aggregated_flow['Region'],
        'Target': 'CBD Hubs',
        'Volume': aggregated_flow['Pax_AM_peak']
    })
    
    # Sort by volume so the Sankey diagram draws the thickest lines at the top
    sankey_df = sankey_df.sort_values(by='Volume', ascending=False)
    
    # Export the final clean file
    sankey_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Success! Sankey data exported to {OUTPUT_CSV}")
    print("\n--- Data Preview ---")
    print(sankey_df)

except FileNotFoundError:
    print(f"Error: Could not find {INPUT_CSV}. Please check the path.")