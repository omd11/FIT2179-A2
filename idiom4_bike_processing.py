import os
import zipfile
import pandas as pd
import geopandas as gpd
from datetime import datetime

# --- CONFIGURATION PATHS ---
ZIP_FOLDER = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/bicycle_volume_speed_2024/"
METADATA_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/counter_locations.csv" # MUST contain: SITE_XN_ROUTE, Lat, Long
GEOJSON_PATH = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/bicycle_infrastructure_network.geojson"
OUTPUT_CSV = r"C:/Users/Omid/OneDrive - Monash University/2026/S1-FIT2179/A2/data/cycling_flow_continuous_paths.csv"

# ---------------------------------------------------------
# PHASE 1: Aggregate Bicycle Volumes (From Zips)
# ---------------------------------------------------------
print("Phase 1: Extracting and aggregating zip volumes...")
all_bike_data = []

for filename in os.listdir(ZIP_FOLDER):
    if filename.endswith(".zip"):
        zip_path = os.path.join(ZIP_FOLDER, filename)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            for internal_file in z.namelist():
                if internal_file.endswith('.csv'):
                    # Parse filename for Site ID and Date
                    parts = internal_file.replace('.csv', '').split('_')
                    site_part = next((p for p in parts if p.startswith('X')), None)
                    if not site_part:
                        continue 
                    site_id = int(site_part.replace('X', ''))
                    
                    date_str = parts[-1]
                    try:
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                        day_type = 'Weekend' if date_obj.weekday() >= 5 else 'Weekday'
                    except ValueError:
                        continue
                    
                    # Count rows for daily volume
                    with z.open(internal_file) as f:
                        try:
                            df = pd.read_csv(f, usecols=[0]) 
                            all_bike_data.append({
                                'SITE_XN_ROUTE': site_id,
                                'Day_Type': day_type,
                                'Volume': len(df)
                            })
                        except Exception:
                            pass

# Aggregate Volumes
bike_df = pd.DataFrame(all_bike_data)
site_overall = bike_df.groupby('SITE_XN_ROUTE')['Volume'].mean().reset_index(name='Avg_Daily_Volume')

# Pivot Weekday/Weekend
site_day_avg = bike_df.groupby(['SITE_XN_ROUTE', 'Day_Type'])['Volume'].mean().unstack(fill_value=0).reset_index()
site_day_avg.rename(columns={'Weekday': 'Avg_Weekday_Volume', 'Weekend': 'Avg_Weekend_Volume'}, inplace=True)

# Master Volume DataFrame
volume_agg_df = pd.merge(site_overall, site_day_avg, on='SITE_XN_ROUTE')
for col in ['Avg_Daily_Volume', 'Avg_Weekday_Volume', 'Avg_Weekend_Volume']:
    volume_agg_df[col] = volume_agg_df[col].round(0).astype(int)

# ---------------------------------------------------------
# PHASE 2: Attach Coordinates to Volumes
# ---------------------------------------------------------
print("Phase 2: Attaching spatial coordinates...")
# Load metadata containing Lat/Long for each SITE_XN_ROUTE
meta_df = pd.read_csv(METADATA_CSV)
spatial_volume_df = pd.merge(volume_agg_df, meta_df, on='SITE_XN_ROUTE', how='inner')

# Convert to GeoDataFrame (WGS84)
counters_gdf = gpd.GeoDataFrame(
    spatial_volume_df, 
    geometry=gpd.points_from_xy(spatial_volume_df.STRT_LONG, spatial_volume_df.STRT_LAT),
    crs="EPSG:4326"
)

# ---------------------------------------------------------
# PHASE 3: Calculate Continuous Path Lengths
# ---------------------------------------------------------
print("Phase 3: Processing GeoJSON and calculating continuous lengths...")
paths_gdf = gpd.read_file(GEOJSON_PATH)

# Ensure empty road names don't break the dissolve grouping
paths_gdf['Name'] = paths_gdf['Name'].fillna('Unnamed Path')

# 1. Dissolve: Merge segments sharing the same Name AND InfraType
dissolved_paths = paths_gdf.dissolve(by=['Name', 'InfraType'], as_index=False)

# 2. Explode: If a "High Street" bike lane is physically broken by a 2km gap, 
# this forces them back into two distinct continuous segments rather than a unified ghost segment.
continuous_paths = dissolved_paths.explode(index_parts=False).reset_index(drop=True)

# 3. Project to Victoria's local grid (EPSG:7899 - GDA2020 / Vicgrid) for accurate meters
continuous_paths = continuous_paths.to_crs("EPSG:7899")
counters_gdf = counters_gdf.to_crs("EPSG:7899")

# 4. Calculate actual continuous length
continuous_paths['Continuous_Length_m'] = continuous_paths.geometry.length

# ---------------------------------------------------------
# PHASE 4: Spatial Join & Export
# ---------------------------------------------------------
print("Phase 4: Snapping counters to nearest continuous path...")

# Find the nearest continuous path to each counter
# (We retain the distance_to_path column to verify accuracy later if needed)
final_gdf = gpd.sjoin_nearest(counters_gdf, continuous_paths, how="left", distance_col="Distance_To_Path_m")

# Keep only necessary columns for Vega-Lite to keep the file tiny
export_df = final_gdf[[
    'SITE_XN_ROUTE', 
    'Avg_Daily_Volume', 
    'Avg_Weekday_Volume', 
    'Avg_Weekend_Volume',
    'Name',
    'InfraType', 
    'Continuous_Length_m',
    'Distance_To_Path_m'
]]

# Rename for clean Vega-Lite mapping
export_df = export_df.rename(columns={'Name': 'Path_Name', 'InfraType': 'Path_Type'})

# Round lengths for readability
export_df['Continuous_Length_m'] = export_df['Continuous_Length_m'].round(1)
export_df['Distance_To_Path_m'] = export_df['Distance_To_Path_m'].round(1)

export_df.to_csv(OUTPUT_CSV, index=False)
print(f"Success! Final data saved to {OUTPUT_CSV}")