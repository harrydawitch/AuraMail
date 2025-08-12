from pathlib import Path
import os
import sys
import json
import shutil
import webbrowser
import platform
from pathlib import Path


try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

# google auth imports
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
except Exception:
    InstalledAppFlow = None
    Credentials = None
    Request = None

APP_NAME = "AuraMail"  # <--- change this to your app's short name if you want
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

def get_app_dir():
    """
    Return the root folder of the project (where this script resides or,
    if frozen by PyInstaller, where the executable resides).
    """
    if getattr(sys, 'frozen', False):  # running as PyInstaller exe
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent

    # If setup_oauth.py is in a subfolder (e.g., src/setup), go up to project root
    return base_path.parent if (base_path / 'setup_oauth.py').exists() else base_path


APP_DIR = get_app_dir()
CREDENTIALS_PATH = APP_DIR / 'credentials.json'
TOKEN_PATH = APP_DIR / 'token.json'
CREDENTIALS_EXAMPLE_PATH = Path('credentials.example.json')
README_PATH = Path('README.md')
ENV_PATH = get_app_dir() / ".env"



GCP_CREDENTIALS_URL = 'https://console.cloud.google.com/apis/credentials'
GCP_ENABLE_API_URL = 'https://console.cloud.google.com/apis/library/gmail.googleapis.com'


def ensure_app_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)


def open_in_browser(url):
    print(f"Opening: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print("Failed to open browser automatically.", e)



def update_env_file(openai_key: str, my_email: str):
    """
    Create or update the .env file with the provided OpenAI key and email.
    """
    env_data = {}
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    env_data[k] = v

    env_data["OPENAI_API_KEY"] = openai_key
    env_data["MY_EMAIL"] = my_email

    with open(ENV_PATH, "w") as f:
        for k, v in env_data.items():
            f.write(f"{k}={v}\n")

    print(f".env file updated at {ENV_PATH}")



def ask_user_for_credentials_file():
    """Try a file dialog first, fall back to text input."""
    if TK_AVAILABLE:
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_path = filedialog.askopenfilename(title='Select credentials.json (downloaded from Google Cloud)')
            root.destroy()
            if file_path:
                return Path(file_path)
        except Exception:
            pass

    # fallback to CLI path entry
    print("\nPlease paste the full path to the downloaded credentials.json file (or press Enter to cancel):")
    p = input().strip()
    if not p:
        return None
    return Path(p)


def copy_credentials_file(src: Path):
    if not src.exists():
        raise FileNotFoundError(str(src))
    ensure_app_dir()
    dest = CREDENTIALS_PATH
    shutil.copy2(str(src), str(dest))
    print(f"Copied credentials.json to {dest}")
    return dest


def save_token(creds):
    ensure_app_dir()
    with open(TOKEN_PATH, 'w') as f:
        f.write(creds.to_json())
    print(f"Saved token to {TOKEN_PATH}")


def run_oauth_flow():
    if InstalledAppFlow is None:
        print("google-auth libraries are not installed. Run:\n  pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2")
        return None

    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError("credentials.json not found in app folder. Run setup to add it.")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    print("Starting local server for OAuth consent — your browser will open.")
    creds = flow.run_local_server(port=0)
    save_token(creds)
    return creds


def ensure_token():
    """Return Credentials object, refreshing or running flow when needed."""
    if Credentials is None:
        print("google-auth libraries are not installed. Run:\n  pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2")
        return None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    else:
        creds = None

    if creds and creds.valid:
        print("Existing token is valid.")
        return creds

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing expired token...")
        try:
            creds.refresh(Request())
            save_token(creds)
            return creds
        except Exception as e:
            print("Failed to refresh token:", e)

    # else we need to run interactive flow
    return run_oauth_flow()


def write_readme_and_example():
    if README_PATH.exists():
        print("README.md already exists in repo root — not overwriting.")
    else:
        print("Writing a quick README.md to repo root...")
        README_CONTENT = f"""
# {APP_NAME} — Quick start

This repository contains a local desktop Python app that accesses the user's Gmail account.

**Important:** each user must create their own OAuth credentials in Google Cloud and download a `credentials.json` file (Desktop app). Do not commit `credentials.json` or `token.json` to source control.

## Quick setup

1. Go to the Google Cloud Console: enable the Gmail API and create OAuth credentials (Desktop app):
   - Enable the Gmail API: {GCP_ENABLE_API_URL}
   - Create OAuth credentials: {GCP_CREDENTIALS_URL}
2. Download the `credentials.json` and run `python setup_oauth.py`.
3. The script will copy `credentials.json` into a local app folder and run the OAuth consent flow. After consent a `token.json` is saved for future runs.

## Where files are stored (defaults)

- Windows: `%APPDATA%\\{APP_NAME}\\credentials.json` and `%APPDATA%\\{APP_NAME}\\token.json`
- macOS / Linux: `~/.{APP_NAME.lower()}/credentials.json` and `~/.{APP_NAME.lower()}/token.json`

## Scopes used

- `https://www.googleapis.com/auth/gmail.readonly` — read email metadata & bodies
- `https://www.googleapis.com/auth/gmail.send` — send email on behalf of the signed-in user

## Packaging & distribution notes

- When creating an executable with PyInstaller, make sure your app reads `credentials.json` and writes `token.json` to the user app folder (not inside the exe).
- Add the `token.json` and `credentials.json` paths to your `.gitignore` file.

"""
        README_PATH.write_text(README_CONTENT, encoding='utf-8')
        print(f"Wrote {README_PATH}")

    if not CREDENTIALS_EXAMPLE_PATH.exists():
        print("Writing credentials.example.json (safe to commit) ...")
        example = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                "project_id": "your-project-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
            }
        }
        CREDENTIALS_EXAMPLE_PATH.write_text(json.dumps(example, indent=2))
        print(f"Wrote {CREDENTIALS_EXAMPLE_PATH}")
    else:
        print("credentials.example.json already exists — not overwriting.")


def setup_interactive():
    print(f"\n=== {APP_NAME} setup ===\n")
    ensure_app_dir()

    if CREDENTIALS_PATH.exists():
        print(f"Found credentials.json at {CREDENTIALS_PATH}")
    else:
        print("No credentials.json found in app folder.")
        print("I can open the Google Cloud Console page where you can create OAuth credentials for a Desktop app.")
        print("Would you like me to open that page in your browser now? [Y/n]")
        choice = input().strip().lower() or 'y'
        if choice.startswith('y'):
            open_in_browser(GCP_CREDENTIALS_URL)

        print("\nAfter creating & downloading the JSON file, select it in the next dialog (or paste its path). Press Enter to continue.")
        input()

        src = ask_user_for_credentials_file()
        if not src:
            print("No file provided. Exiting setup.")
            return
        try:
            copy_credentials_file(src)
        except Exception as e:
            print("Failed to copy credentials.json:", e)
            return

    # run OAuth flow to create token.json
    try:
        creds = ensure_token()
        if creds:
            print("OAuth setup completed successfully!")
            print(f"credentials.json and token.json are stored in: {APP_DIR}")
        else:
            print("OAuth setup did not complete. See messages above.")
            
        print("\n=== Configure OpenAI API key and your email ===")
        openai_key = input("Enter your OpenAI API key: ").strip()
        my_email = input("Enter your email: ").strip()
        update_env_file(openai_key, my_email)
            
    except Exception as e:
        print("Error during OAuth flow:", e)

    # write helpful repo files
    write_readme_and_example()
    print("\nSetup finished. Reminder: add the following paths to your .gitignore if you will commit this repo:")
    print(f"  {CREDENTIALS_PATH}")
    print(f"  {TOKEN_PATH}")


if __name__ == '__main__':
    try:
        setup_interactive()
    except KeyboardInterrupt:
        print("Setup cancelled by user.")
        sys.exit(1)
