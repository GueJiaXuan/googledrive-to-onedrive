"""
Biodiversity Mapping - QField File Processing Application

A desktop application for managing biodiversity data collection workflows,
including Google Drive integration, GPKG file processing, and data merging.

Author: Biodiversity Mapping Team
Version: 1.0
"""

# ============================================================================
# IMPORTS
# ============================================================================

import tkinter as tk
from tkinter import ttk, PhotoImage, filedialog
import json
import os
import sys

from GoogleDriveAuthDownload import auth, delete_all_files_in_folder


# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

SETTINGS_FILE = "settings.json"

# Application window configuration
WINDOW_WIDTH_RATIO = 0.7
WINDOW_HEIGHT_RATIO = 0.9
MAX_WINDOW_WIDTH = 1000
MAX_WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600

# Image scaling
IMAGE_SCALE_FACTOR = 2  # Subsample by 2 = half the original size

# Color scheme - Dark Theme
COLORS = {
    'primary': '#4CAF50',           # Green
    'primary_hover': '#66BB6A',     # Lighter green
    'secondary': '#42A5F5',         # Blue
    'secondary_hover': '#64B5F6',   # Lighter blue
    'danger': '#EF5350',            # Red
    'danger_hover': '#F44336',      # Brighter red
    'bg': '#1E1E1E',                # Dark background
    'card_bg': '#2D2D2D',           # Dark card background
    'text': '#E0E0E0',              # Light text
    'text_secondary': '#B0B0B0',    # Secondary light text
    'border': '#404040',            # Dark border
    'input_bg': '#383838',          # Input field background
    'input_text': '#FFFFFF'         # Input text color
}


# ============================================================================
# UTILITY CLASSES
# ============================================================================

class TextRedirector:
    """Redirects stdout to a tkinter Text widget for real-time output display."""

    def __init__(self, text_widget):
        """
        Initialize the text redirector.

        Args:
            text_widget: tkinter Text widget to redirect output to
        """
        self.text_widget = text_widget

    def write(self, content):
        """Write content to the text widget."""
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.insert(tk.END, content)
        self.text_widget.configure(state=tk.DISABLED)
        self.text_widget.see(tk.END)

    def flush(self):
        """Flush method required for file-like objects."""
        pass


# ============================================================================
# SETTINGS MANAGEMENT
# ============================================================================

def load_settings():
    """Load saved settings from JSON file and populate input fields."""
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
            entry5.delete(0, tk.END)
            entry5.insert(0, settings.get("backup_directory", ""))


def save_settings():
    """Save current input field values to JSON file."""
    settings = {
        "google_folder_id": entry1.get(),
        "onedrive_path": entry2.get(),
        "species_csv": entry3.get(),
        "output_gpkg_path": entry4.get(),
        "backup_directory": entry5.get()
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ============================================================================
# UI COMPONENT FACTORIES
# ============================================================================

def create_styled_button(parent, text, command, color='primary', width=None):
    """
    Create a styled button with hover effects.

    Args:
        parent: Parent widget
        text: Button text
        command: Function to call when clicked
        color: Color theme ('primary', 'secondary', or 'danger')
        width: Optional fixed width

    Returns:
        Frame containing the styled button
    """
    btn_frame = tk.Frame(parent, bg=COLORS[color], bd=0, relief=tk.FLAT)

    btn = tk.Button(
        btn_frame,
        text=text,
        command=command,
        font=("Segoe UI", 13, "bold"),
        bg=COLORS[color],
        fg="#000000",
        bd=0,
        padx=25,
        pady=12,
        cursor="hand2",
        activebackground=COLORS[f'{color}_hover'],
        activeforeground="#000000"
    )

    if width:
        btn.config(width=width)

    btn.pack(padx=2, pady=2)

    # Hover effects
    def on_enter(e):
        btn.config(bg=COLORS[f'{color}_hover'])

    def on_leave(e):
        btn.config(bg=COLORS[color])

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)

    return btn_frame


def create_input_row(parent, label_text, browse_command=None, file_type=None):
    """
    Create a consistent input row with label, entry, and optional browse button.

    Args:
        parent: Parent widget
        label_text: Text for the label
        browse_command: Optional command for browse button
        file_type: Not currently used, reserved for future file type filtering

    Returns:
        Entry widget for accessing the input value
    """
    frame = tk.Frame(parent, bg=COLORS['card_bg'])
    frame.pack(fill=tk.X, pady=8, padx=20)

    # Label
    label = tk.Label(
        frame,
        text=label_text,
        font=("Segoe UI", 10),
        bg=COLORS['card_bg'],
        fg=COLORS['text'],
        anchor="w",
        width=20  # Fixed width for consistent alignment
    )
    label.pack(side=tk.LEFT, padx=(0, 15))

    # Entry field
    entry = tk.Entry(
        frame,
        font=("Segoe UI", 10),
        bg=COLORS['input_bg'],
        fg=COLORS['input_text'],
        relief=tk.SOLID,
        bd=1,
        highlightthickness=1,
        highlightcolor=COLORS['primary'],
        highlightbackground=COLORS['border'],
        insertbackground=COLORS['input_text']
    )
    entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Browse button (optional)
    if browse_command:
        browse_btn = tk.Button(
            frame,
            text="Browse...",
            command=browse_command,
            font=("Segoe UI", 9),
            bg=COLORS['card_bg'],
            fg=COLORS['text'],
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=5,
            cursor="hand2",
            activebackground=COLORS['border'],
            activeforeground=COLORS['text']
        )
        browse_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Hover effect for browse button
        def on_enter(e):
            browse_btn.config(bg=COLORS['border'])

        def on_leave(e):
            browse_btn.config(bg=COLORS['card_bg'])

        browse_btn.bind("<Enter>", on_enter)
        browse_btn.bind("<Leave>", on_leave)

    return entry


def create_section_header(parent, text, icon=None):
    """
    Create a section header with decorative lines.

    Args:
        parent: Parent widget
        text: Header text
        icon: Not currently used, reserved for future icon support
    """
    header_frame = tk.Frame(parent, bg=COLORS['bg'])
    header_frame.pack(fill=tk.X, pady=(20, 10), padx=20)

    # Separator line on left
    left_line = tk.Frame(header_frame, bg=COLORS['primary'], height=2)
    left_line.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=10)

    # Header text
    label = tk.Label(
        header_frame,
        text=f"  {text}  ",
        font=("Segoe UI", 12, "bold"),
        bg=COLORS['bg'],
        fg=COLORS['primary']
    )
    label.pack(side=tk.LEFT)

    # Separator line on right
    right_line = tk.Frame(header_frame, bg=COLORS['primary'], height=2)
    right_line.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=10)


# ============================================================================
# BUTTON ACTION HANDLERS
# ============================================================================

def submit():
    """Handle Google Drive download button click."""
    old_stdout = sys.stdout
    sys.stdout = TextRedirector(output_text)
    try:
        auth(entry1.get(), entry2.get())
    finally:
        sys.stdout = old_stdout


def run_pipeline_ui():
    """Handle GPKG processing pipeline button click."""
    old_stdout = sys.stdout
    sys.stdout = TextRedirector(output_text)
    try:
        gpkg_dir = entry2.get()
        species_csv_path = entry3.get()
        output_gpkg_path = entry4.get()
        directory_copy = entry5.get()

        from error_handler import safe_run_pipeline
        safe_run_pipeline(gpkg_dir, species_csv_path, output_gpkg_path, directory_copy)
    except Exception as e:
        print(f"Pipeline error: {e}")
        print(f"\n✓ Error snapshot created with all files")
        print(f"✓ Look for folder: error_snapshot_YYYYMMDD_HHMMSS")
        print(f"   ZIP and share this entire folder for debugging")
    finally:
        sys.stdout = old_stdout
    save_settings()


def delete_files():
    """Handle delete files from Google Drive button click."""
    old_stdout = sys.stdout
    sys.stdout = TextRedirector(output_text)
    try:
        print(f"Attempting to delete all files in Google Drive folder...")
        delete_all_files_in_folder(entry1.get())
    except Exception as e:
        print(f"An error occurred while deleting files: {e}")
    finally:
        sys.stdout = old_stdout


# ============================================================================
# MAIN APPLICATION WINDOW SETUP
# ============================================================================

# Initialize main window
root = tk.Tk()
root.title("Biodiversity Mapping - QField File Processing")
root.configure(bg=COLORS['bg'])

# Configure window size and position
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
win_w = min(int(screen_w * WINDOW_WIDTH_RATIO), MAX_WINDOW_WIDTH)
win_h = min(int(screen_h * WINDOW_HEIGHT_RATIO), MAX_WINDOW_HEIGHT)
x = (screen_w - win_w) // 2
y = (screen_h - win_h) // 2
root.geometry(f'{win_w}x{win_h}+{x}+{y}')
root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

# Configure grid layout for responsive resizing
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)


# ============================================================================
# SCROLLABLE MAIN CANVAS SETUP
# ============================================================================

# Create scrollable main canvas
main_canvas = tk.Canvas(root, bg=COLORS['bg'], highlightthickness=0)
scrollbar = tk.Scrollbar(
    root,
    orient="vertical",
    command=main_canvas.yview,
    bg=COLORS['card_bg'],
    troughcolor=COLORS['bg']
)
scrollable_frame = tk.Frame(main_canvas, bg=COLORS['bg'])

# Configure scrollable frame to resize with canvas
scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)

canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")


def configure_scroll_region(event):
    """Update scrollable region and frame width when canvas is resized."""
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))
    canvas_width = event.width
    main_canvas.itemconfig(canvas_window, width=canvas_width)


main_canvas.bind("<Configure>", configure_scroll_region)
main_canvas.configure(yscrollcommand=scrollbar.set)


def on_mousewheel(event):
    """Handle mouse wheel scrolling."""
    main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


main_canvas.bind_all("<MouseWheel>", on_mousewheel)


# ============================================================================
# HEADER WITH LOGOS
# ============================================================================

header_frame = tk.Frame(scrollable_frame, bg=COLORS['card_bg'], relief=tk.FLAT, bd=1)
header_frame.pack(fill=tk.X, pady=(0, 10))

logo_container = tk.Frame(header_frame, bg=COLORS['card_bg'])
logo_container.pack(pady=20)

# Load and display logo images
try:
    moth_original = PhotoImage(file="moth.png")
    moth_image = moth_original.subsample(IMAGE_SCALE_FACTOR, IMAGE_SCALE_FACTOR)

    school_original = PhotoImage(file="school_logo.png")
    school_logo = school_original.subsample(IMAGE_SCALE_FACTOR, IMAGE_SCALE_FACTOR)

    butterfly_original = PhotoImage(file="butterfly.png")
    butterfly_image = butterfly_original.subsample(IMAGE_SCALE_FACTOR, IMAGE_SCALE_FACTOR)

    moth_label = tk.Label(logo_container, image=moth_image, bg=COLORS['card_bg'])
    school_label = tk.Label(logo_container, image=school_logo, bg=COLORS['card_bg'])
    butterfly_label = tk.Label(logo_container, image=butterfly_image, bg=COLORS['card_bg'])

    moth_label.pack(side=tk.LEFT, padx=15)
    school_label.pack(side=tk.LEFT, padx=15)
    butterfly_label.pack(side=tk.LEFT, padx=15)

    # Prevent garbage collection
    moth_label.image = moth_image
    moth_label.original = moth_original
    school_label.image = school_logo
    school_label.original = school_original
    butterfly_label.image = butterfly_image
    butterfly_label.original = butterfly_original

except Exception:
    # Fallback if images don't load
    title_label = tk.Label(
        logo_container,
        text="Biodiversity Mapping System",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS['card_bg'],
        fg=COLORS['primary']
    )
    title_label.pack(pady=20)


# ============================================================================
# SECTION 1: GOOGLE DRIVE DOWNLOAD
# ============================================================================

create_section_header(scrollable_frame, "STEP 1: Download Files from Google Drive")

card1 = tk.Frame(scrollable_frame, bg=COLORS['card_bg'], relief=tk.FLAT, bd=1)
card1.pack(fill=tk.X, padx=20, pady=10)

# Input fields
entry1 = create_input_row(card1, "Google Drive Folder ID:", None)
entry2 = create_input_row(
    card1,
    "Download Destination:",
    lambda: (entry2.delete(0, tk.END), entry2.insert(
        0, filedialog.askdirectory(title="Select Download Directory", parent=root)
    ))
)

# Download button
btn_download_frame = tk.Frame(card1, bg=COLORS['card_bg'])
btn_download_frame.pack(pady=15)
create_styled_button(
    btn_download_frame,
    "📥 Download Files from Google Drive",
    submit,
    'secondary',
    30
).pack()


# ============================================================================
# SECTION 2: GPKG PROCESSING
# ============================================================================

create_section_header(scrollable_frame, "STEP 2: Process GPKG Files")

card2 = tk.Frame(scrollable_frame, bg=COLORS['card_bg'], relief=tk.FLAT, bd=1)
card2.pack(fill=tk.X, padx=20, pady=10)

# Input fields
entry3 = create_input_row(
    card2,
    "Species CSV File:",
    lambda: (entry3.delete(0, tk.END), entry3.insert(
        0, filedialog.askopenfilename(
            title="Select Species CSV",
            parent=root,
            filetypes=[("CSV Files", "*.csv")]
        )
    ))
)

entry4 = create_input_row(
    card2,
    "Main GPKG File:",
    lambda: (entry4.delete(0, tk.END), entry4.insert(
        0, filedialog.askopenfilename(
            title="Select Main GPKG",
            parent=root,
            filetypes=[("GeoPackage", "*.gpkg")]
        )
    ))
)

entry5 = create_input_row(
    card2,
    "Backup Directory:",
    lambda: (entry5.delete(0, tk.END), entry5.insert(
        0, filedialog.askdirectory(title="Select Backup Directory", parent=root)
    ))
)

# Pipeline button
btn_pipeline_frame = tk.Frame(card2, bg=COLORS['card_bg'])
btn_pipeline_frame.pack(pady=15)
create_styled_button(
    btn_pipeline_frame,
    "⚙️ Run GPKG Processing Pipeline",
    run_pipeline_ui,
    'primary',
    30
).pack()


# ============================================================================
# SECTION 3: CLEANUP (OPTIONAL)
# ============================================================================

create_section_header(scrollable_frame, "STEP 3: Cleanup (Optional)")

card3 = tk.Frame(scrollable_frame, bg=COLORS['card_bg'], relief=tk.FLAT, bd=1)
card3.pack(fill=tk.X, padx=20, pady=10)

# Warning label
info_label = tk.Label(
    card3,
    text="⚠️  Warning: This will permanently delete all files from the Google Drive folder",
    font=("Segoe UI", 9, "italic"),
    bg=COLORS['card_bg'],
    fg=COLORS['danger']
)
info_label.pack(pady=(15, 10))

# Delete button
btn_delete_frame = tk.Frame(card3, bg=COLORS['card_bg'])
btn_delete_frame.pack(pady=15)
create_styled_button(
    btn_delete_frame,
    "🗑️ Delete All Files from Google Drive",
    delete_files,
    'danger',
    30
).pack()


# ============================================================================
# OUTPUT LOG SECTION
# ============================================================================

create_section_header(scrollable_frame, "Output Log")

# Container frame for output
output_container = tk.Frame(scrollable_frame, bg=COLORS['bg'])
output_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))

output_frame = tk.Frame(output_container, bg=COLORS['card_bg'], relief=tk.FLAT, bd=1)
output_frame.pack(fill=tk.BOTH, expand=True)

# Output scrollbar
output_scroll = tk.Scrollbar(
    output_frame,
    bg=COLORS['card_bg'],
    troughcolor=COLORS['bg']
)
output_scroll.pack(side=tk.RIGHT, fill=tk.Y)

# Output text widget (terminal-style)
output_text = tk.Text(
    output_frame,
    font=("Consolas", 10),
    wrap=tk.WORD,
    bg="#0D0D0D",
    fg="#00FF00",
    relief=tk.FLAT,
    padx=10,
    pady=10,
    yscrollcommand=output_scroll.set,
    insertbackground="#00FF00"
)
output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
output_text.configure(state=tk.DISABLED)
output_scroll.config(command=output_text.yview)


# ============================================================================
# FINALIZE LAYOUT AND START APPLICATION
# ============================================================================

# Grid layout for canvas and scrollbar
main_canvas.grid(row=0, column=0, sticky="nsew")
scrollbar.grid(row=0, column=1, sticky="ns")

# Load saved settings
load_settings()

# Bring window to front on startup (non-persistent)
root.lift()
root.attributes('-topmost', True)
root.after_idle(root.attributes, '-topmost', False)

# Start the application
root.mainloop()
