import os
import glob
import re
from datetime import datetime
import fiona
import pandas as pd
import geopandas as gpd
from shapely import Point, wkt
from shapely.geometry.base import BaseGeometry

# Requirements
# - robust against small data format changes
# - flexibility so all columns are processed even with different variable names, formats
# - additional species name and type data added by matching with attached species list 

# Example data: 
# geom (hidden), fid (auto), year, month, day, species, date, observer, height, radius, photoid, count, year1, comment, type, english_name, taxa
# Example row: Point (-2.79425316963482118 56.33810287940671913)	1	2024-25	02	08	Calluna vulgaris	2025-02-08	Alice Mortimer	2025 Angiosperm	Heather	Angiosperm

# This is the list we want to have in every GPKG so even if some columns are different, they will be added/converted to match this
# Includes expected column names and data type of the fields  
# Includes a list of alternative column names (from different versions of GPKG exports) - can manually add more variants as needed
STANDARD_COLUMNS = [
    {"name": "geom", "datatype": "geometry", "alt_names": ["geom", "geometry"]}, # Location of the observation (geometry for mapping)
    {"name": "species", "datatype": "text", "alt_names": ["species", "species name", "scientific_name", "scientific name"]}, # Observed species
    {"name": "english_name", "datatype": "text", "alt_names": ["english_name", "english name", "english"]},  # English name of species 
    {"name": "type", "datatype": "text", "alt_names": ["type"]}, # Type of species mapped from CSV file: 'species list' 
    {"name": "date", "datatype": "date", "alt_names": ["date", "date_obs"]}, # Date of the observation
    {"name": "samp_year", "datatype": "text", "alt_names": ["samp_year", "school_year", "year"]}, # The ecological year (May to April) during which the observation was made.
    {"name": "cal_year", "datatype": "numeric", "alt_names": ["cal_year", "calendar_year", "year1"]}, # The normal January to December year of the observation.
    {"name": "month", "datatype": "numeric", "alt_names": ["month"]}, # Month of observation - taken from date
    {"name": "day", "datatype": "numeric", "alt_names": ["day"]},  # Day of observation - taken from date 
    {"name": "taxa", "datatype": "text", "alt_names": ["taxa"]},  # Taxonomic classification
    {"name": "observer", "datatype": "text", "alt_names": ["observer", "observer name", "obs"]},  # Name of the observer
    {"name": "comment", "datatype": "text", "alt_names": ["comment"]}, # Notes or comments (optional)
    {"name": "height", "datatype": "numeric", "alt_names": ["height"]},  # Observed height (optional)
    {"name": "radius", "datatype": "numeric", "alt_names": ["radius"]}, # Observed radius (optional)
    {"name": "photoid", "datatype": "text", "alt_names": ["photoid"]},  # Photo ID for any pictures taken (optional)
    {"name": "count", "datatype": "numeric", "alt_names": ["count"]}  # Observed number
]

# Standardises a GeoDataFrame to the expected pipeline format 
def standardise(gdf, label="gdf"):
    if gdf.empty:
        for column in STANDARD_COLUMNS:
            gdf[column["name"]] = None 
        return gdf
    
    # clean column names: removes extra whitespace, converts to lowercase, and replaces spaces with underscores (e.g., "English Name" becomes "english_name") to help with mapping to the expected column names in the pipeline
    gdf.columns = gdf.columns.str.strip().str.lower().str.replace(" ", "_")

    # map any alternative column names to the standard column names
    rename_dict = {}
    for column in STANDARD_COLUMNS:
        for alt in column["alt_names"]:
            key = alt.lower().replace(" ", "_")
            if key in gdf.columns:
                rename_dict[key] = column["name"]
    gdf = gdf.rename(columns=rename_dict)

    gdf = validate_geometry(gdf)
    gdf = parse_dates(gdf)

    # drop any rows where critical data is missing 
    critical_cols = ["geom", "species", "date", "observer"] # these are the minimum fields needed for a valid observation
    existing_critical_cols = [col for col in critical_cols if col in gdf.columns] 
    if existing_critical_cols: # checking if the columns exist first 
        before_drop = len(gdf)
        gdf = gdf.dropna(subset=existing_critical_cols) # drop if data is NaN/None (missing)
        dropped = before_drop - len(gdf)
        print(f"Dropped {dropped} records from {label} with missing critical data: {', '.join(existing_critical_cols)}")

    # clean text fields: strip extra whitespace and convert to title case (e.g., "will cresswell" becomes "Will Cresswell")
    for column in STANDARD_COLUMNS:
        if column["datatype"] == "text" and column["name"] in gdf.columns:
            gdf[column["name"]] = gdf[column["name"]].astype(str).str.strip().str.lower().str.title().str.replace(r'\s+', ' ', regex=True) 

    # special casing: species text field keeps the genus capitalised and species/sub-species lowercase e.g. "Calluna Vulgaris" should be "Calluna vulgaris"
    if "species" in gdf.columns:
        gdf["species"] = gdf["species"].apply(
            lambda x: f"{x.split()[0]} {' '.join(p.lower() for p in x.split()[1:])}" 
            if isinstance(x, str) and len(x.split()) > 1 else x
        )
        
    # ensure all standard columns exist 
    for column in STANDARD_COLUMNS:
        if column["name"] not in gdf.columns:
            gdf[column["name"]] = None

    # reorder columns to match the expected format (any missing columns will be added with None values)
    gdf = gdf[[column["name"] for column in STANDARD_COLUMNS]]

    # drop any rows with invalid observers or calendar years
    gdf = clean_invalid_rows(gdf, label=label) 
    return gdf

# drop any rows with invalid observers or calendar years before 2020 (can adjust year threshold as needed)
def clean_invalid_rows(gdf, min_year=2020, label="gdf"):
    # drop any rows with invalid observers
    bad_observers = ["Jackson Robinson"] # can expand list as needed
    before = len(gdf)
    gdf = gdf[~gdf["observer"].isin(bad_observers)]
    print(f"Dropped {before - len(gdf)} records from {label} with invalid observers: {', '.join(bad_observers)}")

    # drop any rows where the year is < min year
    before = len(gdf)
    gdf = gdf[gdf["cal_year"] >= min_year]
    print(f"Dropped {before - len(gdf)} records from {label} with calendar year before {min_year}")
    return gdf

# ensures geometry is valid and in the correct CRS (EPSG:4326) for mapping in the app - if there is a geometry column
def validate_geometry(gdf):
    geom_col = next((column["name"] for column in STANDARD_COLUMNS if column["datatype"] == "geometry"), None)
    if geom_col and geom_col in gdf.columns:
        gdf[geom_col] = gdf[geom_col].apply(lambda x: wkt.loads(str(x)) if x and not isinstance(x, BaseGeometry) else x)
        gdf = gdf.set_geometry(geom_col, inplace=False)
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
    else:
        print("Warning: No geometry column found.")
    return gdf

# parses date fields and extracts calendar year, month, day, and calculates the sampling year (ecological year) based on the date of observation. 
# This helps to standardise date information across different GPKG formats and allows for easier analysis of temporal patterns in the data.
def parse_dates(gdf):
    date_col = next((column["name"] for column in STANDARD_COLUMNS if column["datatype"] == "date"), None)
    if date_col and date_col in gdf.columns:
        gdf[date_col] = pd.to_datetime(gdf[date_col], errors="coerce") #converts to datetime format, coercing any invalid formats to NaT (Not a Time)
        gdf["cal_year"] = gdf[date_col].dt.year
        gdf["month"] = gdf[date_col].dt.month
        gdf["day"] = gdf[date_col].dt.day
        gdf["samp_year"] = gdf.apply(calculate_sampling_year, axis=1)
    return gdf

# Calculate year (sampling year) in format YYYY-YY based on non-calendar year (May 1 - April 30)
def calculate_sampling_year(row):
    if pd.isna(row["date"]):
        return None
    year, month = row["date"].year, row["date"].month 
    if month >= 5: # May to December
        return f"{year}-{str(year+1)[-2:]}"  # Format: year-next_year (e.g., 2025-26)
    else:  # January to April
        return f"{year-1}-{str(year)[-2:]}" # Format: previous_year-year (e.g., 2024-25)
    
# Full pipeline: update the input GPKGs, backup the main GPKG, and merge collected data from student observers into the main GPKG
def run_pipeline(student_gpkgs_directory, species_csv, main_file, backup_folder):
    try: 
        create_main_copy(main_file, backup_folder) # backup of main GPKG before merging new data
        
        main_gdf = standardise(read_gpkg(main_file), "main gdf") # read main GPKG to get current data for merging
        student_gdfs = standardise(read_student_gpkgs(student_gpkgs_directory), "student gdf") # read all student GPKGs into GeoDataFrames
        
        combined = merge_collected_data(main_gdf, student_gdfs) # merge all student GPKGs into the main GPKG
        combined = update_species_info(combined, species_csv, "combined gdf") # update 'type' and 'english_name' in the GDF based on species CSV mapping
        combined = detect_and_remove_duplicates(combined, "combined gdf") # detect and remove any duplicate observations in the main GPKG after merging new data
        save_main_gpkg(combined, main_file) # save the updated main GPKG with merged data and duplicates removed
        
    except Exception as e:  
        print(f"Error during pipeline execution: {e}")

# update 'type' and 'english_name' in the GDF based on species CSV mapping
def update_species_info(gdf, species_csv, label="gdf"):
    try:
        # Load species CSV
        species_df = pd.read_csv(species_csv, encoding='ISO-8859-1')
        species_df['species'] = species_df['species'].str.strip().str.lower()  # lowercase for case-insensitive matching
        species_df = species_df[species_df['species'] != '']

        # Check for duplicates in species CSV
        dupes = species_df['species'][species_df['species'].duplicated()].unique()
        if len(dupes) > 0:
            print(f"Warning: Duplicate species in CSV (keeping first occurrence): {', '.join(dupes)}")
            species_df = species_df.drop_duplicates(subset='species', keep='first')

        # Create mapping dictionary
        species_map = species_df.set_index('species')[['type', 'english_name']].to_dict(orient='index')

        # Map type and english_name, using lowercase for GPKG species
        gdf['species_lower'] = gdf['species'].str.strip().str.lower()
        gdf['type'] = gdf['species_lower'].map(lambda x: species_map.get(x, {}).get('type', None))
        gdf['english_name'] = gdf['species_lower'].map(lambda x: species_map.get(x, {}).get('english_name', None))

        # Identify species missing from CSV
        missing_species = sorted(set(gdf['species_lower']) - set(species_map.keys()))
        if missing_species:
            print(f"Warning: Dropping {len(missing_species)} records from {label} with species not in the species CSV list:")
            for sp in missing_species[:10]:  # print first 10 for debug
                print(f" - {sp}")
            if len(missing_species) > 10:
                print(f" - ... and {len(missing_species) - 10} more")
            
            # Drop rows with species not in the list
            gdf = gdf[gdf['species_lower'].isin(species_map.keys())]

        # Drop the temporary lowercase column
        gdf = gdf.drop(columns=['species_lower'])

    except Exception as e:
        print(f"Error updating species info: {e}")

    return gdf

# Makes a backup copy of the main GPKG before merging new data (e.g., copying the file to a backup folder with a timestamp)
def create_main_copy(main_file, backup_folder):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    name, ext = os.path.splitext(os.path.basename(main_file))
    destination = os.path.join(backup_folder, f"{name}_({timestamp}){ext}")
    with open(main_file, 'rb') as src, open(destination, 'wb') as dst:
        dst.write(src.read())
    print(f"Backup created: {destination}")

# Read a individual GPKG file (first layer) into a GeoDataFrame
def read_gpkg(gpkg_file):
    layer = fiona.listlayers(gpkg_file)[0]
    gdf = gpd.read_file(gpkg_file, layer=layer)
    return gdf

# Read all student GPKG files from the specified directory and combine them into a single GeoDataFrame (using glob to find all .gpkg files, reading each one, and concatenating them together)
def read_student_gpkgs(directory):
    combined_data = []
    for path in glob.glob(os.path.join(directory, "*.gpkg")):
        try:
            gdf = read_gpkg(path)
            combined_data.append(gdf)
            print(f"Loaded {len(gdf)} records from {os.path.basename(path)}")
        except Exception as e:
            print(f"Skipping {os.path.basename(path)}: {e}")
    if not combined_data:
        print("No valid student data found.")
        return None
    combined_gdf = pd.concat(combined_data, ignore_index=True)
    return combined_gdf

# Merge all student GeoDataFrames into the main GPKG GeoDataFrame   
def merge_collected_data(main_gdf, student_gdfs):
    if student_gdfs is None or student_gdfs.empty:
        print("No student data to merge.")
        return main_gdf
    print(f"Main data: {len(main_gdf)} records")
    print(f"Student data: {len(student_gdfs)} records")
    combined = pd.concat([main_gdf, student_gdfs], ignore_index=True)
    print(f"Combined before duplication removal: {len(combined)} records")
    return combined

# Detect and remove duplicate records from the combined GeoDataFrame 
# This helps to ensure that the main GPKG does not contain duplicate entries after merging new data from student GPKGs.
def detect_and_remove_duplicates(gdf, label="gdf"):
    if gdf is None or gdf.empty:
        return gdf
    # define uniqueness of an observation
    group_cols = ["cal_year", "month", "day", "geom", "species"]
    # groups records using the defined columns and keeps only the first occurrence to drop duplicates
    existing_cols = [col for col in group_cols if col in gdf.columns]
    before = len(gdf)

    # rounds the geom coordinates to 10 decimal places (spatial tolerance) to help with duplicate detection 
    # (e.g. if two points are very close but not exactly the same due to minor differences in coordinate precision, they will be treated as duplicates)
    if "geom" in gdf.columns:
        gdf["geom"] = gdf["geom"].apply(
            lambda g: Point(round(g.x, 10), round(g.y, 10)) if g and g.geom_type == "Point" else g
        )
    gdf = gdf.drop_duplicates(subset=existing_cols, keep="first")
    after = len(gdf)
    print(f"Removed {before - after} duplicate records from {label}")
    return gdf

# Save the updated main GeoDataFrame back to a GPKG file 
def save_main_gpkg(gdf, main_file):
    layer_name = os.path.splitext(os.path.basename(main_file))[0]
    gdf.to_file(main_file, layer=layer_name, driver="GPKG")
    print(f"Main GPKG updated: {len(gdf)} total records")
    print(f"Saved to: {main_file}")
