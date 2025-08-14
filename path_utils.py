"""
Unified path utilities for SmartEmailBot
Handles both development and PyInstaller bundled environments
"""
import os
import sys
from pathlib import Path

def get_app_dir():
    """
    Get the application directory consistently across dev and bundled modes.
    This is where credentials.json, token.json, and .env should be located.
    
    Returns:
        Path: The application directory
    """
    if getattr(sys, 'frozen', False):  # PyInstaller bundled
        # When bundled, use the directory containing the executable
        app_dir = Path(sys.executable).parent
        print(f"[PATH] Running as bundled app, executable at: {sys.executable}")
        print(f"[PATH] App directory: {app_dir}")
        return app_dir
    else:  # Development mode
        # In development, use the project root (where main.py is located)
        app_dir = Path(__file__).resolve().parent
        print(f"[PATH] Running in development mode")
        print(f"[PATH] Script file: {__file__}")
        print(f"[PATH] App directory: {app_dir}")
        return app_dir

def get_credentials_path():
    """Get the path to credentials.json"""
    return get_app_dir() / 'credentials.json'

def get_token_path():
    """Get the path to token.json"""
    return get_app_dir() / 'token.json'

def get_env_path():
    """Get the path to .env file"""
    return get_app_dir() / '.env'

def load_environment():
    """
    Load environment variables from .env file if it exists.
    This should be called early in the application startup.
    """
    env_path = get_env_path()
    
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            print(f"[ENV] ✓ Loaded environment from: {env_path}")
            
            # Verify key environment variables
            required_vars = ['OPENAI_API_KEY', 'MY_EMAIL', 'EMAIL_DISPLAY_NAME']
            missing = []
            for var in required_vars:
                if not os.getenv(var):
                    missing.append(var)
            
            if missing:
                print(f"[ENV] ⚠️  Missing environment variables: {', '.join(missing)}")
                return False
            else:
                print(f"[ENV] ✓ All required environment variables found")
                return True
                
        except ImportError:
            print(f"[ENV] ⚠️  python-dotenv not available, skipping .env loading")
            return False
        except Exception as e:
            print(f"[ENV] ❌ Error loading .env file: {e}")
            return False
    else:
        print(f"[ENV] ⚠️  No .env file found at: {env_path}")
        return False

def debug_paths():
    """Print debugging information about paths and files"""
    print("\n" + "="*60)
    print("PATH DEBUG INFORMATION")
    print("="*60)
    
    print(f"Python executable: {sys.executable}")
    print(f"Frozen (bundled): {getattr(sys, 'frozen', False)}")
    print(f"Current working dir: {os.getcwd()}")
    
    if not getattr(sys, 'frozen', False):
        print(f"Script file (__file__): {__file__}")
    
    app_dir = get_app_dir()
    print(f"App directory: {app_dir}")
    print(f"App directory exists: {app_dir.exists()}")
    
    # Check important files
    files_to_check = {
        'credentials.json': get_credentials_path(),
        'token.json': get_token_path(),
        '.env': get_env_path(),
    }
    
    print("\nFile locations:")
    for name, path in files_to_check.items():
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        print(f"  {name:<15} {'✓' if exists else '✗'} {path} ({size} bytes)")
    
    print("\nEnvironment variables:")
    env_vars = ['OPENAI_API_KEY', 'MY_EMAIL', 'EMAIL_DISPLAY_NAME']
    for var in env_vars:
        value = os.getenv(var, '')
        masked_value = f"{value[:10]}..." if len(value) > 10 else value
        print(f"  {var:<20} {'✓' if value else '✗'} {masked_value if value else '(not set)'}")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    # Test the path utilities
    debug_paths()
    load_environment()
    
    