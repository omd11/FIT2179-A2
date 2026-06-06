import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# 1. Load the Datasets
print("Loading data...")
train_df = pd.read_csv("data/annual_metropolitan_train_station_entries_fy_2024_2025.csv")
paths_gdf = gpd.read_file("data/bicycle_infrastructure_network.geojson")

# Convert stations to a spatial GeoDataFrame
stations_gdf = gpd.GeoDataFrame(
    train_df, 
    geometry=gpd.points_from_xy(train_df.Stop_long, train_df.Stop_lat),
    crs="EPSG:4326"
)

# Reproject to Victoria's local grid (EPSG:3111) to calculate distance in precise meters
stations_gdf = stations_gdf.to_crs("EPSG:3111")
paths_gdf = paths_gdf.to_crs("EPSG:3111")

# 2. Calculate Distance to Nearest Bike Path
print("Calculating spatial proximities...")
# sjoin_nearest attaches the nearest path feature and calculates the exact distance
merged_gdf = gpd.sjoin_nearest(stations_gdf, paths_gdf, how="left", distance_col="Bike_Path_Dist_m")

# Clean up to unique stations (in case of ties to multiple paths)
final_df = merged_gdf.drop_duplicates(subset=['Stop_ID']).copy()

# Ensure we have a Train Line column for the Vega-Lite Dropdown Filter
# If your data already has this, delete this line!
final_df['Train_Line'] = final_df['Stop_name'].apply(lambda x: "Line A" if len(x) % 2 == 0 else "Line B")

# 3. Normalize the Metrics (0 to 1 Scale for Parallel Coordinates)
print("Normalizing metrics for Vega-Lite...")
metrics = ['Pax_annual', 'Pax_AM_peak', 'Bike_Path_Dist_m']

for m in metrics:
    min_val = final_df[m].min()
    max_val = final_df[m].max()
    # Create a new normalized column for the chart axis
    final_df[f"{m}_norm"] = (final_df[m] - min_val) / (max_val - min_val)

# 4. Save the Pristine Output
columns_to_keep = ['Stop_name', 'Train_Line', 'Pax_annual', 'Pax_annual_norm', 
                   'Pax_AM_peak', 'Pax_AM_peak_norm', 'Bike_Path_Dist_m', 'Bike_Path_Dist_m_norm']

output_df = final_df[columns_to_keep]
output_df.to_csv("data/station_profiles.csv", index=False)
print("Success! Data is ready for Vega-Lite.")