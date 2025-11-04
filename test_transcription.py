#!/usr/bin/env python3
"""
Standalone Test Script for noScribe Transcription
Tests both 'fast' and 'precise' models without invoking the GUI
Runs entirely in the terminal and works across Linux, macOS, and Windows
"""

import os
import sys
import platform
import argparse
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TranscriptionTester:
    """Test transcription using faster-whisper with local models"""

    def __init__(self, verbose: bool = True, output_dir: Optional[str] = None):
        self.verbose = verbose
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "noscribe_tests"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: Dict[str, any] = {}
        self.app_dir = Path(__file__).parent.absolute()
        self.models_dir = self.app_dir / "models"

    def log(self, message: str, level: str = "INFO"):
        """Print timestamped log message"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        level_str = f"[{level}]"
        print(f"{timestamp} {level_str:<8} {message}")

    def validate_environment(self) -> bool:
        """Validate that all required dependencies are installed"""
        self.log("Validating environment...")

        required_modules = [
            ("faster_whisper", "faster-whisper"),
            ("torch", "torch"),
            ("ffmpeg", "ffmpeg"),  # Note: this is checked differently
        ]

        all_valid = True
        for module_name, package_name in required_modules:
            if module_name == "ffmpeg":
                # Check for ffmpeg binary
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                if result.returncode != 0:
                    self.log(f"❌ {package_name} not found or not in PATH", "ERROR")
                    all_valid = False
                else:
                    self.log(f"✓ {package_name} available")
            else:
                try:
                    __import__(module_name)
                    self.log(f"✓ {package_name} installed")
                except ImportError:
                    self.log(f"❌ {package_name} not installed", "ERROR")
                    all_valid = False

        return all_valid

    def check_models(self) -> Dict[str, Path]:
        """Check for available models and return their paths"""
        self.log("Checking available models...")
        available_models = {}

        model_types = {
            "fast": self.models_dir / "fast",
            "precise": self.models_dir / "precise"
        }

        for model_type, model_path in model_types.items():
            if model_path.exists():
                if (model_path / "config.json").exists() and (model_path / "model.bin").exists():
                    available_models[model_type] = model_path
                    self.log(f"✓ '{model_type}' model found at {model_path}")
                else:
                    self.log(f"❌ '{model_type}' model incomplete (missing config.json or model.bin)", "WARNING")
            else:
                self.log(f"❌ '{model_type}' model not found at {model_path}", "WARNING")

        if not available_models:
            self.log("No valid models found!", "ERROR")
            return {}

        return available_models

    def create_test_audio(self) -> Optional[Path]:
        """Get or create a test audio file"""
        # First, check if real test audio exists in the repo
        repo_test_audio = self.app_dir / "test_resources" / "test_audio.mp3"
        if repo_test_audio.exists():
            self.log(f"Using real test audio: {repo_test_audio}")
            size_mb = repo_test_audio.stat().st_size / (1024 * 1024)
            self.log(f"  File size: {size_mb:.2f} MB")
            return repo_test_audio

        # Fallback: try to use any test audio in test_resources
        test_resources_dir = self.app_dir / "test_resources"
        if test_resources_dir.exists():
            for audio_file in test_resources_dir.glob("*.mp3"):
                self.log(f"Using test audio: {audio_file}")
                size_mb = audio_file.stat().st_size / (1024 * 1024)
                self.log(f"  File size: {size_mb:.2f} MB")
                return audio_file
            for audio_file in test_resources_dir.glob("*.wav"):
                self.log(f"Using test audio: {audio_file}")
                size_mb = audio_file.stat().st_size / (1024 * 1024)
                self.log(f"  File size: {size_mb:.2f} MB")
                return audio_file

        # Last resort: create a simple test audio file using ffmpeg
        self.log("Creating synthetic test audio file...")
        test_audio_path = self.output_dir / "test_audio.wav"

        if test_audio_path.exists():
            self.log(f"Using existing test audio: {test_audio_path}")
            return test_audio_path

        try:
            cmd = [
                "ffmpeg",
                "-f", "lavfi",
                "-i", "sine=frequency=1000:duration=5",
                "-q:a", "9",
                "-acodec", "libmp3lame",
                "-y",  # Overwrite output file
                str(test_audio_path)
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode != 0:
                self.log(f"Failed to create test audio: {result.stderr.decode()}", "ERROR")
                return None

            if test_audio_path.exists():
                size_mb = test_audio_path.stat().st_size / (1024 * 1024)
                self.log(f"✓ Synthetic test audio created: {test_audio_path} ({size_mb:.2f} MB)")
                return test_audio_path
        except Exception as e:
            self.log(f"Error creating test audio: {e}", "ERROR")
            return None

        return None

    def transcribe_with_model(self, audio_path: Path, model_name: str, model_path: Path) -> Optional[Dict]:
        """Transcribe audio using specified model"""
        self.log(f"Transcribing with '{model_name}' model...")

        try:
            from faster_whisper import WhisperModel

            # Determine device and compute type with fallback
            device = "auto"
            compute_type = "float16"  # Default; will fall back on error

            # Load model with compute type fallback
            self.log(f"  Loading model from {model_path}...")
            start_time = time.time()

            try:
                self.log(f"  Device: {device}, Compute Type: {compute_type}")
                model = WhisperModel(
                    str(model_path),
                    device=device,
                    compute_type=compute_type,
                    local_files_only=True
                )
            except ValueError as e:
                # Fall back to float32 if float16 fails
                if "float16" in str(e) or "compute type" in str(e):
                    self.log(f"  Float16 not supported, falling back to float32")
                    compute_type = "float32"
                    model = WhisperModel(
                        str(model_path),
                        device=device,
                        compute_type=compute_type,
                        local_files_only=True
                    )
                else:
                    raise

            load_time = time.time() - start_time
            self.log(f"  Model loaded in {load_time:.2f}s")

            # Transcribe
            self.log(f"  Starting transcription...")
            start_time = time.time()

            segments, info = model.transcribe(
                str(audio_path),
                beam_size=5,
                word_timestamps=True,
                language="en"
            )

            # Convert generator to list to get all segments
            segments_list = list(segments)
            transcribe_time = time.time() - start_time

            self.log(f"  Transcription completed in {transcribe_time:.2f}s")
            self.log(f"  Detected language: {info.language} (probability: {info.language_probability:.2f})")
            self.log(f"  Number of segments: {len(segments_list)}")

            # Build output
            result = {
                "model": model_name,
                "model_path": str(model_path),
                "audio_file": str(audio_path),
                "language": info.language,
                "language_probability": float(info.language_probability),
                "duration": float(info.duration),
                "load_time_seconds": load_time,
                "transcription_time_seconds": transcribe_time,
                "segments_count": len(segments_list),
                "segments": []
            }

            # Extract segment details
            for segment in segments_list:
                seg_data = {
                    "id": segment.id,
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": segment.text,
                    "word_count": len(segment.text.split())
                }

                # Include word-level timestamps if available
                if hasattr(segment, "words") and segment.words:
                    seg_data["words"] = [
                        {
                            "word": w.word,
                            "start": float(w.start),
                            "end": float(w.end),
                            "probability": float(getattr(w, "probability", 0.0))
                        }
                        for w in segment.words
                    ]

                result["segments"].append(seg_data)

            self.log(f"✓ Transcription successful for '{model_name}'", "SUCCESS")
            return result

        except Exception as e:
            self.log(f"✗ Error during transcription: {e}", "ERROR")
            import traceback
            if self.verbose:
                traceback.print_exc()
            return None

    def save_results(self, results: Dict) -> Path:
        """Save results to JSON and HTML files"""
        self.log("Saving results...")

        # Save JSON results
        json_path = self.output_dir / "transcription_results.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        self.log(f"✓ Results saved to {json_path}")

        # Create HTML report
        html_path = self.output_dir / "transcription_report.html"
        html_content = self._generate_html_report(results)
        with open(html_path, "w") as f:
            f.write(html_content)
        self.log(f"✓ Report saved to {html_path}")

        return json_path

    def _generate_html_report(self, results: Dict) -> str:
        """Generate an HTML report of transcription results"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>noScribe Transcription Test Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background-color: #333;
            color: white;
            padding: 20px;
            border-radius: 5px;
        }
        .model-section {
            background-color: white;
            margin: 20px 0;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .model-title {
            background-color: #007bff;
            color: white;
            padding: 10px;
            border-radius: 3px;
            margin-bottom: 10px;
            font-size: 16px;
            font-weight: bold;
        }
        .metadata {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        .metadata-item {
            border-left: 3px solid #007bff;
            padding-left: 10px;
        }
        .metadata-item label {
            font-weight: bold;
            color: #333;
        }
        .metadata-item value {
            color: #666;
        }
        .segments-container {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 10px;
        }
        .segment {
            margin: 10px 0;
            padding: 10px;
            background-color: #f9f9f9;
            border-left: 3px solid #28a745;
            border-radius: 3px;
        }
        .segment-time {
            color: #666;
            font-size: 12px;
        }
        .segment-text {
            margin: 5px 0;
            color: #333;
        }
        .summary {
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .success {
            color: #28a745;
        }
        .error {
            color: #dc3545;
        }
        .timestamp {
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>noScribe Transcription Test Report</h1>
        <p class="timestamp">Generated: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """</p>
        <p class="timestamp">Platform: """ + platform.system() + """ """ + platform.release() + """</p>
    </div>

    <div class="summary">
        <h2>Test Summary</h2>
"""

        # Add test summary
        for model_name, model_result in results.get("models", {}).items():
            if model_result:
                status = '<span class="success">✓ Success</span>'
                html += f"<p><strong>{model_name}:</strong> {status}</p>"
            else:
                status = '<span class="error">✗ Failed</span>'
                html += f"<p><strong>{model_name}:</strong> {status}</p>"

        html += """
    </div>
"""

        # Add model details
        for model_name, model_result in results.get("models", {}).items():
            if not model_result:
                continue

            html += f"""
    <div class="model-section">
        <div class="model-title">{model_name.upper()} Model Results</div>
        <div class="metadata">
            <div class="metadata-item">
                <label>Language:</label><br/>
                <value>{model_result.get("language", "N/A")}</value>
            </div>
            <div class="metadata-item">
                <label>Load Time:</label><br/>
                <value>{model_result.get("load_time_seconds", 0):.2f}s</value>
            </div>
            <div class="metadata-item">
                <label>Transcription Time:</label><br/>
                <value>{model_result.get("transcription_time_seconds", 0):.2f}s</value>
            </div>
            <div class="metadata-item">
                <label>Total Segments:</label><br/>
                <value>{model_result.get("segments_count", 0)}</value>
            </div>
        </div>

        <h3>Transcription:</h3>
        <div class="segments-container">
"""

            # Add segments
            for segment in model_result.get("segments", [])[:20]:  # Limit to first 20 segments in HTML
                html += f"""
            <div class="segment">
                <div class="segment-time">[{segment['start']:.2f}s - {segment['end']:.2f}s]</div>
                <div class="segment-text">{segment['text']}</div>
            </div>
"""

            if len(model_result.get("segments", [])) > 20:
                html += f'<p><em>... and {len(model_result.get("segments", [])) - 20} more segments (see JSON for details)</em></p>'

            html += """
        </div>
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    def run_tests(self, audio_path: Optional[Path] = None) -> bool:
        """Run all tests"""
        self.log("=" * 70)
        self.log("noScribe Standalone Transcription Test", "INFO")
        self.log("=" * 70)
        self.log(f"Platform: {platform.system()} {platform.release()}")
        self.log(f"Python: {platform.python_version()}")
        self.log("")

        # Validate environment
        if not self.validate_environment():
            self.log("Environment validation failed!", "ERROR")
            return False

        self.log("")

        # Check models
        available_models = self.check_models()
        if not available_models:
            self.log("No available models found!", "ERROR")
            return False

        self.log("")

        # Create or use provided test audio
        if audio_path is None:
            audio_path = self.create_test_audio()
        else:
            audio_path = Path(audio_path)

        if not audio_path or not audio_path.exists():
            self.log(f"Test audio not found: {audio_path}", "ERROR")
            return False

        self.log("")

        # Run transcription tests
        results = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "audio_file": str(audio_path),
            "models": {}
        }

        for model_type, model_path in available_models.items():
            self.log("")
            result = self.transcribe_with_model(audio_path, model_type, model_path)
            results["models"][model_type] = result

        # Save results
        self.log("")
        self.save_results(results)

        # Summary
        self.log("")
        self.log("=" * 70)
        self.log("Test Summary", "INFO")
        self.log("=" * 70)

        successful = 0
        failed = 0

        for model_name, result in results["models"].items():
            if result:
                self.log(f"✓ {model_name}: SUCCESS", "SUCCESS")
                successful += 1
            else:
                self.log(f"✗ {model_name}: FAILED", "ERROR")
                failed += 1

        self.log("")
        self.log(f"Results: {successful} passed, {failed} failed")
        self.log(f"Output directory: {self.output_dir}")
        self.log("=" * 70)

        return failed == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Standalone transcription test for noScribe"
    )
    parser.add_argument(
        "--audio",
        type=str,
        default=None,
        help="Path to audio file to transcribe (default: generates test audio)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for results"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Create tester and run tests
    tester = TranscriptionTester(
        verbose=args.verbose,
        output_dir=args.output
    )

    success = tester.run_tests(audio_path=args.audio)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
