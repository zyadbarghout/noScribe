#!/usr/bin/env python3
"""
Platform-Specific Test Runner for noScribe
Tests transcription on the current platform with proper environment setup
Generates detailed reports showing what passed/failed and why
"""

import os
import sys
import platform
import subprocess
import json
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
import venv


class PlatformTestRunner:
    """Run platform-specific tests with proper environment setup"""

    PLATFORM_NAMES = {
        "Linux": "linux",
        "Darwin": "macos",
        "Windows": "windows"
    }

    def __init__(self):
        self.current_platform = platform.system()
        self.current_arch = platform.machine()
        self.python_version = platform.python_version()
        self.results: Dict = {}
        self.app_dir = Path(__file__).parent.absolute()
        self.test_dir = self.app_dir / "platform_test_results"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.venv_dir = self.test_dir / f"venv_{self.PLATFORM_NAMES.get(self.current_platform, 'unknown')}"

    def log(self, message: str, level: str = "INFO", prefix: str = ""):
        """Print timestamped log message"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        level_str = f"[{level}]"
        prefix_str = f"[{prefix}]" if prefix else ""
        print(f"{timestamp} {level_str:<8} {prefix_str:<20} {message}")

    def print_section(self, title: str):
        """Print a formatted section header"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")

    def get_requirements_file(self) -> Optional[Path]:
        """Get the correct requirements file for the current platform"""
        self.log(f"Detecting platform: {self.current_platform} {self.current_arch}")

        if self.current_platform == "Darwin":  # macOS
            if self.current_arch == "arm64":
                req_file = self.app_dir / "environments" / "requirements_macOS_arm64.txt"
            else:
                req_file = self.app_dir / "environments" / "requirements_macOS_x86_64.txt"
        elif self.current_platform == "Linux":
            req_file = self.app_dir / "environments" / "requirements_linux.txt"
        elif self.current_platform == "Windows":
            req_file = self.app_dir / "environments" / "requirements_win_cpu.txt"
        else:
            self.log(f"Unsupported platform: {self.current_platform}", "ERROR")
            return None

        if req_file.exists():
            self.log(f"Using requirements file: {req_file.name}")
            return req_file
        else:
            self.log(f"Requirements file not found: {req_file}", "ERROR")
            return None

    def setup_environment(self) -> bool:
        """Set up a clean Python virtual environment for testing"""
        self.log("Setting up test environment...")

        try:
            # Create virtual environment
            if self.venv_dir.exists():
                self.log(f"Removing existing venv: {self.venv_dir}")
                shutil.rmtree(self.venv_dir)

            self.log(f"Creating virtual environment: {self.venv_dir}")
            venv.create(self.venv_dir, with_pip=True)

            # Get Python executable in venv
            if self.current_platform == "Windows":
                python_exe = self.venv_dir / "Scripts" / "python.exe"
                pip_exe = self.venv_dir / "Scripts" / "pip.exe"
            else:
                python_exe = self.venv_dir / "bin" / "python"
                pip_exe = self.venv_dir / "bin" / "pip"

            if not python_exe.exists():
                self.log(f"Failed to create venv, python executable not found", "ERROR")
                return False

            self.log(f"✓ Virtual environment created")

            # Upgrade pip
            self.log("Upgrading pip...")
            result = subprocess.run(
                [str(pip_exe), "install", "--upgrade", "pip", "setuptools", "wheel"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                self.log(f"Failed to upgrade pip: {result.stderr}", "ERROR")
                return False

            # Install requirements
            req_file = self.get_requirements_file()
            if not req_file:
                return False

            self.log(f"Installing requirements from {req_file.name}...")
            result = subprocess.run(
                [str(pip_exe), "install", "-r", str(req_file)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )

            if result.returncode != 0:
                self.log(f"Failed to install requirements", "ERROR")
                self.log(f"Output: {result.stdout[-500:] if result.stdout else ''}", "ERROR")
                self.log(f"Errors: {result.stderr[-500:] if result.stderr else ''}", "ERROR")
                return False

            self.log(f"✓ Requirements installed successfully")

            # Store python executable path
            self.python_exe = python_exe
            self.pip_exe = pip_exe

            return True

        except Exception as e:
            self.log(f"Error setting up environment: {e}", "ERROR")
            return False

    def verify_dependencies(self) -> Dict[str, bool]:
        """Verify that all required dependencies are installed"""
        self.log("Verifying dependencies...")

        required_packages = [
            "faster_whisper",
            "torch",
            "torchaudio",
            "pyannote",
            "customtkinter",
            "PIL",
            "yaml"
        ]

        verification_results = {}

        for package in required_packages:
            try:
                result = subprocess.run(
                    [str(self.python_exe), "-c", f"import {package}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                success = result.returncode == 0
                verification_results[package] = success
                status = "✓" if success else "✗"
                self.log(f"{status} {package}", prefix="DEPS")
            except Exception as e:
                self.log(f"✗ {package}: {e}", prefix="DEPS")
                verification_results[package] = False

        return verification_results

    def check_system_dependencies(self) -> Dict[str, bool]:
        """Check for required system dependencies"""
        self.log("Checking system dependencies...")

        system_deps = {}

        # Check ffmpeg
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            system_deps["ffmpeg"] = result.returncode == 0
            status = "✓" if system_deps["ffmpeg"] else "✗"
            self.log(f"{status} ffmpeg", prefix="SYSDEPS")
        except Exception:
            system_deps["ffmpeg"] = False
            self.log(f"✗ ffmpeg", prefix="SYSDEPS")

        return system_deps

    def check_models(self) -> Dict[str, bool]:
        """Check if required models are present"""
        self.log("Checking models...")

        models_dir = self.app_dir / "models"
        models_status = {}

        for model_type in ["fast", "precise"]:
            model_path = models_dir / model_type
            config_exists = (model_path / "config.json").exists()
            model_exists = (model_path / "model.bin").exists()

            is_valid = config_exists and model_exists
            models_status[model_type] = is_valid

            status = "✓" if is_valid else "✗"
            self.log(f"{status} {model_type} model", prefix="MODELS")

            if not is_valid:
                if not config_exists:
                    self.log(f"  Missing: config.json", prefix="MODELS")
                if not model_exists:
                    self.log(f"  Missing: model.bin", prefix="MODELS")

        return models_status

    def run_transcription_tests(self) -> Dict[str, any]:
        """Run transcription tests using the test_transcription.py script"""
        self.log("Running transcription tests...")

        test_script = self.app_dir / "test_transcription.py"
        audio_file = self.app_dir / "test_resources" / "test_audio.mp3"

        if not test_script.exists():
            self.log(f"Test script not found: {test_script}", "ERROR")
            return {}

        if not audio_file.exists():
            self.log(f"Test audio not found: {audio_file}", "ERROR")
            return {}

        test_output_dir = self.test_dir / f"transcription_results_{int(time.time())}"
        test_output_dir.mkdir(parents=True, exist_ok=True)

        try:
            cmd = [
                str(self.python_exe),
                str(test_script),
                "--audio", str(audio_file),
                "--output", str(test_output_dir),
                "--verbose"
            ]

            self.log(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )

            # Print test output
            if result.stdout:
                print(result.stdout)

            if result.stderr:
                print(f"STDERR:\n{result.stderr}", file=sys.stderr)

            # Load results
            results_file = test_output_dir / "transcription_results.json"
            if results_file.exists():
                with open(results_file, "r") as f:
                    test_results = json.load(f)
                    test_results["success"] = result.returncode == 0
                    test_results["test_output_dir"] = str(test_output_dir)
                    return test_results
            else:
                self.log(f"Results file not found: {results_file}", "ERROR")
                return {"success": False, "error": "Results file not generated"}

        except subprocess.TimeoutExpired:
            self.log("Transcription tests timed out after 10 minutes", "ERROR")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            self.log(f"Error running tests: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def generate_comprehensive_report(self, results: Dict) -> str:
        """Generate a comprehensive test report"""
        report = []

        report.append("=" * 80)
        report.append("PLATFORM TEST REPORT")
        report.append("=" * 80)
        report.append("")

        # System Information
        report.append("SYSTEM INFORMATION")
        report.append("-" * 80)
        report.append(f"Platform:         {self.current_platform} {self.current_arch}")
        report.append(f"Python Version:   {self.python_version}")
        report.append(f"Test Timestamp:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Python Dependencies
        if "dependencies" in results:
            report.append("PYTHON DEPENDENCIES")
            report.append("-" * 80)
            for dep, status in results["dependencies"].items():
                icon = "✓" if status else "✗"
                report.append(f"{icon} {dep:<40} {'INSTALLED' if status else 'MISSING'}")
            report.append("")

        # System Dependencies
        if "system_deps" in results:
            report.append("SYSTEM DEPENDENCIES")
            report.append("-" * 80)
            for dep, status in results["system_deps"].items():
                icon = "✓" if status else "✗"
                report.append(f"{icon} {dep:<40} {'AVAILABLE' if status else 'NOT FOUND'}")
            report.append("")

        # Models
        if "models" in results:
            report.append("MODELS")
            report.append("-" * 80)
            for model, status in results["models"].items():
                icon = "✓" if status else "✗"
                report.append(f"{icon} {model:<40} {'PRESENT' if status else 'MISSING'}")
            report.append("")

        # Test Results
        if "transcription" in results:
            transcription_results = results["transcription"]
            report.append("TRANSCRIPTION TESTS")
            report.append("-" * 80)

            if transcription_results.get("success"):
                report.append("✓ Tests completed successfully")
                report.append("")

                # Model results
                for model_name, model_result in transcription_results.get("models", {}).items():
                    if model_result:
                        report.append(f"\n{model_name.upper()} Model:")
                        report.append(f"  Language:           {model_result.get('language', 'N/A')}")
                        report.append(f"  Language Probability: {model_result.get('language_probability', 0):.2%}")
                        report.append(f"  Duration:           {model_result.get('duration', 0):.2f}s")
                        report.append(f"  Load Time:          {model_result.get('load_time_seconds', 0):.2f}s")
                        report.append(f"  Transcription Time: {model_result.get('transcription_time_seconds', 0):.2f}s")
                        report.append(f"  Segments:           {model_result.get('segments_count', 0)}")

                        # Show first few segments
                        if model_result.get("segments"):
                            report.append(f"  Sample Segments:")
                            for seg in model_result.get("segments", [])[:3]:
                                report.append(f"    [{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}")
                    else:
                        report.append(f"\n✗ {model_name.upper()} Model:")
                        report.append(f"  FAILED - Check logs for details")
            else:
                report.append("✗ Tests failed")
                error = transcription_results.get("error", "Unknown error")
                report.append(f"  Error: {error}")

            report.append("")

        # Summary
        report.append("=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)

        # Count passes and failures
        passes = 0
        failures = 0

        if results.get("dependencies"):
            dep_passes = sum(1 for v in results["dependencies"].values() if v)
            dep_total = len(results["dependencies"])
            report.append(f"Dependencies:     {dep_passes}/{dep_total} passed")
            passes += dep_passes
            failures += (dep_total - dep_passes)

        if results.get("system_deps"):
            sys_passes = sum(1 for v in results["system_deps"].values() if v)
            sys_total = len(results["system_deps"])
            report.append(f"System Deps:      {sys_passes}/{sys_total} passed")
            passes += sys_passes
            failures += (sys_total - sys_passes)

        if results.get("models"):
            model_passes = sum(1 for v in results["models"].values() if v)
            model_total = len(results["models"])
            report.append(f"Models:           {model_passes}/{model_total} present")
            passes += model_passes
            failures += (model_total - model_passes)

        if results.get("transcription"):
            if results["transcription"].get("success"):
                test_passes = sum(1 for v in results["transcription"].get("models", {}).values() if v)
                test_total = len(results["transcription"].get("models", {}))
                report.append(f"Transcription:    {test_passes}/{test_total} passed")
                passes += test_passes
                failures += (test_total - test_passes)
            else:
                failures += 1
                report.append(f"Transcription:    FAILED")

        report.append("")
        report.append(f"TOTAL:            {passes} passed, {failures} failed")
        report.append("=" * 80)

        return "\n".join(report)

    def save_report(self, report: str):
        """Save report to file"""
        report_file = self.test_dir / f"test_report_{int(time.time())}.txt"
        with open(report_file, "w") as f:
            f.write(report)
        self.log(f"Report saved to: {report_file}")
        return report_file

    def run_all_tests(self) -> bool:
        """Run all platform tests"""
        self.print_section("NOSCRIBE PLATFORM TEST SUITE")
        self.log(f"Platform: {self.current_platform} {self.current_arch}")
        self.log(f"Python: {self.python_version}")

        results = {
            "platform": self.current_platform,
            "architecture": self.current_arch,
            "python_version": self.python_version,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Step 1: Setup environment
        self.print_section("1. ENVIRONMENT SETUP")
        if not self.setup_environment():
            self.log("Environment setup failed", "ERROR")
            return False

        # Step 2: Verify dependencies
        self.print_section("2. DEPENDENCY VERIFICATION")
        results["dependencies"] = self.verify_dependencies()

        # Step 3: Check system dependencies
        self.print_section("3. SYSTEM DEPENDENCIES")
        results["system_deps"] = self.check_system_dependencies()

        # Step 4: Check models
        self.print_section("4. MODEL VERIFICATION")
        results["models"] = self.check_models()

        # Step 5: Run transcription tests
        self.print_section("5. TRANSCRIPTION TESTS")
        results["transcription"] = self.run_transcription_tests()

        # Generate and save report
        self.print_section("6. TEST REPORT")
        report = self.generate_comprehensive_report(results)
        print(report)
        self.save_report(report)

        # Save results as JSON
        results_file = self.test_dir / f"test_results_{int(time.time())}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        self.log(f"Results saved to: {results_file}")

        # Return overall success
        overall_success = all([
            all(results.get("dependencies", {}).values()),
            all(results.get("system_deps", {}).values()),
            all(results.get("models", {}).values()),
            results.get("transcription", {}).get("success", False)
        ])

        return overall_success


def main():
    """Main entry point"""
    runner = PlatformTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
