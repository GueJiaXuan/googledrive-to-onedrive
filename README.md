# GPKG Data Collection & Processing Tool

This tool automates the process of:
- Downloading `.gpkg` (GeoPackage) files from a shared **Google Drive** folder
- Matching them with metadata from an **Excel form**
- Updating species and observer fields using a **species list CSV**
- Merging and deduplicating the data
- Saving the clean result to a specified **OneDrive** folder

## Requirements

For Microsoft Users: Please make sure you download Python from Microsoft Store NOT directly from Python site.

Before starting, make sure:
- You have Python installed (version 3.9 or later is recommended)
- Your computer has internet access
- Download this set of code into your preferred directory
- You’ve installed the required Python packages (see below)

### 🛠️ Installation (2 Options)

**Double-click `initial_run.bat`**  
   This installs the necessary packages for windows user.

**Double-click `initial_run.sh`**  
   This installs the necessary packages for mac user.

3. Place the following in a folder on your computer:
   - All `.py` files (`main.py`, `brain.py`, `GoogleDriveAuthDownload.py`)
   - The two `.bat` files: `initial_run.bat` and `run.bat`
   - Your `credentials_biodiversity.json` file for Google Drive access
   - Your `species.csv` file (mapping species to English names and types)
   - A logo image file named `school_logo.png` (optional)

## Getting Started

1. **Double-click `run.bat`**  
   This opens the main window.

2. **In the app window**, fill in:
   - **Google Drive Folder ID**: Copy the string from your Google Drive sharing link (e.g., the part after `folders/`)
   - **Downloaded Folder Path**: Where downloaded `.gpkg` files will be saved (this can be a OneDrive folder)
   - **Select species.csv file**: Browse to your species mapping CSV file
   - **Select Main.Gpkg File**: This is where the final, clean GeoPackage file will be saved

3. **Click “Download Files”**  
   This downloads all `.gpkg` files from the shared Google Drive.
   Note: A json file containing credentials must be in the same directory as the program files. Contact me for more information regarding this.

5. **Click “Run GPKG Processing Pipeline”**  
   This updates all the `.gpkg` files based on the Excel sheet and species CSV, merges them, removes duplicates, and saves the final file.

6. (Optional) **Click “Delete All Files in the Google Folder”**  
   This will delete all `.gpkg` files from the Google Drive folder to avoid duplicates on the next upload cycle.

## Files Overview

| File | Purpose |
|------|---------|
| `main.py` | Launches the user interface and handles app logic |
| `brain.py` | Updates `.gpkg` files, merges and deduplicates them |
| `GoogleDriveAuthDownload.py` | Authenticates with Google Drive and handles file download/delete |
| `initial_run.bat` | Opens the app (same as running `main.py`) |
| `run.bat` | Reserved for automation or alternate entry point |
| `settings.json` | Remembers your last-used inputs |
| `log.xlsx` | Automatically created to record each run's details |

## Tips

- The tool automatically remembers your last entries.

## First-Time Setup (Google Drive Access)

The first time you run this, a browser window will open asking you to sign in with your Google account. Grant access so the app can read your shared folder.

## Troubleshooting

- If you see **authentication errors**, delete the `token.pickle` file and restart the program.
- If the window closes immediately, try running `initial_run.bat` to see error messages.
