import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# Edit main to take in root_folder_id and download_dir
SCOPES = ['https://www.googleapis.com/auth/drive']

def auth(root_folder_id, download_dir):
    """Downloads all files from a Google Drive folder, including subfolders, maintaining the folder structure."""
    # Get Google Drive API service
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials_biodiversity.json', SCOPES)
                creds = flow.run_local_server(port=8080)  # Set specific port
        except Exception as e:
            print(f"Authentication error: {e}")
            print("Creating new authentication token...")
            # Remove existing token if there's an issue with it
            if os.path.exists('token.pickle'):
                os.remove('token.pickle')
            # Create new token
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_biodiversity.json', SCOPES)
            creds = flow.run_local_server(port=8080)  # Set specific port

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    # Process the root folder
    process_folder(service, root_folder_id, download_dir)

    print('Files saved to '+ download_dir)




def process_folder(service, folder_id, parent_path):
    """
    Processes a Google Drive folder, downloading its files and recursively processing subfolders.

    Args:
        service: Authorized Google Drive API service instance.
        folder_id: The ID of the folder to process.
        parent_path: Local path of the parent directory where the folder's contents will be downloaded.
    """
    # Create the parent folder locally if it doesn't exist
    if not os.path.exists(parent_path):
        os.makedirs(parent_path)

    # Get the list of files and subfolders in the given folder
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType)"
    ).execute()

    items = results.get('files', [])

    if not items:
        print(f'No files found in the folder: {parent_path}')
        return

    print(f'Processing folder: {parent_path}, found {len(items)} items.')

    # Process each item
    for item in items:
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        ext = os.path.splitext(file_name)[1]
        file_path = os.path.join(parent_path, f"{file_id}{ext}")

        #print(f'Processing {file_name}...')

        if mime_type == 'application/vnd.google-apps.folder':
            # If the item is a folder, recursively process it
            print(f'Entering subfolder: {file_name}')
            process_folder(service, file_id, file_path)
        else:
            try:
                # Handle Google Docs, Sheets, etc.
                if mime_type.startswith('application/vnd.google-apps'):
                    if mime_type == 'application/vnd.google-apps.document':
                        request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
                        file_path += '.pdf'
                    elif mime_type == 'application/vnd.google-apps.spreadsheet':
                        request = service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        file_path += '.xlsx'
                    elif mime_type == 'application/vnd.google-apps.presentation':
                        request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
                        file_path += '.pdf'
                    else:
                        print(f'Skipping unsupported Google format: {file_name}')
                        continue
                else:
                    request = service.files().get_media(fileId=file_id)

                # Download the file
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        print(f"Download {int(status.progress() * 100)}% for {file_name}")

                print(f'Successfully downloaded {file_name} to {file_path}')

            except Exception as e:
                print(f'Error downloading {file_name}: {str(e)}')


def delete_all_files_in_folder(folder_id):
    """
    Deletes only .gpkg files in a Google Drive folder, including recursively processing subfolders.

    Args:
        folder_id: The ID of the folder whose .gpkg files are to be deleted.
    """
    # Initialize Google Drive API service
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials_biodiversity.json', SCOPES)
                creds = flow.run_local_server(port=8080)  # Set specific port
        except Exception as e:
            print(f"Authentication error: {e}")
            print("Creating new authentication token...")
            if os.path.exists('token.pickle'):
                os.remove('token.pickle')
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_biodiversity.json', SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    try:
        # Get the list of files and subfolders in the folder
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            pageSize=1000,
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()

        items = results.get('files', [])

        if not items:
            print(f'No files found in the folder with ID: {folder_id}')
            return

        print(f'Checking folder: {folder_id}, found {len(items)} items.')

        for item in items:
            file_id = item['id']
            file_name = item['name']
            mime_type = item['mimeType']

            if mime_type == 'application/vnd.google-apps.folder':
                # Recurse into subfolders
                print(f'Entering subfolder: {file_name}')
                # delete_gpkg_files_in_folder(file_id)
            else:
                # Check if the file is a .gpkg file
                if file_name.lower().endswith('.gpkg'):
                    try:
                        service.files().delete(fileId=file_id).execute()
                        print(f'Successfully deleted .gpkg file: {file_name}')
                    except HttpError as error:
                        print(f'Failed to delete {file_name}: {error}')
                else:
                    print(f'Skipping non-gpkg file: {file_name}')

    except Exception as e:
        print(f'Error processing folder {folder_id}: {str(e)}')


# if __name__ == '__main__':
#     if os.path.exists('token.pickle'):
#         os.remove('token.pickle')
#         print("Removed existing token.pickle")
#
#     # Set the root folder ID and download directory
#     root_folder_id = '13tUCjvC4GCbD7zKCqm2XmqcWVofekkQ_nrqOimu9U35vDjtFBxBfr6jXYKBmtvtssRRgjh8F'  # Replace with your folder ID
#     download_dir = '/Users/johnny/Documents/Biodiversity Stuff/GoogleDriveToOneDrive/test'
#     auth(root_folder_id, download_dir)
