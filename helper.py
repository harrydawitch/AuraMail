import os
from dotenv import load_dotenv
import traceback
from path_utils import get_credentials_path, get_token_path

load_dotenv()

def refresh_gmail_token():
    """
    Refresh Gmail token if expired using unified path system
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        
        # Use unified path system
        TOKEN_PATH = get_token_path()
        CREDENTIALS_PATH = get_credentials_path()
        
        SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]
        
        print(f"[GMAIL] Looking for token at: {TOKEN_PATH}")
        print(f"[GMAIL] Looking for credentials at: {CREDENTIALS_PATH}")
        
        if not TOKEN_PATH.exists():
            return False, f"No token.json found at {TOKEN_PATH}. Run setup.py first."
            
        if not CREDENTIALS_PATH.exists():
            return False, f"No credentials.json found at {CREDENTIALS_PATH}. Run setup.py first."
        
        # Load existing credentials
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        
        if creds and creds.valid:
            return True, "Token is still valid."
            
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired Gmail token...")
            try:
                creds.refresh(Request())
                
                # Save refreshed token
                with open(TOKEN_PATH, 'w') as f:
                    f.write(creds.to_json())
                    
                print(f"✓ Token refreshed and saved to {TOKEN_PATH}")
                return True, "Token successfully refreshed."
                
            except Exception as refresh_error:
                print(f"Failed to refresh token: {refresh_error}")
                return False, f"Token refresh failed: {refresh_error}"
        
        # If we get here, we need to re-authenticate
        return False, "Token expired and cannot be refreshed. Run setup.py to re-authenticate."
        
    except ImportError:
        return False, "google-auth libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2"
    except Exception as e:
        return False, f"Error during token refresh: {e}"

def check_gmail_api(gmail_toolkit, timeout_seconds: int = 10):
    """
    Enhanced Gmail API check with automatic token refresh
    """
    try:
        service = getattr(gmail_toolkit, "api_resource", None)
        if service is None:
            return False, "GmailToolkit has no api_resource – authentication not initialized."

        # Try the API call first
        try:
            labels_resp = service.users().labels().list(userId="me",).execute()
            labels = labels_resp.get("labels", [])
            return True, f"Gmail API OK – found {len(labels)} labels."
            
        except Exception as api_error:
            # If API call fails, try refreshing token
            print(f"Gmail API call failed: {api_error}")
            print("Attempting to refresh token...")
            
            refresh_success, refresh_message = refresh_gmail_token()
            
            if refresh_success:
                # Reinitialize gmail_toolkit with refreshed token
                try:
                    from langchain_google_community import GmailToolkit
                    new_toolkit = GmailToolkit()
                    service = new_toolkit.api_resource
                    
                    # Try API call again with refreshed token
                    labels_resp = service.users().labels().list(userId="me",).execute()
                    labels = labels_resp.get("labels", [])
                    return True, f"Gmail API OK after token refresh – found {len(labels)} labels."
                    
                except Exception as retry_error:
                    return False, f"Gmail API still failing after token refresh: {retry_error}"
            else:
                return False, f"Gmail API error and token refresh failed: {refresh_message}"
                
    except Exception as e:
        tb = traceback.format_exc()
        return False, f"Gmail API error: {e}\n{tb}"

def check_openai_api():
    """
    Verify OPENAI_API_KEY exists and try to call the OpenAI SDK.
    Tries both new `from openai import OpenAI` and the older `import openai` API.
    Returns (True, message) or (False, error_message).
    """
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not key.strip():
        return False, "OPENAI_API_KEY not set in environment."

    # Try new SDK first
    try:
        from openai import OpenAI
        client = OpenAI()  # will read API key from env
        # tiny call that lists models; inexpensive
        models = client.models.list()
        # models.data is list-like in new SDK
        count = len(getattr(models, "data", models))
        return True, f"OpenAI SDK OK – {count} models listed (via OpenAI client)."
    except Exception as e_new:
        # fallback to legacy package
        try:
            import openai
            openai.api_key = key
            models = openai.Model.list()
            count = len(models.get("data", [])) if isinstance(models, dict) else len(models.data)
            return True, f"OpenAI OK – {count} models listed (via openai)."
        except Exception as e_legacy:
            import traceback
            tb = traceback.format_exc()
            return False, f"OpenAI check failed.\nnew-sdk error: {e_new}\nlegacy error: {e_legacy}\n{tb}"