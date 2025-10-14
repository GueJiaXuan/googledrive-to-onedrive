"""
Error Handler Module
Catches and logs detailed error information including file states and data integrity
"""

import traceback
import sys
import os
import pandas as pd
import geopandas as gpd
from datetime import datetime
import glob
import fiona
import shutil


def log_error(error_message, log_file="error_log.txt"):
    """Write error message to log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"ERROR LOG - {timestamp}\n")
        f.write(f"{'='*80}\n")
        f.write(error_message)
        f.write(f"\n{'='*80}\n\n")


def copy_files_to_error_folder(directory, species_csv, main_file):
    """
    Create an error snapshot folder with copies of all files being used
    Returns the path to the error folder
    """
    # Create timestamped error folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    error_folder = f"error_snapshot_{timestamp}"
    os.makedirs(error_folder, exist_ok=True)

    info = []
    info.append(f"\n{'='*80}")
    info.append("COPYING FILES TO ERROR SNAPSHOT FOLDER")
    info.append(f"{'='*80}")
    info.append(f"Error folder: {error_folder}")

    # Copy species.csv
    if os.path.exists(species_csv):
        dest = os.path.join(error_folder, os.path.basename(species_csv))
        shutil.copy2(species_csv, dest)
        info.append(f"✓ Copied: {os.path.basename(species_csv)}")

    # Copy Excel file
    excel_files = glob.glob(os.path.join(directory, "*.xlsx"))
    for excel_file in excel_files:
        dest = os.path.join(error_folder, os.path.basename(excel_file))
        shutil.copy2(excel_file, dest)
        info.append(f"✓ Copied: {os.path.basename(excel_file)}")

    # Copy all GPKG files from directory
    gpkg_files = glob.glob(os.path.join(directory, "*.gpkg"))
    student_folder = os.path.join(error_folder, "student_files")
    os.makedirs(student_folder, exist_ok=True)
    for gpkg_file in gpkg_files:
        dest = os.path.join(student_folder, os.path.basename(gpkg_file))
        shutil.copy2(gpkg_file, dest)
        info.append(f"✓ Copied student file: {os.path.basename(gpkg_file)}")

    # Copy main GPKG file
    if os.path.exists(main_file):
        dest = os.path.join(error_folder, os.path.basename(main_file))
        shutil.copy2(main_file, dest)
        info.append(f"✓ Copied main file: {os.path.basename(main_file)}")

    info.append(f"\n✓ All files copied to: {error_folder}")
    info.append(f"   Share this entire folder for debugging")

    return error_folder, "\n".join(info)


def check_species_csv(species_csv_path):
    """Analyze species.csv for potential issues"""
    info = []
    info.append(f"\n{'='*80}")
    info.append("SPECIES CSV ANALYSIS")
    info.append(f"{'='*80}")
    info.append(f"File path: {species_csv_path}")
    info.append(f"File exists: {os.path.exists(species_csv_path)}")

    if os.path.exists(species_csv_path):
        info.append(f"File size: {os.path.getsize(species_csv_path)} bytes")
        info.append(f"Last modified: {datetime.fromtimestamp(os.path.getmtime(species_csv_path))}")

        try:
            # Try reading without stripping
            species_df = pd.read_csv(species_csv_path, encoding='ISO-8859-1')
            info.append(f"\nDataFrame loaded successfully")
            info.append(f"Total rows: {len(species_df)}")
            info.append(f"Columns: {list(species_df.columns)}")
            info.append(f"Unique species (raw): {species_df['species'].nunique()}")
            info.append(f"Duplicate species (raw): {species_df['species'].duplicated().sum()}")

            # Check with stripped values
            species_df_stripped = species_df.copy()
            species_df_stripped['species'] = species_df_stripped['species'].str.strip()
            info.append(f"\nAfter stripping whitespace:")
            info.append(f"Unique species: {species_df_stripped['species'].nunique()}")
            info.append(f"Duplicate species: {species_df_stripped['species'].duplicated().sum()}")

            if species_df_stripped['species'].duplicated().any():
                info.append(f"\n⚠️  DUPLICATE SPECIES FOUND:")
                dups = species_df_stripped[species_df_stripped['species'].duplicated(keep=False)].sort_values('species')
                info.append(dups[['species', 'type', 'english_name']].to_string())

            # Try creating the mapping (the line that fails)
            try:
                species_mapping = species_df.set_index('species')[['type', 'english_name']].to_dict(orient='index')
                info.append(f"\n✓ species_mapping created successfully (NO ERROR)")
            except ValueError as e:
                info.append(f"\n✗ ERROR creating species_mapping: {e}")
                info.append(f"\nThis is the error your professor is seeing!")

        except Exception as e:
            info.append(f"\n✗ ERROR reading CSV: {e}")
            info.append(traceback.format_exc())

    return "\n".join(info)


def check_excel_file(directory):
    """Analyze Excel file in directory"""
    info = []
    info.append(f"\n{'='*80}")
    info.append("EXCEL FILE ANALYSIS")
    info.append(f"{'='*80}")
    info.append(f"Directory: {directory}")

    excel_files = glob.glob(os.path.join(directory, "*.xlsx"))
    info.append(f"Excel files found: {len(excel_files)}")

    if excel_files:
        for excel_file in excel_files:
            info.append(f"\nFile: {os.path.basename(excel_file)}")
            info.append(f"File size: {os.path.getsize(excel_file)} bytes")
            info.append(f"Last modified: {datetime.fromtimestamp(os.path.getmtime(excel_file))}")

            try:
                df = pd.read_excel(excel_file)
                info.append(f"Rows: {len(df)}")
                info.append(f"Columns: {list(df.columns)}")
            except Exception as e:
                info.append(f"✗ ERROR reading Excel: {e}")

    return "\n".join(info)


def check_gpkg_files(directory):
    """Analyze GPKG files in directory"""
    info = []
    info.append(f"\n{'='*80}")
    info.append("GPKG FILES ANALYSIS")
    info.append(f"{'='*80}")
    info.append(f"Directory: {directory}")

    gpkg_files = glob.glob(os.path.join(directory, "*.gpkg"))
    info.append(f"GPKG files found: {len(gpkg_files)}")

    for gpkg_file in gpkg_files:
        info.append(f"\n  File: {os.path.basename(gpkg_file)}")
        info.append(f"  File size: {os.path.getsize(gpkg_file)} bytes")
        info.append(f"  Last modified: {datetime.fromtimestamp(os.path.getmtime(gpkg_file))}")

        try:
            layers = fiona.listlayers(gpkg_file)
            info.append(f"  Layers: {layers}")

            if layers:
                gdf = gpd.read_file(gpkg_file, layer=layers[0])
                info.append(f"  Rows in first layer: {len(gdf)}")
                info.append(f"  Columns: {list(gdf.columns)}")

                if 'species' in gdf.columns:
                    info.append(f"  Unique species: {gdf['species'].nunique()}")
                    info.append(f"  Species with trailing spaces: {(gdf['species'].astype(str).str.len() != gdf['species'].astype(str).str.strip().str.len()).sum()}")

        except Exception as e:
            info.append(f"  ✗ ERROR reading GPKG: {e}")

    return "\n".join(info)


def check_main_gpkg(main_file):
    """Analyze main GPKG file"""
    info = []
    info.append(f"\n{'='*80}")
    info.append("MAIN GPKG FILE ANALYSIS")
    info.append(f"{'='*80}")
    info.append(f"File path: {main_file}")
    info.append(f"File exists: {os.path.exists(main_file)}")

    if os.path.exists(main_file):
        info.append(f"File size: {os.path.getsize(main_file)} bytes")
        info.append(f"Last modified: {datetime.fromtimestamp(os.path.getmtime(main_file))}")

        try:
            layers = fiona.listlayers(main_file)
            info.append(f"Layers: {layers}")

            layer_name = os.path.splitext(os.path.basename(main_file))[0]
            info.append(f"Expected layer name: {layer_name}")

            if layer_name in layers:
                gdf = gpd.read_file(main_file, layer=layer_name)
                info.append(f"Rows: {len(gdf)}")
                info.append(f"Columns: {list(gdf.columns)}")
            else:
                info.append(f"⚠️  Expected layer '{layer_name}' not found in layers!")

        except Exception as e:
            info.append(f"✗ ERROR reading main GPKG: {e}")

    return "\n".join(info)


def diagnose_pipeline_error(directory, species_csv, main_file, directory_copy=""):
    """
    Comprehensive error diagnosis for the pipeline
    Returns a detailed error report string
    """
    report = []
    report.append(f"\n{'#'*80}")
    report.append("PIPELINE ERROR DIAGNOSIS")
    report.append(f"{'#'*80}")
    report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\nInput Parameters:")
    report.append(f"  directory: {directory}")
    report.append(f"  species_csv: {species_csv}")
    report.append(f"  main_file: {main_file}")
    report.append(f"  directory_copy: {directory_copy}")

    # Check all components
    report.append(check_species_csv(species_csv))
    report.append(check_excel_file(directory))
    report.append(check_gpkg_files(directory))
    report.append(check_main_gpkg(main_file))

    # System info
    report.append(f"\n{'='*80}")
    report.append("SYSTEM INFORMATION")
    report.append(f"{'='*80}")
    report.append(f"Python version: {sys.version}")
    report.append(f"Pandas version: {pd.__version__}")
    report.append(f"GeoPandas version: {gpd.__version__}")

    report_text = "\n".join(report)

    # Log to file
    log_error(report_text)

    return report_text


def safe_run_pipeline(directory, species_csv, main_file, directory_copy=""):
    """
    Wrapper around run_pipeline that catches and logs errors with full diagnostics
    """
    try:
        from brain import run_pipeline
        run_pipeline(directory, species_csv, main_file, directory_copy)
        print("\n✓ Pipeline completed successfully!")

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        print(f"\n✗ Pipeline failed with {error_type}: {error_msg}")
        print("\nCopying files to error snapshot folder...")

        # Copy all files to error folder
        try:
            error_folder, copy_info = copy_files_to_error_folder(directory, species_csv, main_file)
            print(copy_info)
        except Exception as copy_error:
            print(f"✗ Warning: Could not copy files: {copy_error}")
            error_folder = None
            copy_info = f"File copy failed: {copy_error}"

        print("\nGenerating diagnostic report...")

        # Generate full diagnostic report
        report = diagnose_pipeline_error(directory, species_csv, main_file, directory_copy)

        # Add file copy info
        if copy_info:
            report += "\n" + copy_info

        # Add exception details
        exception_info = []
        exception_info.append(f"\n{'='*80}")
        exception_info.append("EXCEPTION DETAILS")
        exception_info.append(f"{'='*80}")
        exception_info.append(f"Exception Type: {error_type}")
        exception_info.append(f"Exception Message: {error_msg}")
        exception_info.append(f"\nFull Traceback:")
        exception_info.append(traceback.format_exc())

        exception_text = "\n".join(exception_info)
        report += exception_text

        # Log everything
        log_error(report)

        # If we created an error folder, also save the report there
        if error_folder:
            error_report_path = os.path.join(error_folder, "error_report.txt")
            with open(error_report_path, "w") as f:
                f.write(report)
            print(f"\n✓ Error report also saved to: {error_folder}/error_report.txt")

        # Print to console
        print("\n" + report)
        print(f"\n✓ Full diagnostic report saved to: error_log.txt")
        if error_folder:
            print(f"✓ All files and report saved to: {error_folder}/")
            print(f"   ZIP and share this folder for debugging")

        # Re-raise the error so the UI still shows it
        raise


if __name__ == "__main__":
    # Test mode - run diagnostics without running pipeline
    print("Running diagnostics...")

    # Use default paths from settings.json
    import json
    if os.path.exists("settings.json"):
        with open("settings.json") as f:
            settings = json.load(f)
            directory = settings.get("onedrive_path", "")
            species_csv = settings.get("species_csv", "species.csv")
            main_file = settings.get("output_gpkg_path", "")
            directory_copy = settings.get("backup_directory", "")
    else:
        directory = input("Enter directory path: ")
        species_csv = input("Enter species CSV path: ")
        main_file = input("Enter main GPKG path: ")
        directory_copy = input("Enter backup directory (optional): ")

    report = diagnose_pipeline_error(directory, species_csv, main_file, directory_copy)
    print(report)
    print(f"\nDiagnostic report saved to: error_log.txt")
