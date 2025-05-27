import glob
import os
import pandas as pd
import geopandas as gpd
import re
import fiona
from datetime import datetime


# def get_last_timestamp_from_log(directory = ""):
#     """
#     Retrieves the last (most recent) timestamp from log.xlsx in the directory.
#
#     Input:
#     directory (str): Path to directory containing log.xlsx
#
#     Output:
#     str or None: Last timestamp as a string, or None if no log or no timestamps found
#     """
#     log_path = os.path.join(directory, "log.xlsx")
#
#     if not os.path.exists(log_path):
#         print("No log.xlsx file found.")
#         return None
#
#     try:
#         log_df = pd.read_excel(log_path)
#         if 'timestamp' not in log_df.columns or log_df.empty:
#             print("log.xlsx has no 'timestamp' column or is empty.")
#             return None
#         last_timestamp = log_df['timestamp'].iloc[-1]
#         return str(last_timestamp)
#     except Exception as e:
#         print(f"Error reading log.xlsx: {str(e)}")
#         return None

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
    # Get last timestamp from log
    #last_logged_timestamp = get_last_timestamp_from_log(directory)
    # if last_logged_timestamp:
    #     print(f"Filtering Excel rows newer than last log timestamp: {last_logged_timestamp}")
    # else:
    #     print("No previous log timestamp found. Processing all Excel rows.")

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

    # # Ensure Excel has a 'timestamp' column (adjust this to your actual column name)
    # if 'timestamp' not in df.columns:
    #     print("Error: Excel file has no 'timestamp' column.")
    #     return
    #
    # # Convert Excel timestamp column to datetime
    # df['timestamp'] = pd.to_datetime(df['timestamp'])
    #
    # # Filter rows newer than last logged timestamp
    # if last_logged_timestamp:
    #     df = df[df['timestamp'] > last_logged_timestamp]
    #
    # if df.empty:
    #     print("No new Excel rows found after last logged timestamp.")
    #     return

    # Build mapping: file_id → observer name
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

def merge_gpkg_files(input_dir, output_file):
    """
    Merges .gpkg files from a directory, using only the layer matching the file name, and saves as a new .gpkg.

    Input:
    input_dir (str): Path to the directory containing .gpkg files
    output_file (str): Path to the output .gpkg file

    Output:
    None (saves merged file)
    """
    # Get all .gpkg files in the directory
    gpkg_files = glob.glob(os.path.join(input_dir, "*.gpkg"))

    if not gpkg_files:
        print(f"No .gpkg files found in {input_dir}")
        return

    print(f"Found {len(gpkg_files)} .gpkg files in {input_dir}")

    # List to store all geodataframes
    all_gdf = []

    # Read each .gpkg file using the layer that matches the file name (without extension)
    for file in gpkg_files:
        file_name = os.path.basename(file)
        layer_name = os.path.splitext(file_name)[0]

        try:
            layers = fiona.listlayers(file)
            if layer_name not in layers:
                print(f"Warning: {file} does not have a layer named '{layer_name}'. Skipping.")
                continue

            print(f"Reading {file}, layer '{layer_name}'...")
            gdf = gpd.read_file(file, layer=layer_name)

            target_crs = "EPSG:4326"
            if gdf.crs and gdf.crs.to_string() != target_crs:
                print(f"Reprojecting {file} from {gdf.crs} to {target_crs}")
                gdf = gdf.to_crs(target_crs)

            all_gdf.append(gdf)
            print(f"Successfully read {file}, layer '{layer_name}' with {len(gdf)} features")

        except Exception as e:
            print(f"Error reading {file}: {str(e)}")

    if not all_gdf:
        print("No data was read from the files")
        return

    # Concatenate all geodataframes
    print("Merging all files...")
    merged_gdf = pd.concat(all_gdf, ignore_index=True)

    # Save to a new file
    print(f"Saving merged data to {output_file}...")
    merged_gdf.to_file(output_file, driver="GPKG")

    print(f"Successfully created {output_file} with {len(merged_gdf)} features")

def remove_duplicates_from_gpkg(input_file, output_dir):
    """
    Removes duplicate records from a GeoPackage file and saves the result to a new file.

    Input:
    input_file (str): Path to the input .gpkg file
    output_file (str, optional): Path to the output .gpkg file. Defaults to input_file + '_no_duplicates'
    subset (list, optional): Columns to check for duplicates. Defaults to all columns.

    Output:
    bool: True if successful, False otherwise
    """
    if output_dir:
        os.makedirs(os.path.dirname(output_dir), exist_ok=True)

    try:
        print(f"Reading {input_file}...")
        gdf = gpd.read_file(input_file)
        original_count = len(gdf)
        print(f"Successfully read {input_file} with {original_count} features")

        if output_dir and os.path.exists(output_dir):
            df_extra = gpd.read_file(output_dir)
            print(f"Read {len(df_extra)} features from {output_dir}")

            target_crs = "EPSG:4326"

            if df_extra.crs and df_extra.crs.to_string() != target_crs:
                print(f"Reprojecting output file from {df_extra.crs} to {target_crs}")
                df_extra = df_extra.to_crs(target_crs)

            # Combine the data
            df = pd.concat([gdf, df_extra], ignore_index=True)
            print(f"Combined total: {len(df)} features")

        # Remove duplicates
        print("Removing duplicates...")
        gdf_no_duplicates = gdf.drop_duplicates(subset=['geometry', 'species', 'observer'])

        #gdf_no_duplicates = gdf.drop_duplicates(subset=subset, keep='first')
        removed_count = original_count - len(gdf_no_duplicates)

        # Save to a new file
        print(f"Saving data without duplicates to {output_dir}...")
        gdf_no_duplicates.to_file(output_dir, driver="GPKG")

        print(f"Successfully created {output_dir} with {len(gdf_no_duplicates)} features")
        print(f"Removed {removed_count} duplicate features")

        return True
    except Exception as e:
        print(f"Error processing {input_file}: {str(e)}")
        return False

def update_excel_log(directory, timestamp, files_processed, total_merged, final_saved, note):
    """
    Update or create an Excel log file to record processing summary.

    Input:
    directory (str): Path to directory
    timestamp (str): Timestamp string (same format as Excel sheet)
    files_processed (int): Number of gpkg files processed
    total_merged (int): Number of gpkg rows merged
    final_saved (int): Number of gpkg rows saved after deduplication
    note (str): Additional note or message
    """
    log_path = os.path.join(os.path.dirname(directory), "log.xlsx")
    log_columns = ['timestamp', 'files_processed', 'total_gpkg_rows_merged', 'final_rows_saved', 'note']

    # Prepare new log row
    new_log = pd.DataFrame([{
        'timestamp': timestamp,
        'files_processed': files_processed,
        'total_gpkg_rows_merged': total_merged,
        'final_rows_saved': final_saved,
        'note': note
    }])

    # If log exists, append; otherwise create
    if os.path.exists(log_path):
        existing_log = pd.read_excel(log_path)
        updated_log = pd.concat([existing_log, new_log], ignore_index=True)
    else:
        updated_log = new_log

    updated_log.to_excel(log_path, index=False)
    print(f"Updated {log_path}")

def run_pipeline(directory, species_csv, output_gpkg_path, output_merged="final.gpkg", log_note="Run completed"):
    """
    Executes the full processing pipeline:
    1. Updates GPKG files using Excel and species CSV
    2. Merges all GPKG layers
    3. Removes duplicates from merged file and saves output to specified directory
    4. Logs summary to Excel

    Input:
    directory (str): Path to input directory with .gpkg and .xlsx files
    species_csv (str): Path to species mapping CSV
    output_dir (str): Directory to save the merged and deduplicated output GPKG files
    output_merged (str, optional): Output filename for merged GPKG. Defaults to "final.gpkg"
    output_dedup (str, optional): Output filename for deduplicated GPKG. Defaults to "final_no_duplicates.gpkg"
    log_note (str, optional): Note to include in the log entry. Defaults to "Run completed"

    Output:
    None
    """
    from brain import (
        update_observer_and_species_in_gpkg,
        merge_gpkg_files,
        remove_duplicates_from_gpkg,
        update_excel_log,
    )

    # Validate Excel
    excel_files = glob.glob(os.path.join(directory, "*.xlsx"))
    if len(excel_files) != 1:
        print("Error: There must be exactly one Excel file in the directory.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: Update gpkg files
    update_observer_and_species_in_gpkg(directory, species_csv)

    # Step 2: Merge updated files
    merge_gpkg_files(directory, output_merged)

    # Step 3: Remove duplicates
    remove_duplicates_from_gpkg(output_merged, output_dir=output_gpkg_path)

    # Step 4: Summarise stats
    gpkg_files = glob.glob(os.path.join(directory, "*.gpkg"))
    files_processed = len(gpkg_files)
    merged_gdf = gpd.read_file(output_merged)
    total_merged = len(merged_gdf)
    final_gdf = gpd.read_file(output_gpkg_path)
    final_saved = len(final_gdf)

    # Step 5: Log results
    update_excel_log(
        output_gpkg_path,
        timestamp,
        files_processed,
        total_merged,
        final_saved,
        note=log_note
    )


# if __name__ == "__main__":
#     directory = "second_test"
#     species_csv = "species.csv"
#
#     #Auto-detect the Excel filename
#     excel_files = glob.glob(os.path.join(directory, "*.xlsx"))
#     if len(excel_files) != 1:
#         print("Error: There must be exactly one Excel file in the directory.")
#         exit(1)
#     excel_filename = os.path.basename(excel_files[0])
#
#     from datetime import datetime
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#
#     update_observer_and_species_in_gpkg(directory, species_csv)
#     merge_gpkg_files(directory, "final.gpkg")
#     remove_duplicates_from_gpkg("final.gpkg", "final_no_duplicates.gpkg")
#
#     # Collect summary numbers
#     gpkg_files = glob.glob(os.path.join(directory, "*.gpkg"))
#     files_processed = len(gpkg_files)
#     merged_gdf = gpd.read_file("final.gpkg")
#     total_merged = len(merged_gdf)
#     final_gdf = gpd.read_file("final_no_duplicates.gpkg")
#     final_saved = len(final_gdf)
#
#     # Write to Excel log
#     update_excel_log("", timestamp, files_processed, total_merged, final_saved, note="Run completed")
