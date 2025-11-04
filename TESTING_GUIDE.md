# Cross-Platform Transcription Testing Guide

## Overview

This document describes the comprehensive testing infrastructure for noScribe transcription across multiple platforms (macOS, Linux, Windows) and Python versions.

## Test Suite Components

### 1. **test_transcription.py**
Standalone test script that:
- Transcribes audio files using both fast and precise Whisper models
- Runs entirely in terminal without GUI
- Generates HTML reports and JSON results
- Includes automatic compute type fallback (float16 → float32)
- Platform agnostic design

**Usage:**
```bash
python3 test_transcription.py --audio test_resources/test_audio.mp3 --verbose
```

### 2. **simple_platform_test.py**
Platform-specific test runner that:
- Validates Python dependencies
- Checks system dependencies (ffmpeg)
- Verifies model availability
- Runs transcription tests
- Generates comprehensive reports with pass/fail details
- Provides actionable recommendations

**Usage:**
```bash
python3 simple_platform_test.py
```

**Output includes:**
- Environment information (platform, Python version, architecture)
- Dependency verification status
- Model presence and size
- Transcription results with timing metrics
- Detailed recommendations for missing components

### 3. **generate_test_report.py**
Comprehensive report generator that:
- Loads latest test results
- Generates detailed formatted reports
- Shows what passed and what failed
- Provides platform-specific installation commands

**Usage:**
```bash
python3 generate_test_report.py
```

## GitHub Actions Workflows

### Primary Workflow: `test-transcription-cross-platform.yml`

This workflow runs cross-platform tests automatically on:
- **Platforms**: Ubuntu Latest, macOS Latest, Windows Latest
- **Python Versions**: 3.9, 3.10, 3.11
- **Models**: fast, precise
- **Total Combinations**: 18 test runs per trigger

**Triggers:**
- Push to `main` and `feature/**` branches
- Pull requests to `main`
- Daily schedule (2 AM UTC)
- Manual workflow dispatch

**Environment Setup:**
Each platform installs:
1. System dependencies:
   - Ubuntu: `ffmpeg libsndfile1 libffi-dev`
   - macOS: `ffmpeg libsndfile`
   - Windows: `ffmpeg`

2. Python dependencies from platform-specific requirements:
   - macOS ARM64: `environments/requirements_macOS_arm64.txt`
   - macOS x86_64: `environments/requirements_macOS_x86_64.txt`
   - Linux: `environments/requirements_linux.txt`
   - Windows: `environments/requirements_win_cpu.txt`

3. Test execution:
   - Validates all dependencies
   - Verifies models exist
   - Checks test audio file
   - Runs transcription tests
   - Collects and uploads results

## Local Testing

### Quick Test (Current Environment)
```bash
# Run transcription tests with current Python
python3 simple_platform_test.py

# This will:
# 1. Check all dependencies
# 2. Verify system tools
# 3. Test both models
# 4. Generate report
```

### Detailed Test
```bash
# Run individual transcription test
python3 test_transcription.py --audio test_resources/test_audio.mp3 --verbose

# Or let it auto-detect test audio
python3 test_transcription.py --verbose
```

### View Test Results
```bash
# Generate comprehensive report from latest test results
python3 generate_test_report.py
```

## Requirements Files

Each platform has a dedicated requirements file ensuring correct dependency installation:

### macOS ARM64 (`requirements_macOS_arm64.txt`)
```
torch==2.8
torchaudio==2.8
faster-whisper
pyannote.audio>=4
customtkinter
AdvancedHTMLParser
Pillow
PyYAML
...
```

### Linux (`requirements_linux.txt`)
```
torch>=2.0
torchaudio>=2.0
faster-whisper
pyannote.audio>=3.3.2
customtkinter
AdvancedHTMLParser
...
```

### Windows (`requirements_win_cpu.txt`)
```
torch>=2.0
torchaudio>=2.0
faster-whisper
pyannote.audio>=4.0
customtkinter
cpufeature
...
```

## Test Results Interpretation

### Success Indicators
✓ All dependencies installed
✓ System tools available (ffmpeg)
✓ Models present and valid
✓ Test audio file exists
✓ Both models transcribe successfully
✓ Output files generated (JSON, HTML)

### Common Failures and Solutions

**Missing Python Dependencies**
```bash
# macOS ARM64
pip install -r environments/requirements_macOS_arm64.txt

# macOS x86_64
pip install -r environments/requirements_macOS_x86_64.txt

# Linux
pip install -r environments/requirements_linux.txt

# Windows
pip install -r environments/requirements_win_cpu.txt
```

**Missing System Dependencies**

macOS:
```bash
brew install ffmpeg libsndfile
```

Linux:
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg libsndfile1 libffi-dev
```

Windows:
```bash
choco install ffmpeg -y
```

**Models Not Found**
- Ensure `models/fast/` directory contains `config.json` and `model.bin`
- Ensure `models/precise/` directory contains `config.json` and `model.bin`
- Check file sizes are reasonable (fast ~461MB, precise ~2.9GB)

**Test Audio Missing**
- Place test audio at `test_resources/test_audio.mp3`
- Minimum duration: ~30 seconds
- Format: MP3, WAV, or other ffmpeg-supported formats

## Performance Metrics

The test suite captures and reports:
- **Model Load Time**: Time to initialize Whisper model
- **Transcription Time**: Time to transcribe entire audio file
- **Segments Count**: Number of transcript segments generated
- **Language Detection**: Detected language and probability
- **Audio Duration**: Total duration of input audio

Example results from macOS ARM64:
```
FAST Model:
  Load Time: 0.66s
  Transcription Time: 4.92s
  Segments: 8
  Language: en (100% probability)

PRECISE Model:
  Load Time: 3.76s
  Transcription Time: 19.30s
  Segments: 4
  Language: en (100% probability)
```

## GitHub Actions Best Practices

1. **Matrix Strategy**: Tests run in parallel for faster feedback
2. **Fail-fast Disabled**: Allows identifying failures across all combinations
3. **Artifact Upload**: Test results preserved for 30 days
4. **Caching**: Python dependencies cached to speed up subsequent runs
5. **Platform Detection**: Automatic requirements file selection per platform

## Continuous Improvement

The test infrastructure:
- Validates transcription quality across platforms
- Ensures consistency between fast and precise models
- Detects environment setup issues early
- Provides detailed diagnostics for troubleshooting
- Tracks performance metrics over time

## Troubleshooting

### Test hangs or times out
- Check system resources (disk space, memory)
- Verify models are not corrupted
- Try running with verbose flag: `--verbose`

### Float16 compute type warnings
These are expected on macOS ARM64 and CPU-only systems:
- Automatically falls back to float32
- No action required
- Transcription quality unaffected

### Missing imports during tests
- Verify requirements file installed: `pip install -r environments/requirements_*.txt`
- Check Python version compatibility (3.9-3.11)
- Ensure virtual environment is activated if using one

## Next Steps

1. **Local Testing**: Run `python3 simple_platform_test.py` to validate your environment
2. **Fix Issues**: Follow recommendations from test report
3. **GitHub Actions**: Push changes to trigger CI/CD workflow
4. **Review Results**: Check artifacts after workflow completes
5. **Iterate**: Make improvements and re-test

