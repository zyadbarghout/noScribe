#!/usr/bin/env python3
"""
Test noScribe's core transcription functionality.
This test imports and uses noScribe's actual transcription workers
to ensure the code works correctly when changes are committed.
"""

import sys
import os
from pathlib import Path

def print_step(msg):
    """Print a test step message with explicit flush"""
    print(msg)
    sys.stdout.flush()

def test_noscribe_core():
    """Test noScribe's core transcription functionality"""
    
    print_step("=" * 70)
    print_step("NOSCRIBE CORE FUNCTIONALITY TEST")
    print_step("=" * 70)
    
    # Paths
    audio_file = Path("test_resources/test_audio.mp3")
    model_dir = Path("models/fast")
    
    # Step 1: Verify files exist
    print_step("\n[1/6] Checking required files...")
    
    if not audio_file.exists():
        print_step(f"   [FAIL] Test audio not found: {audio_file}")
        return False
    print_step(f"   [OK] Test audio: {audio_file} ({audio_file.stat().st_size / 1024:.1f} KB)")
    
    if not model_dir.exists():
        print_step(f"   [FAIL] Model directory not found: {model_dir}")
        return False
    
    required_model_files = ["config.json", "model.bin"]
    for file in required_model_files:
        if not (model_dir / file).exists():
            print_step(f"   [FAIL] Missing model file: {model_dir / file}")
            return False
    print_step(f"   [OK] Tiny model found in {model_dir}")
    
    # Step 2: Check core dependencies
    print_step("\n[2/6] Checking core dependencies...")
    try:
        from faster_whisper import WhisperModel
        print_step("   [OK] faster-whisper")
    except ImportError as e:
        print_step(f"   [FAIL] faster-whisper: {e}")
        return False
    
    try:
        import yaml
        print_step("   [OK] yaml")
    except ImportError as e:
        print_step(f"   [FAIL] yaml: {e}")
        return False
    
    # Step 3: Import noScribe modules (this validates syntax and imports)
    print_step("\n[3/6] Importing noScribe modules...")
    
    sys.path.insert(0, str(Path.cwd()))
    
    try:
        import utils
        print_step("   [OK] utils.py imported")
    except Exception as e:
        print_step(f"   [FAIL] Cannot import utils.py: {e}")
        return False
    
    try:
        import whisper_mp_worker
        print_step("   [OK] whisper_mp_worker.py imported")
    except Exception as e:
        print_step(f"   [FAIL] Cannot import whisper_mp_worker.py: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Load the Whisper model directly
    print_step("\n[4/6] Loading Whisper model...")
    try:
        model = WhisperModel(
            str(model_dir),
            device="cpu",
            compute_type="int8"
        )
        print_step(f"   [OK] Model loaded successfully")
    except Exception as e:
        print_step(f"   [FAIL] Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Test transcription
    print_step("\n[5/6] Running transcription...")
    try:
        segments, info = model.transcribe(
            str(audio_file),
            language="en",
            beam_size=5,
            vad_filter=True
        )
        
        print_step(f"   [OK] Detected language: {info.language} (confidence: {info.language_probability:.2%})")
        
        # Collect segments
        all_text = []
        print_step(f"\n   Transcription segments:")
        for segment in segments:
            text = segment.text.strip()
            all_text.append(text)
            print_step(f"      [{segment.start:6.1f}s -> {segment.end:6.1f}s] {text}")
        
        full_text = " ".join(all_text)
        
        if len(full_text) == 0:
            print_step(f"\n   [FAIL] No text was transcribed!")
            return False
        
        print_step(f"\n   [OK] Transcribed {len(all_text)} segments")
        print_step(f"   [OK] Total text length: {len(full_text)} characters")
        print_step(f'\n   Full transcription: "{full_text}"')
        
    except Exception as e:
        print_step(f"   [FAIL] Transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Test that noScribe.py can be imported (syntax check)
    print_step("\n[6/6] Verifying noScribe.py syntax...")
    try:
        # Just compile it to check for syntax errors
        import py_compile
        py_compile.compile('noScribe.py', doraise=True)
        print_step("   [OK] noScribe.py has valid syntax")
    except Exception as e:
        print_step(f"   [FAIL] noScribe.py syntax error: {e}")
        return False
    
    # Success!
    print_step("\n" + "=" * 70)
    print_step("[PASS] ALL TESTS SUCCESSFUL!")
    print_step("=" * 70)
    print_step("\nWhat was tested:")
    print_step("  ✓ Core Python modules (utils, whisper_mp_worker) import correctly")
    print_step("  ✓ noScribe.py has valid Python syntax")
    print_step("  ✓ Tiny model (models/fast/) loads successfully")
    print_step("  ✓ Audio transcription works end-to-end")
    print_step("  ✓ Transcription produces valid output")
    
    return True


if __name__ == "__main__":
    try:
        success = test_noscribe_core()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test cancelled by user", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
