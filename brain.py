import glob
import os
import re
import fiona
import pyogrio
import hashlib 
import pandas as pd
import geopandas as gpd
from datetime import datetime
from shapely import wkt
from shapely.geometry.base import BaseGeometry

# ==============================
# --- Constants / Configuration ---
# ==============================
# Target Columns
    # This is the master list of all columns we want in every dataset,
    # in a consistent order. Even if some columns are missing in the input files,
    # they will be added automatically.
TARGET_COLUMNS = [
    "geom",          # Location of the observation (geometry for mapping)
    "Date",          # Date of the observation
    "species",       # Observed species
    "obs",           # Name of the observer
    "height",        # Plant height (optional)
    "radius",        # Plant radius (optional)
    "photoid",       # Photo ID for any pictures taken (optional)
    "count",         # Number of plants/animals observed
    "year",          # Sampling year (May-Apr) e.g., 2025-26
    "year1",         # Calendar year (Jan-Dec) from the date
    "month",         # Month of observation
    "day",           # Day of observation
    "comment",       # Notes or comments (optional)
    "type",          # Taxonomic type from species mapping
    "english_name",  # English species name
    "Taxa"           # Taxonomic classification
]

# Flexible Column Mapping
    # Maps possible variations of column names (from different QGIS/GPKG exports)
    # to our standard names used in the pipeline.
    # This makes the code robust against minor column name changes.
COLUMN_MAPPING = {
    "observer": "obs",
    "Observer Name": "obs",
    "geometry": "geom",
    "geom": "geom",
    "species": "species",
    "Species Name": "species",
    "Date": "Date",
    "date_obs": "Date",
    "school_year": "year",
    "calendar_year": "year1",
    "type": "type",
    "english_name": "english_name",
    "height": "height",
    "radius": "radius",
    "photoid": "photoid",
    "count": "count",
    "month": "month",
    "day": "day",
    "comment": "comment",
    "Taxa": "Taxa"
}

# Text Fields
    # Columns that contain text and should be “cleaned” to avoid issues,
    # like extra spaces. For example, "oak " and "oak" would be treated the same.
TEXT_FIELDS = ["species", "obs"]

# ==============================
# --- Utility Functions ---
# ==============================
# Calculate year (sampling year) in format YYYY-YY based on non-calendar year (May 1 - April 30)
    # NOTE: This populates the "year" column (previously called "school_year")

    # Rules:
        # If month is 5-12: year = "{year}-{last_two_of_year+1}"  (e.g., 14/08/2025 -> "2025-26")
        # If month is 1-4: year = "{year-1}-{last_two_of_year}"  (e.g., 30/04/2025 -> "2024-25")

    # Returns the sampling year string (e.g., "2025-26")
def calculate_sampling_year(date):
    if pd.isna(date):
        return None
    year, month = date.year, date.month
    if month >= 5:  # May to December
        # Format: year-next_year (e.g., 2025-26)
        next_year_short = str(year + 1)[-2:]
        return f"{year}-{next_year_short}"
    else:  # January to April
        # Format: previous_year-year (e.g., 2024-25)
        year_short = str(year)[-2:]
        return f"{year - 1}-{year_short}"

# Standardize and clean a GeoDataFrame (the converted .gpkg file)
    # So all student files become consistent  
    # with the same column names, geometry column, coordinate system, date fields and column order
def standardize_gdf(gdf, target_columns=TARGET_COLUMNS):
    if gdf.empty:
        return gdf

    # Rename columns according to the flexible column mapping
    rename_dict = {col: COLUMN_MAPPING[col] for col in gdf.columns if col in COLUMN_MAPPING}
    gdf = gdf.rename(columns=rename_dict)

    # Remove duplicate columns 
    gdf = gdf.loc[:, ~gdf.columns.duplicated()]

    # Ensure valid geometry column 
    if "geom" in gdf.columns:
        # Convert geometry strings to a shapely geometry object
        gdf["geom"] = gdf["geom"].apply(lambda x: wkt.loads(str(x)) if x and not isinstance(x, BaseGeometry) else x)
        # Drop any extra geometry columns
        extra_geom_cols = [c for c in gdf.columns if isinstance(gdf[c].dtype, gpd.array.GeometryDtype) and c != "geom"]
        gdf = gdf.drop(columns=extra_geom_cols)
        # Set geometry and CRS to indicate this column contains spatial data 
        gdf = gdf.set_geometry("geom", inplace=False)
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
            # if no coordinate system exists, assume EPSG:4326 (WGS84 lat/long standard GPS system)
        elif gdf.crs.to_string() != "EPSG:4326":
            # if the CRS is different, converts it so all files use the same map projection
            gdf = gdf.to_crs("EPSG:4326")
    else:
        # If no geometry, just warn
        print("Warning: 'geom' column missing, skipping CRS assignment.")

    # Clean text fields 
    for col in TEXT_FIELDS:
        if col in gdf.columns:
            gdf[col] = gdf[col].astype(str).str.strip()

    # Fill missing columns 
    for col in target_columns:
        if col not in gdf.columns:
            gdf[col] = None

    # Standardize date fields to datetime objects
    if "Date" in gdf.columns:
        gdf["Date"] = parse_date_column(gdf["Date"])
        gdf["year1"] = gdf["Date"].dt.year
        gdf["month"] = gdf["Date"].dt.month
        gdf["day"] = gdf["Date"].dt.day
        gdf["year"] = gdf["Date"].apply(calculate_sampling_year)

    # Reorder columns 
    gdf = gdf[target_columns]

    # Drop rows with missing geometry (prevents fake new records) 
    gdf = gdf.dropna(subset=["geom"])

    return gdf

# Read species CSV and return a mapping dict for 'type' and 'english_name'.
def read_species_mapping(species_csv):
    df = pd.read_csv(species_csv, encoding="ISO-8859-1")
    df['species'] = df['species'].astype(str).str.strip()
    df = df.drop_duplicates(subset=['species'], keep='first')
    return df.set_index('species')[['type', 'english_name']].to_dict(orient='index')

# Extract {file_id: observer_name} mapping from form sheet in directory.
    # So the pipeline can automatically fill the observer column for each .gpkg 
def extract_excel_mapping(directory):
    excel_files = glob.glob(os.path.join(directory, "*.xlsx"))
    if not excel_files:
        raise FileNotFoundError("No Excel file found in directory.")
    # Read the form submission sheet 
    df = pd.read_excel(excel_files[0])
    id_to_name = {}
    for _, row in df.iterrows():
        links_cell = row.get('Upload your gpkg files here')
        name = str(row.get('Include your name here', "")).strip()
        if pd.isna(links_cell) or not name:
            continue
        # Extract Google Drive upload links from the form cell
        links = re.findall(r'https?://[^\s,]+', str(links_cell))
        for link in links:
            if 'id=' in link:
                # Extract the Google Drive file ID from the link
                file_id = link.split('id=')[1].split('&')[0]
                # Match the file ID with the student's name
                id_to_name[file_id] = name
    # Return dictionary mapping: file id to student name 
    return id_to_name

#  Safely parse a column as datetime.
    # Handles strings in multiple formats
    # Handles Excel numeric dates
def parse_date_column(col):
    # Try pandas automatic parsing first
    dt = pd.to_datetime(col, errors="coerce")
    # If all values are NaT (cannot parse date) and column is numeric, assume Excel numeric dates
    if dt.isna().all() and pd.api.types.is_numeric_dtype(col):
        dt = pd.to_datetime('1899-12-30') + pd.to_timedelta(col, unit='D')
    return dt

# Create a coordinate key for geometry, to compare locations
def geom_key(geom, precision=5):
    if geom is None:
        return None
    try:
        return f"{round(geom.x, precision)}_{round(geom.y, precision)}"
    except Exception:
        return None
        
# ==============================
# --- Core Processing Functions ---
# ==============================
# Update observer, type, and english_name fields in all GPKG files in a directory.
    # Updates the 'observer' column in .gpkg files using an Excel sheet and replaces
    # 'type' and 'english_name' based on species matching from a CSV file.

    # Input:
    # directory (str): Path to directory with .gpkg files and Excel sheet
    # species_csv (str): Path to species CSV file

    # Output:
    # None (updates files in place)
def update_observer_and_species_in_gpkg(directory, species_csv):
    species_mapping = read_species_mapping(species_csv)
    id_to_name = extract_excel_mapping(directory)
    gpkg_files = glob.glob(os.path.join(directory, "*.gpkg"))

    for path in gpkg_files:
        file_id = os.path.splitext(os.path.basename(path))[0]
        observer_name = id_to_name.get(file_id)
        if not observer_name:
            print(f"Skipping {file_id}: No observer mapping found.")
            continue

        try:
            layers = pyogrio.list_layers(path)
            layer_name = layers[0][0]  # first layer name
            gdf = gpd.read_file(path, layer=layer_name)
        except Exception as e:
            print(f"Error reading {path}: {e}")
            continue

        # Update observer & species info 
        if 'species' in gdf.columns:
            gdf['type'] = gdf['species'].map(lambda sp: species_mapping.get(sp, {}).get('type'))
            gdf['english_name'] = gdf['species'].map(lambda sp: species_mapping.get(sp, {}).get('english_name'))
        if 'observer' in gdf.columns:
            gdf['observer'] = observer_name

        # Standardize everything (geometry, text, dates, columns) 
        gdf = standardize_gdf(gdf, TARGET_COLUMNS)

        # Save safely 
        layer_name = file_id
        gdf.to_file(path, driver="GPKG", layer=layer_name)
        print(f"Updated {os.path.basename(path)} (geom safely handled)")

# Load a individual GPKG file (first layer) and standardize it.
def load_gpkg(path, target_columns=TARGET_COLUMNS):
    layer = fiona.listlayers(path)[0]
    gdf = gpd.read_file(path, layer=layer)
    return standardize_gdf(gdf, target_columns)

# Load all student GPKG files in a directory and combine them.
    # Args:
    #     directory (str): Folder containing student .gpkg files
    #     target_columns (list[str]): Columns to keep and order

    # Returns:
    #     GeoDataFrame: Combined standardized student data
def load_student_data(directory, target_columns=TARGET_COLUMNS):
    combined_data = []
    for path in glob.glob(os.path.join(directory, "*.gpkg")):
        try:
            gdf = load_gpkg(path, target_columns)
            combined_data.append(gdf)
            print(f"Loaded {len(gdf)} records from {os.path.basename(path)}")
        except Exception as e:
            print(f"Skipping {os.path.basename(path)}: {e}")

    if not combined_data:
        print("No valid student data found.")
        return None

    combined_gdf = pd.concat(combined_data, ignore_index=True)
    before_drop = len(combined_gdf)
    combined_gdf = combined_gdf.dropna(subset=["Date"])
    print(f"Dropped {before_drop - len(combined_gdf)} records with missing Date")
    print(f"Total combined student records: {len(combined_gdf)}")
    return combined_gdf

# Creates a unique hash for each observation, used for duplicate detection
    # Key fields used are species, observer, date, x coordinate and y coordinate
def row_fingerprint(row):
    values = [
        str(row.get("species", "")).strip().lower(),
        str(row.get("obs", "")).strip().lower(),
        str(row.get("Date", "")),
        str(round(row.geom.x, 5) if row.geom else ""),
        str(round(row.geom.y, 5) if row.geom else "")
    ]
    key = "|".join(values)
    return hashlib.md5(key.encode()).hexdigest()

# Duplicate detection: find records that exist in student data but not in main dataset.
def detect_new_records(main_gdf, student_gdf):
    # compute the unique hash fingerprints 
    main_gdf["fingerprint"] = main_gdf.apply(row_fingerprint, axis=1)
    student_gdf["fingerprint"] = student_gdf.apply(row_fingerprint, axis=1)

    # Check if student fingerprints already exist in main dataset 
    new_records = student_gdf[~student_gdf["fingerprint"].isin(main_gdf["fingerprint"])].copy()

    # Returns rows in student_gdf that are not in main_gdf.
    main_gdf.drop(columns=["fingerprint"], inplace=True)
    student_gdf.drop(columns=["fingerprint"], inplace=True)
    return new_records

#  Merge student data into main GPKG, remove duplicates, and save updated main file.
def merge_and_update_main(main_gdf, student_gdf, output_path, target_columns=TARGET_COLUMNS):
    if student_gdf is None or student_gdf.empty:
        print("No student data to merge.")
        return

    # Detect new records
    new_records = detect_new_records(main_gdf, student_gdf)
    print(f"New student records to merge: {len(new_records)}")

    # DEBUG: show the records that are being treated as new
    if len(new_records) > 0:
        print("DEBUG – records considered new:")
        print(new_records[["species", "obs", "geom"]])
        
    # Merge
    if not new_records.empty:
        combined_gdf = pd.concat([main_gdf, new_records], ignore_index=True)
    else:
        combined_gdf = main_gdf.copy()

    # Ensure all target columns exist
    for col in target_columns:
        if col not in combined_gdf.columns:
            combined_gdf[col] = None

    # Re-validate date columns 
    if "Date" in combined_gdf.columns:
        combined_gdf["Date"] = parse_date_column(combined_gdf["Date"])
        combined_gdf["year1"] = combined_gdf["Date"].dt.year
        combined_gdf["month"] = combined_gdf["Date"].dt.month
        combined_gdf["day"] = combined_gdf["Date"].dt.day
        combined_gdf["year"] = combined_gdf["Date"].apply(calculate_sampling_year)

    # Reorder columns
    combined_gdf = combined_gdf[target_columns]

    # Save updated GPKG
    layer_name = os.path.splitext(os.path.basename(output_path))[0]
    combined_gdf.to_file(output_path, layer=layer_name, driver="GPKG")
    print(f"Main GPKG updated: {len(combined_gdf)} total records")

# Create a dated copy of the main .gpkg file in a destination folder
    # Input:
    # - filepath (str): Path to the original .gpkg file.
    # - destination_folder (str): Folder where the copy should be saved.
def create_main_copy(filepath, destination_folder):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    name, ext = os.path.splitext(os.path.basename(filepath))
    destination = os.path.join(destination_folder, f"{name}_({timestamp}){ext}")
    with open(filepath, 'rb') as src, open(destination, 'wb') as dst:
        dst.write(src.read())
    print(f"Backup created: {destination}")


# ==============================
# --- Pipeline ---
# ==============================
# Full pipeline: update GPKGs, backup main file, merge student data.
def run_pipeline(directory, species_csv, main_file, backup_folder):
    try:
        update_observer_and_species_in_gpkg(directory, species_csv)
        create_main_copy(main_file, backup_folder)
        main_gdf = standardize_gdf(load_gpkg(main_file), TARGET_COLUMNS)
        student_gdf = standardize_gdf(load_student_data(directory), TARGET_COLUMNS)
        merge_and_update_main(main_gdf, student_gdf, main_file)
    except Exception as e:
        print(f"Pipeline failed: {e}")