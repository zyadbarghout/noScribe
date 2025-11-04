#!/usr/bin/env python3
"""
Cross-Platform Test Runner for noScribe
Tests transcription on multiple platforms with detailed metrics
"""

import os
import sys
import platform
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import time


class CrossPlatformTestRunner:
    """Run and manage cross-platform tests"""

    PLATFORMS = {
        "Linux": "linux",
        "Darwin": "macos",
        "Windows": "windows"
    }

    MODELS = ["fast", "precise"]

    def __init__(self, test_script: str = "test_transcription.py"):
        self.test_script = test_script
        self.script_path = Path(__file__).parent / test_script
        self.current_platform = platform.system()
        self.results: List[Dict] = []

    def log(self, message: str, level: str = "INFO"):
        """Print timestamped log message"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        level_str = f"[{level}]"
        print(f"{timestamp} {level_str:<8} {message}")

    def run_local_test(self, audio_path: Optional[str] = None) -> Optional[Dict]:
        """Run test on the current platform"""
        self.log(f"Running test on {self.current_platform}...")

        try:
            cmd = [
                sys.executable,
                str(self.script_path),
                "--verbose"
            ]

            if audio_path:
                cmd.extend(["--audio", audio_path])

            output_dir = Path(tempfile.gettempdir()) / f"noscribe_test_{int(time.time())}"
            cmd.extend(["--output", str(output_dir)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            # Print test output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"STDERR: {result.stderr}", file=sys.stderr)

            # Load results
            results_file = output_dir / "transcription_results.json"
            if results_file.exists():
                with open(results_file, "r") as f:
                    test_result = json.load(f)
                    test_result["success"] = result.returncode == 0
                    test_result["platform_detected"] = self.current_platform
                    self.log(f"✓ Test completed successfully", "SUCCESS")
                    return test_result
            else:
                self.log(f"Results file not found: {results_file}", "ERROR")
                return None

        except subprocess.TimeoutExpired:
            self.log("Test timed out after 10 minutes", "ERROR")
            return None
        except Exception as e:
            self.log(f"Error running test: {e}", "ERROR")
            return None

    def generate_github_actions_matrix(self) -> Dict:
        """Generate GitHub Actions matrix configuration"""
        matrix = {
            "os": ["ubuntu-latest", "macos-latest", "windows-latest"],
            "python-version": ["3.9", "3.10", "3.11"],
            "model": self.MODELS
        }
        return matrix

    def save_test_results(self, results: Dict, output_file: str = "test_results.json"):
        """Save test results to file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        self.log(f"Results saved to {output_path}")

    def print_summary(self, results: Dict):
        """Print test summary"""
        self.log("=" * 70)
        self.log("Cross-Platform Test Summary", "INFO")
        self.log("=" * 70)

        if results.get("success"):
            self.log(f"✓ Platform: {results.get('platform')}", "SUCCESS")
            self.log(f"  Python: {results.get('python_version')}")
            self.log(f"  Timestamp: {results.get('timestamp')}")

            for model_name, model_result in results.get("models", {}).items():
                if model_result:
                    self.log(f"\n  {model_name.upper()}:")
                    self.log(f"    Load Time: {model_result.get('load_time_seconds', 0):.2f}s")
                    self.log(f"    Transcription Time: {model_result.get('transcription_time_seconds', 0):.2f}s")
                    self.log(f"    Segments: {model_result.get('segments_count', 0)}")
                    self.log(f"    Language: {model_result.get('language', 'N/A')}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cross-platform test runner for noScribe"
    )
    parser.add_argument(
        "--audio",
        type=str,
        default=None,
        help="Path to audio file to test"
    )
    parser.add_argument(
        "--github-matrix",
        action="store_true",
        help="Print GitHub Actions matrix configuration"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="test_results.json",
        help="Output file for results"
    )

    args = parser.parse_args()

    runner = CrossPlatformTestRunner()

    if args.github_matrix:
        matrix = runner.generate_github_actions_matrix()
        print(json.dumps(matrix, indent=2))
        return

    # Run local test
    runner.log("Starting cross-platform test runner...")
    runner.log(f"Platform: {runner.current_platform}")
    runner.log("")

    results = runner.run_local_test(audio_path=args.audio)

    if results:
        runner.print_summary(results)
        runner.save_test_results(results, args.output)
        sys.exit(0 if results.get("success") else 1)
    else:
        runner.log("Test failed to complete", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
