#!/usr/bin/env python3
"""
Download tiny Whisper model from Hugging Face for CI testing.
This script is used by GitHub Actions to set up the test environment.
"""

from pathlib import Path
from huggingface_hub import snapshot_download
import shutil
import sys

def download_model():
    """Download and prepare the tiny Whisper model"""
    
    print("[INFO] Downloading tiny.en model from Hugging Face...")
    
    # Create models directory for TINY test model (separate from production models)
    models_dir = Path("models/tiny-test")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download the tiny.en model (smallest - ~37MB)
        model_path = snapshot_download(
            repo_id="Systran/faster-whisper-tiny.en",
            cache_dir=".cache/huggingface"
        )
        
        print(f"[INFO] Downloaded to: {model_path}")
        
        # Copy all files to models/tiny-test/
        source = Path(model_path)
        copied_files = []
        
        for file in source.rglob("*"):
            if file.is_file():
                dest = models_dir / file.name  # Flatten structure
                shutil.copy2(file, dest)
                copied_files.append(file.name)
                print(f"[INFO] Copied: {file.name}")
        
        print(f"[OK] Model ready at {models_dir}")
        print(f"[OK] Copied {len(copied_files)} files")
        
        # Verify required files
        required = ["config.json", "model.bin", "tokenizer.json"]
        missing = []
        
        for req in required:
            if not (models_dir / req).exists():
                missing.append(req)
        
        if missing:
            print(f"[FAIL] Missing required files: {', '.join(missing)}")
            return False
        
        print("[OK] All required model files present")
        return True
        
    except Exception as e:
        print(f"[FAIL] Error downloading model: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)
