#!/usr/bin/env python3
"""
Test noScribe's core transcription functionality using the tiny Whisper model.

This test validates that noScribe's dependencies and core transcription work.
It uses a tiny model (~75MB) from HuggingFace for fast CI testing.

What this tests:
- noScribe modules (utils.py, whisper_mp_worker.py) import correctly
- noScribe.py has valid Python syntax
- Tiny Whisper model loads and transcribes audio
- Core transcription pipeline works end-to-end

Note: This is a simplified test for CI. The full multiprocessing pipeline
is tested separately by pytest in the python.yml workflow.
"""

import sys
import os
from pathlib import Path

def print_step(msg):
    """Print with flush for immediate output"""
    print(msg, flush=True)

def test_noscribe_core():
    """Test noScribe's core functionality (pytest-compatible)"""
    
    print_step("="*70)
    print_step("NOSCRIBE TRANSCRIPTION TEST (Tiny Model)")
    print_step("="*70)
    
    # Use tiny test model (not production models)
    audio_file = Path("test_resources/test_audio.mp3")
    model_dir = Path("models/tiny-test")
    
    # Step 1: Verify test files
    print_step("\n[1/5] Verifying test files...")
    assert audio_file.exists(), f"Test audio not found: {audio_file}"
    print_step(f"   ✓ Audio: {audio_file} ({audio_file.stat().st_size/1024:.1f} KB)")
    
    assert model_dir.exists(), f"Model dir not found: {model_dir}"
    for f in ["config.json", "model.bin", "tokenizer.json"]:
        assert (model_dir/f).exists(), f"Missing: {model_dir/f}"
    
    size_mb = (model_dir/"model.bin").stat().st_size/(1024*1024)
    print_step(f"   ✓ Model: {model_dir} ({size_mb:.1f} MB)")
    
    # Step 2: Import noScribe modules
    print_step("\n[2/5] Importing noScribe modules...")
    sys.path.insert(0, str(Path.cwd()))
    
    try:
        import utils
        print_step("   ✓ utils.py")
    except Exception as e:
        assert False, f"Cannot import utils.py: {e}"
    
    try:
        import whisper_mp_worker
        print_step("   ✓ whisper_mp_worker.py")
    except Exception as e:
        assert False, f"Cannot import whisper_mp_worker.py: {e}"
    
    # Step 3: Validate noScribe.py syntax
    print_step("\n[3/5] Validating noScribe.py...")
    try:
        import py_compile
        py_compile.compile('noScribe.py', doraise=True)
        print_step("   ✓ noScribe.py syntax valid")
    except Exception as e:
        assert False, f"noScribe.py syntax error: {e}"
    
    # Step 4: Load and test Whisper model
    print_step(f"\n[4/5] Testing transcription...")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(str(model_dir), device="cpu", compute_type="int8")
        print_step("   ✓ Model loaded")
        
        segments, info = model.transcribe(str(audio_file), language="en", beam_size=5, vad_filter=True)
        print_step(f"   ✓ Language: {info.language} ({info.language_probability:.2%})")
        
        texts = []
        for seg in segments:
            text = seg.text.strip()
            texts.append(text)
            print_step(f"      [{seg.start:5.1f}s-{seg.end:5.1f}s] {text}")
        
        full_text = " ".join(texts)
        assert len(full_text) > 0, "No text transcribed"
        print_step(f"\n   ✓ Transcribed {len(texts)} segments ({len(full_text)} chars)")
        
    except AssertionError:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        assert False, f"Transcription failed: {e}"
    
    # Step 5: Summary
    print_step("\n[5/5] Test summary")
    print_step(f"   ✓ Model: {size_mb:.1f} MB (tiny test model)")
    print_step(f"   ✓ Segments: {len(texts)}")
    print_step(f"   ✓ Text: {len(full_text)} characters")
    
    print_step("\n"+"="*70)
    print_step("✓ ALL TESTS PASSED")
    print_step("="*70)
    print_step("\nValidated:")
    print_step("  ✓ noScribe modules import correctly")
    print_step("  ✓ noScribe.py has valid syntax")
    print_step("  ✓ Tiny Whisper model loads and transcribes")
    print_step("  ✓ Core transcription pipeline works")

if __name__ == "__main__":
    try:
        test_noscribe_core()
        print("\n✓ Test completed", flush=True)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}", flush=True)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n✗ Interrupted", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
