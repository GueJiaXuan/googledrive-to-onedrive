#!/usr/bin/env python3
"""
Diagnostic Script for Pipeline Errors
Run this BEFORE running the full pipeline to check for issues
"""

import json
import os
from error_handler import diagnose_pipeline_error

print("="*80)
print("PIPELINE DIAGNOSTIC TOOL")
print("="*80)
print("\nThis script will check your files for potential issues WITHOUT running")
print("the full pipeline. It will generate a detailed report in error_log.txt")
print()

# Try to load settings from settings.json
if os.path.exists("settings.json"):
    print("✓ Found settings.json")
    with open("settings.json") as f:
        settings = json.load(f)
        directory = settings.get("onedrive_path", "")
        species_csv = settings.get("species_csv", "species.csv")
        main_file = settings.get("output_gpkg_path", "")
        directory_copy = settings.get("backup_directory", "")

    print(f"\nSettings loaded:")
    print(f"  Directory: {directory}")
    print(f"  Species CSV: {species_csv}")
    print(f"  Main GPKG: {main_file}")
    print(f"  Backup Directory: {directory_copy}")
    print()

else:
    print("✗ settings.json not found. Please enter paths manually:")
    directory = input("Enter directory path with student GPKG files: ")
    species_csv = input("Enter species CSV path: ")
    main_file = input("Enter main GPKG file path: ")
    directory_copy = input("Enter backup directory (optional, press Enter to skip): ")

print("\n" + "="*80)
print("Running diagnostics...")
print("="*80)

# Run full diagnostics
report = diagnose_pipeline_error(directory, species_csv, main_file, directory_copy)

# Display report
print(report)

print("\n" + "="*80)
print("DIAGNOSTIC COMPLETE")
print("="*80)
print(f"\n✓ Full report saved to: error_log.txt")
print("\nIf you see any ✗ ERROR or ⚠️ WARNING messages above, those are likely")
print("the cause of the pipeline failure.")
print("\nShare error_log.txt with your developer for help.")
