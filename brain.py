import glob
import os
import pandas as pd
import geopandas as gpd
import re
import fiona
from datetime import datetime

def update_observer_and_species_in_gpkg(directory, species_csv):
    """
    Updates the 'observer' column in .gpkg files using an Excel sheet and replaces
    'type' and 'english_name' based on species matching from a CSV file.

    Input:
    directory (str): Path to directory with .gpkg files and Excel sheet
    species_csv (str): Path to species CSV file

    Output:
    None (updates files in place)
    """

    # Load species mapping CSV
    species_df = pd.read_csv(species_csv, encoding='ISO-8859-1')
    species_mapping = species_df.set_index('species')[['type', 'english_name']].to_dict(orient='index')

    # Find Excel file
    excel_files = glob.glob(os.path.join(directory, "*.xlsx"))
    if not excel_files:
        print("Error: No Excel sheet found in the directory.")
        return
    excel_file = excel_files[0]

    # Read Excel data
    df = pd.read_excel(excel_file)

    id_to_name = {}
    for _, row in df.iterrows():
        links_cell = row['Upload your gpkg files here']
        name = str(row['Include your name here']).strip()
        if pd.isna(links_cell) or pd.isna(name):
            continue

        links = re.findall(r'https?://[^\s,]+', str(links_cell))
        for link in links:
            if 'id=' in link:
                file_id = link.split('id=')[1].split('&')[0]
                id_to_name[file_id] = name

    # Process each .gpkg file
    gpkg_files = glob.glob(os.path.join(directory, "*.gpkg"))

    for file_path in gpkg_files:
        file_name = os.path.basename(file_path)
        file_id = os.path.splitext(file_name)[0]

        if file_id not in id_to_name:
            print(f"Skipping {file_name}: No matching entry in Excel sheet.")
            continue

        observer_name = id_to_name[file_id]

        try:
            gdf = gpd.read_file(file_path)
        except Exception as e:
            print(f"Error reading {file_name}: {str(e)}")
            continue

        # Update observer
        if 'observer' in gdf.columns:
            gdf['observer'] = observer_name
            print(f"Updated 'observer' in {file_name}")
        else:
            print(f"Warning: {file_name} has no 'observer' column.")

        # Update type and english_name based on species
        if 'species' in gdf.columns:
            gdf['type'] = gdf['species'].map(lambda sp: species_mapping.get(sp, {}).get('type', gdf.get('type')))
            gdf['english_name'] = gdf['species'].map(lambda sp: species_mapping.get(sp, {}).get('english_name', gdf.get('english_name')))
            print(f"Updated 'type' and 'english_name' in {file_name}")
        else:
            print(f"Warning: {file_name} has no 'species' column.")

        # Save back using layer = file name (no extension)
        layer_name = file_id
        gdf.to_file(file_path, driver="GPKG", layer=layer_name)
        print(f"Saved updates to {file_name}")

def clean_geometry_and_observer(gdf):
    if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    if "observer" in gdf.columns:
        gdf = gdf.rename(columns={"observer": "obs"})
    if "geometry" in gdf.columns:
        gdf = gdf.rename(columns={"geometry": "geom"})
    gdf = gdf.set_geometry("geom")
    if "geometry" in gdf.columns:
        gdf = gdf.drop(columns="geometry")
    return gdf


def create_main_copy(filepath, destination_folder):
    """
    Create a dated copy of the main .gpkg file in a destination folder,
    Input:
    filepath (str): Path to the original .gpkg file.
    destination_folder (str): Folder where the copy should be saved.

    Output:
    None
    """
    datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    dated_filename = f"{name}_({datetime_str}){ext}"
    destination_filepath = os.path.join(destination_folder, dated_filename)

    with open(filepath, 'rb') as original_file:
        data = original_file.read()

    with open(destination_filepath, 'wb') as backup_file:
        backup_file.write(data)

    print(f"Copied original file to: {destination_filepath}")

def load_main_data(filepath):
    target_columns = [
        "geom", "Date", "species", "obs", "height", "radius", "photoid",
        "count", "year", "month", "day", "comment", "type", "english_name", "Taxa"
    ]

    layer_name = os.path.splitext(os.path.basename(filepath))[0]
    gdf = gpd.read_file(filepath, layer=layer_name)
    gdf = clean_geometry_and_observer(gdf)

    missing_columns = [col for col in target_columns if col not in gdf.columns]
    if missing_columns:
        print(f"Warning: The following required columns are missing from '{filepath}': {missing_columns}")

    print(f"Main file '{filepath}' loaded with {len(gdf)} records from layer '{layer_name}'")
    return gdf


def load_student_data(directory):
    target_columns = [
        "geom", "Date", "species", "obs", "height", "radius", "photoid",
        "count", "year", "month", "day", "comment", "type", "english_name", "Taxa"
    ]
    # Create a mapping from lowercase to canonical column name
    col_map = {col.lower(): col for col in target_columns}

    gpkg_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".gpkg")]
    combined = []

    for path in gpkg_files:
        try:
            layer_name = fiona.listlayers(path)[0]
            gdf = gpd.read_file(path, layer=layer_name)
            gdf = clean_geometry_and_observer(gdf)

            # Normalize existing column names: lowercase + remap to correct casing
            renamed_columns = {
                col: col_map[col.strip().lower()]
                for col in gdf.columns
                if col.strip().lower() in col_map
            }
            gdf = gdf.rename(columns=renamed_columns)

            # Add missing columns as None
            for col in target_columns:
                if col not in gdf.columns:
                    gdf[col] = None

            # Extract year, month, day from datetime64[ns] Date column and populate day, month, year columns
            gdf["year"] = gdf["Date"].dt.year
            gdf["month"] = gdf["Date"].dt.month
            gdf["day"] = gdf["Date"].dt.day

            # Reorder columns
            gdf = gdf[target_columns]

            combined.append(gdf)
            print(f"Student file '{path}' loaded with {len(gdf)} records from layer '{layer_name}'")

        except Exception as e:
            print(f"Skipping '{path}': {e}")

    if combined:
        combined_gdf = pd.concat(combined, ignore_index=True)

        # Drop rows with missing date in date column (e.g. null)
        before_drop = len(combined_gdf)
        combined_gdf = combined_gdf.dropna(subset=["Date"])
        after_drop = len(combined_gdf)
        print(f"Dropped {before_drop - after_drop} records with missing Date.")

        print(f"Total combined student records: {len(combined_gdf)}")
        return combined_gdf
    else:
        print("No valid student GPKG files found.")
        return None

def merge_and_update_main(main_gdf, student_gdf, output_path):
    target_columns = [
        "geom", "Date", "species", "obs", "height", "radius", "photoid",
        "count", "year", "month", "day", "comment", "type", "english_name", "Taxa"
    ]
    subset = ["geom", "species", "obs"]

    # Safety check
    for col in subset:
        if col not in main_gdf.columns or col not in student_gdf.columns:
            print(f"Error: Missing required column '{col}' in input data.")
            return

    student_gdf = student_gdf.drop_duplicates()

    def is_duplicate(row):
        return ((main_gdf[subset] == row[subset]).all(axis=1)).any()

    new_data = student_gdf[~student_gdf.apply(is_duplicate, axis=1)]

    print(f"Number of non-duplicate records: {len(new_data)}")

    if not new_data.empty:
        print(f"Appending {len(new_data)} new records to main GPKG")
        new_data = new_data[target_columns]  # ensure column order
        new_data.to_file(output_path, layer=os.path.splitext(os.path.basename(output_path))[0], driver="GPKG", mode="a")
    else:
        print("No new records to append.")


def run_pipeline(directory, species_csv, main_file, directory_copy):

    from brain import (
        update_observer_and_species_in_gpkg,
        load_main_data,
        load_student_data,
        merge_and_update_main,
    )

    # Validate Excel
    excel_files = glob.glob(os.path.join(directory, "*.xlsx"))
    if len(excel_files) != 1:
        print("Error: There must be exactly one Excel file in the directory.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: Update Gpkg Files in the Directory
    update_observer_and_species_in_gpkg(directory, species_csv)

    # Step 1.5: Create a copy of the main data
    create_main_copy(main_file, directory_copy)

    # Step 2: Find Main File
    main = load_main_data(main_file)

    # Step 3: Combine Gpkg Files in the Directory
    student = load_student_data(directory)

    # Step 4: Combine Main file and Student's File, Remove all Duplicates, and then append deduplicated data that is not
    # present in the main file to the main file
    merge_and_update_main(main, student, main_file)




