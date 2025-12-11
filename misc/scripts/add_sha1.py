import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY_FILE = '/home/guest/Downloads/gen-lang-client-0087898455-firebase-adminsdk-fbsvc-0d2b894038.json'
SHA1 = '9B:0F:4B:9B:0F:ED:0D:D0:A3:23:D0:B7:2C:7C:3C:A5:FB:6A:48:04'
PACKAGE_NAME = 'io.nekohasekai.sagernet'

def add_sha1():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            KEY_FILE, scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/firebase']
        )
        service = build('firebase', 'v1beta1', credentials=credentials)

        # 1. List Projects to get Project ID (or use from JSON)
        # The JSON usually has project_id. Let's assume we need to find the App ID.
        project_id = credentials.project_id
        print(f"Project ID: {project_id}")

        # 2. List Android Apps to find the App ID for the package name
        parent = f"projects/{project_id}"
        response = service.projects().androidApps().list(parent=parent).execute()
        
        app_id = None
        for app in response.get('apps', []):
            if app.get('packageName') == PACKAGE_NAME:
                app_id = app['appId']
                print(f"Found App ID: {app_id}")
                break
        
        if not app_id:
            print(f"Error: Could not find Android App for package {PACKAGE_NAME}")
            return

        # 3. Add SHA-1
        sha_body = {
            "shaHash": SHA1,
            "certType": "SHA_1"
        }
        
        try:
            result = service.projects().androidApps().sha().create(
                parent=f"{parent}/androidApps/{app_id}",
                body=sha_body
            ).execute()
            print(f"Successfully added SHA-1: {result.get('name')}")
        except Exception as e:
            if "already exists" in str(e):
                print("SHA-1 already exists.")
            else:
                raise e

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    add_sha1()
