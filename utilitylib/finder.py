import os
import sys
import json

from google.cloud import storage

class ScriptFinder:
    '''
    Finder class for script-based program
    '''
    def __init__(self, filename: str):
        self.path = self.get_resource_path(filename)
    
    # Get resource path
    def get_resource_path(self, relative_path: str):
        # Check if running as compiled .exe
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            file_path = os.path.join(exe_dir, relative_path)
            if os.path.exists(file_path): return file_path
            
            # Fall back to PyInstaller temp directory
            try: base_path = sys._MEIPASS
            except AttributeError: base_path = exe_dir
        # Running as script
        else: 
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_path = current_dir
        return os.path.join(base_path, relative_path)

    # Load data from local file
    def load_data(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f: 
                return json.load(f)
        except Exception as e: 
            print(f"Failed to load data: {e}"); 
            return False
    
    # Save data to local file
    def save_data(self, data: dict):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e: 
            print(f"Failed to save data: {e}"); 
            return False

class CloudFinder:
    '''
    Finder class for cloud-based program
    '''
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name

    # Save data to cloud
    def save(self, data: dict, blob_name: str, local: bool = False):
        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            if local:
                with open(blob_name, "w", encoding='utf-8') as f:
                    f.write(json_content)
                return True
            else:
                client = storage.Client()
                bucket = client.bucket(self.bucket_name)
                blob = bucket.blob(blob_name)
                blob.upload_from_string(json_content, content_type='application/json; charset=utf-8')
                return True
        except Exception as e:
            print(f"Failed to save data: {e}")
            return False

    # Load data from cloud
    def load(self, local_file_name, blob_name = "", local = False):
        # Loads .json file from GCS. Blob name is set to local file name if not provided.
        try:
            if not blob_name: blob_name = local_file_name
            if local:
                with open(local_file_name, "r", encoding='utf-8') as f:
                    content = f.read()
                    return json.loads(content) if content else False
            else:
                client = storage.Client()
                bucket = client.bucket(self.bucket_name)
                blob = bucket.blob(blob_name)
                if not blob.exists(): return False
                content = blob.download_as_text(encoding='utf-8')
                return json.loads(content) if content else False
        except Exception as e:
            print(f"Failed to load data: {e}")
            return False
