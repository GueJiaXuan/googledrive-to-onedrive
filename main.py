import tkinter as tk
from tkinter import PhotoImage  # Required for displaying images
from GoogleDriveAuthDownload import auth, delete_all_files_in_folder
from brain import run_pipeline
import json
import os
SETTINGS_FILE = "settings.json"

# Define entry widgets with the settings.json file
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            entry1.delete(0, tk.END)
            entry1.insert(0, settings.get("google_folder_id", ""))
            entry2.delete(0, tk.END)
            entry2.insert(0, settings.get("onedrive_path", ""))
            entry3.delete(0, tk.END)
            entry3.insert(0, settings.get("species_csv", ""))
            entry4.delete(0, tk.END)
            entry4.insert(0, settings.get("output_gpkg_path", ""))

def save_settings():
    settings = {
        "google_folder_id": entry1.get(),
        "onedrive_path": entry2.get(),
        "species_csv": entry3.get(),
        "output_gpkg_path": entry4.get()
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def make_flagged_window():
    """
    Sets up a window with specific configuration such as keeping it on top,
    disabling resizing, and centering it to occupy 40% of the screen dimensions
    both horizontally and vertically.

    By computing 40% screen dimensions, this function ensures that the created
    window is neither too large nor too small. The positioning centers the
    window on the screen for better visibility.
    """

    # 2) Flag: disable resizing, so geometry is respected
    # root.resizable(False, False)
    #root.attributes("-topmost", 1)  # Set window as topmost initially
    root.lift()
    root.focus_force()  # Also give it keyboard focus

    # This is important - update the window to ensure it appears
    # before continuing with other code
    root.update()


    # 3) Compute 40% dimensions
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w = int(screen_w * 0.6)
    win_h = int(screen_h * 1)

    # 4) Center offsets
    x = (screen_w - win_w) // 2
    y = (screen_h - win_h) // 2

    # 5) Apply size & position
    root.geometry(f'{win_w}x{win_h}+{x}+{y}')

# Title

root = tk.Tk()
root.title("Google Drive Files Download")

# Create a separate frame for the logo at the top
logo_frame = tk.Frame(root, bg="white")
logo_frame.pack(fill=tk.BOTH, pady=10)

# Display school_logo.png inside the logo frame
logo = PhotoImage(file="school_logo.png")
logo_label = tk.Label(logo_frame, image=logo, bg="white")
logo_label.pack(anchor="center")  # Centered within the logo frame

# Delay flags + sizing until window is realized
root.after(0, make_flagged_window)

# First Frame (Google Drive Folder ID)
frame1 = tk.Frame(root)
frame1.pack(fill=tk.X, pady=(10, 0), padx=20)

# Label (Google Drive Folder ID)
label1 = tk.Label(frame1, text="Google Drive Folder ID:", font=("Helvetica", 14))
label1.grid(row=0, column=0, padx=(0, 10))
entry1 = tk.Entry(frame1, font=("Helvetica", 14))
entry1.grid(row=0, column=1, sticky="ew")
frame1.columnconfigure(1, weight=1)

# Second Frame (Downloaded Folder Path. e.g. OneDrive folder path)
frame2 = tk.Frame(root)
frame2.pack(fill=tk.X, pady=(10, 0), padx=20)

# Label (Downloaded Folder Path. e.g. OneDrive folder path)
label2 = tk.Label(frame2, text="Downloaded Folder Path:", font=("Helvetica", 14))
label2.grid(row=0, column=0, padx=(0, 10))
entry2 = tk.Entry(frame2, font=("Helvetica", 14))
entry2.grid(row=0, column=1, sticky="ew")
frame2.columnconfigure(1, weight=1)

# Extra Logic and button for browsing (Downloaded Folder Path. e.g. OneDrive folder path)
def select_directory():
    """
    Basically chooses a directory to download to.
    """
    from tkinter import filedialog
    selected_dir = filedialog.askdirectory(title="Select Directory", parent=root)
    if selected_dir:
        entry2.delete(0, tk.END)
        entry2.insert(0, selected_dir)


browse_button = tk.Button(
    frame2,
    text="...",
    font=("Helvetica", 12),
    command=select_directory,
    width=3,
    height=1,
    relief="raised",
    activebackground="#d9d9d9"
)
browse_button.grid(row=0, column=2, padx=(10, 0))

# Logic and button for First and Second Frame (Google Drive Folder ID to Downloaded Folder Path. e.g. OneDrive folder path)
def submit():
    """
    Logic that takes the first frame, which is the Google Drive folder ID,
    and downloads the files in the downloaded folder path
    :return: NIL
    """
    import sys

    class TextRedirector:
        """Redirects stdout to a text widget for live updates."""

        def __init__(self, text_widget):
            self.text_widget = text_widget

        def write(self, content):
            self.text_widget.configure(state=tk.NORMAL)
            self.text_widget.insert(tk.END, content)
            self.text_widget.configure(state=tk.DISABLED)
            self.text_widget.see(tk.END)

        def flush(self):
            pass  # Required method for file-like objects

    # Redirect stdout to the text widget
    old_stdout = sys.stdout
    sys.stdout = TextRedirector(output_text)

    try:
        auth(entry1.get(), entry2.get())  # Call auth with entered values
    finally:
        sys.stdout = old_stdout  # Restore original stdout

button = tk.Button(
    root,
    text="Download Files",
    font=("Helvetica", 12),  # Match the font size to "Browse"
    command=submit,
    height=2,
    relief="raised",
    activebackground="#d9d9d9"
)
button.pack(pady=20)

# Third Frame (for species.csv folder)
frame3 = tk.Frame(root)
frame3.pack(fill=tk.X, pady=(10, 0), padx=20)

# Third Label (for species.csv file)
label3 = tk.Label(frame3, text="Select species.csv file:", font=("Helvetica", 14))
label3.grid(row=0, column=0, padx=(0, 10))
entry3 = tk.Entry(frame3, font=("Helvetica", 14))
entry3.grid(row=0, column=1, sticky="ew")
frame3.columnconfigure(1, weight=1)

# Logic and button for Third Label (species.csv file)
def select_species_csv_file():
    from tkinter import filedialog
    selected_file = filedialog.askopenfilename(
        title="Select species.csv file",
        parent=root,
        filetypes=[("CSV Files", "*.csv")]
    )
    if selected_file:
        entry3.delete(0, tk.END)
        entry3.insert(0, selected_file)

browse_species_button = tk.Button(
    frame3,
    text="...",
    font=("Helvetica", 12),
    command=select_species_csv_file,
    width=3,
    height=1,
    relief="raised",
    activebackground="#d9d9d9"
)
browse_species_button.grid(row=0, column=2, padx=(10, 0))


# Fourth Frame (for saving output directory, aka selecting the main gpkg file)
frame4 = tk.Frame(root)
frame4.pack(fill=tk.X, pady=(10, 0), padx=20)

label4 = tk.Label(frame4, text="Select Main.Gpkg File", font=("Helvetica", 14))
label4.grid(row=0, column=0, padx=(0, 10))

entry4 = tk.Entry(frame4, font=("Helvetica", 14))
entry4.grid(row=0, column=1, sticky="ew")
frame4.columnconfigure(1, weight=1)

# Fourth Frame (for saving output directory, aka selecting the main gpkg file)
frame5 = tk.Frame(root)
frame5.pack(fill=tk.X, pady=(10, 0), padx=20)

label5 = tk.Label(frame5, text="Directory to save original copy of main.gpkg", font=("Helvetica", 14))
label5.grid(row=0, column=0, padx=(0, 10))

entry5 = tk.Entry(frame5, font=("Helvetica", 14))
entry5.grid(row=0, column=1, sticky="ew")
frame5.columnconfigure(1, weight=1)


# Logic and button to select the output file (for saving output directory, aka selecting the main gpkg file)
def select_output_file():
    from tkinter import filedialog
    selected_file = filedialog.askopenfilename(
        title="Select .gpkg File",
        parent=root,
        filetypes=[("GeoPackage", "*.gpkg")]
    )
    if selected_file:
        entry4.delete(0, tk.END)
        entry4.insert(0, selected_file)

browse_output_button = tk.Button(
    frame4,
    text="...",
    font=("Helvetica", 12),
    command=select_output_file,
    width=3,
    height=1,
    relief="raised",
    activebackground="#d9d9d9"
)
browse_output_button.grid(row=0, column=2, padx=(10, 0))

# Logic and button to select directory where the copied file is being saved to
def select_backup_directory():
    from tkinter import filedialog
    selected_directory = filedialog.askdirectory(
        title="Select Directory to Save Copy",
        parent=root
    )
    if selected_directory:
        entry5.delete(0, tk.END)
        entry5.insert(0, selected_directory)

browse_backup_button = tk.Button(
    frame5,
    text="...",
    font=("Helvetica", 12),
    command=select_backup_directory,
    width=3,
    height=1,
    relief="raised",
    activebackground="#d9d9d9"
)
browse_backup_button.grid(row=0, column=2, padx=(10, 0))


# Logic for running the GPKG Processing Pipeline
def run_pipeline_ui():
    import sys

    class TextRedirector:
        def __init__(self, text_widget):
            self.text_widget = text_widget

        def write(self, content):
            self.text_widget.configure(state=tk.NORMAL)
            self.text_widget.insert(tk.END, content)
            self.text_widget.configure(state=tk.DISABLED)
            self.text_widget.see(tk.END)

        def flush(self):
            pass

    old_stdout = sys.stdout
    sys.stdout = TextRedirector(output_text)

    try:
        gpkg_dir = entry2.get()
        species_csv_path = entry3.get()
        output_gpkg_path = entry4.get()
        directory_copy = entry5.get()

        run_pipeline(gpkg_dir, species_csv_path, output_gpkg_path, directory_copy)
    except Exception as e:
        print(f"Pipeline error: {e}")
    finally:
        sys.stdout = old_stdout

    # save current entry inputs to json file
    save_settings()

pipeline_button = tk.Button(
    root,
    text="Run GPKG Processing Pipeline",
    font=("Helvetica", 12),
    command=run_pipeline_ui,
    height=2,
    relief="raised",
    activebackground="#d9d9d9"
)
pipeline_button.pack(pady=10)

# Logic and Button for deleting google drive files (specifically gpkg files in OneDrive)
def delete_files():
    import sys

    class TextRedirector:
        """Redirects stdout to a text widget for live updates."""

        def __init__(self, text_widget):
            self.text_widget = text_widget

        def write(self, content):
            self.text_widget.configure(state=tk.NORMAL)
            self.text_widget.insert(tk.END, content)
            self.text_widget.configure(state=tk.DISABLED)
            self.text_widget.see(tk.END)

        def flush(self):
            pass  # Required method for file-like objects

    # Redirect stdout to the text widget
    old_stdout = sys.stdout
    sys.stdout = TextRedirector(output_text)

    try:
        print(f"Attempting to delete all files in folder in the Google Folder")
        delete_all_files_in_folder(entry1.get())  # Call delete_all_files_in_folder with entered folder ID
        #print("All files deleted successfully.")
    except Exception as e:
        print(f"An error occurred while deleting files: {e}")
    finally:
        sys.stdout = old_stdout  # Restore original stdout


delete_button = tk.Button(
    root,
    text="Delete All Files in the Google Folder",
    font=("Helvetica", 12),
    command=delete_files,
    width=30,
    height=2,
    relief="raised",
    activebackground="#d9d9d9"
)
delete_button.pack(pady=10)

# Add a text widget to display the logs/output from the auth function
output_text = tk.Text(root, font=("Helvetica", 12), wrap=tk.WORD, height=10)
output_text.configure(state=tk.DISABLED)
output_text.pack(fill=tk.BOTH, expand=True, pady=10, padx=20)

# Fill in entry widget inputs
load_settings()

# Run the program
root.mainloop()



