#!/usr/bin/env python3
"""
Simplified Platform Test Runner
Tests transcription on current platform without venv setup
Generates detailed reports showing what passed/failed and why
"""

import os
import sys
import platform
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, Optional


class SimplePlatformTestRunner:
    """Run platform tests using current environment"""

    PLATFORM_NAMES = {
        "Linux": "linux",
        "Darwin": "macos",
        "Windows": "windows"
    }

    def __init__(self):
        self.current_platform = platform.system()
        self.current_arch = platform.machine()
        self.python_version = platform.python_version()
        self.app_dir = Path(__file__).parent.absolute()
        self.test_dir = self.app_dir / "platform_test_results"
        self.test_dir.mkdir(parents=True, exist_ok=True)

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

    def verify_dependencies(self) -> Dict[str, bool]:
        """Verify that all required dependencies are installed"""
        self.log("Verifying Python dependencies...")

        required_packages = {
            "faster_whisper": "faster-whisper",
            "torch": "torch",
            "torchaudio": "torchaudio",
            "pyannote": "pyannote.audio",
            "customtkinter": "customtkinter",
            "PIL": "Pillow",
            "yaml": "PyYAML",
            "AdvancedHTMLParser": "AdvancedHTMLParser",
            "appdirs": "appdirs"
        }

        verification_results = {}

        for import_name, display_name in required_packages.items():
            try:
                __import__(import_name)
                verification_results[display_name] = True
                self.log(f"✓ {display_name}", prefix="DEPS")
            except ImportError:
                verification_results[display_name] = False
                self.log(f"✗ {display_name} - NOT INSTALLED", prefix="DEPS", level="WARNING")

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
            self.log(f"✗ ffmpeg - NOT FOUND", prefix="SYSDEPS", level="WARNING")

        return system_deps

    def check_models(self) -> Dict[str, bool]:
        """Check if required models are present"""
        self.log("Checking models...")

        models_dir = self.app_dir / "models"
        models_status = {}

        for model_type in ["fast", "precise"]:
            model_path = models_dir / model_type
            config_exists = (model_path / "config.json").exists()
            model_bin_exists = (model_path / "model.bin").exists()

            is_valid = config_exists and model_bin_exists
            models_status[model_type] = is_valid

            if is_valid:
                size_mb = (model_path / "model.bin").stat().st_size / (1024 * 1024)
                self.log(f"✓ {model_type.upper()} model ({size_mb:.1f} MB)", prefix="MODELS")
            else:
                self.log(f"✗ {model_type.upper()} model - MISSING", prefix="MODELS", level="WARNING")
                if not config_exists:
                    self.log(f"  Missing: config.json", prefix="MODELS")
                if not model_bin_exists:
                    self.log(f"  Missing: model.bin", prefix="MODELS")

        return models_status

    def check_test_audio(self) -> bool:
        """Check if test audio file exists"""
        self.log("Checking test audio...")

        audio_file = self.app_dir / "test_resources" / "test_audio.mp3"

        if audio_file.exists():
            size_mb = audio_file.stat().st_size / (1024 * 1024)
            self.log(f"✓ Test audio found ({size_mb:.2f} MB)", prefix="AUDIO")
            return True
        else:
            self.log(f"✗ Test audio not found", prefix="AUDIO", level="WARNING")
            return False

    def run_transcription_tests(self) -> Dict[str, any]:
        """Run transcription tests"""
        self.log("Running transcription tests...")

        test_script = self.app_dir / "test_transcription.py"
        audio_file = self.app_dir / "test_resources" / "test_audio.mp3"

        if not test_script.exists():
            self.log(f"Test script not found: {test_script}", level="ERROR")
            return {"success": False, "error": "Test script not found"}

        if not audio_file.exists():
            self.log(f"Test audio not found: {audio_file}", level="ERROR")
            return {"success": False, "error": "Test audio not found"}

        try:
            cmd = [
                sys.executable,
                str(test_script),
                "--audio", str(audio_file),
                "--verbose"
            ]

            self.log(f"Executing: {' '.join(cmd[:3])}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )

            # Print full test output
            if result.stdout:
                print("\n--- TEST OUTPUT ---")
                print(result.stdout)
                print("--- END TEST OUTPUT ---\n")

            if result.stderr and "Traceback" in result.stderr:
                print("\n--- TEST ERRORS ---")
                print(result.stderr)
                print("--- END TEST ERRORS ---\n")

            # Try to find and parse results
            # Look for the temp directory results
            import tempfile
            from pathlib import Path
            
            temp_base = Path(tempfile.gettempdir())
            results_files = list(temp_base.glob("*/noscribe_tests/transcription_results.json"))
            
            if results_files:
                latest_results = sorted(results_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
                with open(latest_results, "r") as f:
                    test_results = json.load(f)
                    test_results["success"] = result.returncode == 0
                    return test_results

            return {"success": result.returncode == 0, "error": "Could not parse results"}

        except subprocess.TimeoutExpired:
            self.log("Transcription tests timed out after 10 minutes", level="ERROR")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            self.log(f"Error running tests: {e}", level="ERROR")
            return {"success": False, "error": str(e)}

    def generate_comprehensive_report(self, results: Dict) -> str:
        """Generate a comprehensive test report"""
        report = []

        report.append("=" * 80)
        report.append("NOSCRIBE PLATFORM TEST REPORT")
        report.append("=" * 80)
        report.append("")

        # System Information
        report.append("SYSTEM INFORMATION")
        report.append("-" * 80)
        report.append(f"Platform:         {self.current_platform} {self.current_arch}")
        report.append(f"Python Version:   {self.python_version}")
        report.append(f"Python Executable: {sys.executable}")
        report.append(f"Test Timestamp:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Python Dependencies
        if "dependencies" in results:
            report.append("PYTHON DEPENDENCIES")
            report.append("-" * 80)
            dep_pass = 0
            dep_fail = 0
            for dep, status in results["dependencies"].items():
                icon = "✓" if status else "✗"
                result_str = "INSTALLED" if status else "MISSING"
                report.append(f"{icon} {dep:<40} {result_str}")
                if status:
                    dep_pass += 1
                else:
                    dep_fail += 1
            report.append(f"  Summary: {dep_pass}/{dep_pass + dep_fail} installed")
            report.append("")

        # System Dependencies
        if "system_deps" in results:
            report.append("SYSTEM DEPENDENCIES")
            report.append("-" * 80)
            sys_pass = 0
            sys_fail = 0
            for dep, status in results["system_deps"].items():
                icon = "✓" if status else "✗"
                result_str = "AVAILABLE" if status else "NOT FOUND"
                report.append(f"{icon} {dep:<40} {result_str}")
                if status:
                    sys_pass += 1
                else:
                    sys_fail += 1
            report.append(f"  Summary: {sys_pass}/{sys_pass + sys_fail} available")
            report.append("")

        # Models
        if "models" in results:
            report.append("MODELS")
            report.append("-" * 80)
            model_pass = 0
            model_fail = 0
            for model, status in results["models"].items():
                icon = "✓" if status else "✗"
                result_str = "PRESENT" if status else "MISSING"
                report.append(f"{icon} {model.upper():<40} {result_str}")
                if status:
                    model_pass += 1
                else:
                    model_fail += 1
            report.append(f"  Summary: {model_pass}/{model_pass + model_fail} present")
            report.append("")

        # Test Audio
        if "test_audio" in results:
            report.append("TEST AUDIO")
            report.append("-" * 80)
            icon = "✓" if results["test_audio"] else "✗"
            result_str = "PRESENT" if results["test_audio"] else "MISSING"
            report.append(f"{icon} test_audio.mp3              {result_str}")
            report.append("")

        # Transcription Test Results
        if "transcription" in results:
            transcription_results = results["transcription"]
            report.append("TRANSCRIPTION TEST RESULTS")
            report.append("-" * 80)

            if transcription_results.get("success"):
                report.append("✓ Tests completed successfully")
                report.append("")

                # Model results
                for model_name, model_result in transcription_results.get("models", {}).items():
                    if model_result:
                        report.append(f"{model_name.upper()} Model:")
                        report.append(f"  Status:               ✓ SUCCESS")
                        report.append(f"  Language:             {model_result.get('language', 'N/A')}")
                        report.append(f"  Language Probability: {model_result.get('language_probability', 0):.1%}")
                        report.append(f"  Audio Duration:       {model_result.get('duration', 0):.2f}s")
                        report.append(f"  Model Load Time:      {model_result.get('load_time_seconds', 0):.2f}s")
                        report.append(f"  Transcription Time:   {model_result.get('transcription_time_seconds', 0):.2f}s")
                        report.append(f"  Total Segments:       {model_result.get('segments_count', 0)}")

                        # Show first few segments
                        if model_result.get("segments"):
                            report.append(f"  Sample Transcription:")
                            for i, seg in enumerate(model_result.get("segments", [])[:3]):
                                report.append(f"    [{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}")
                            if len(model_result.get("segments", [])) > 3:
                                report.append(f"    ... and {len(model_result.get('segments', [])) - 3} more segments")
                        report.append("")
                    else:
                        report.append(f"{model_name.upper()} Model:")
                        report.append(f"  Status:               ✗ FAILED")
                        report.append("")
            else:
                report.append("✗ Tests failed")
                error = transcription_results.get("error", "Unknown error")
                report.append(f"  Error: {error}")
                report.append("")

        # Summary and Recommendations
        report.append("=" * 80)
        report.append("SUMMARY & RECOMMENDATIONS")
        report.append("=" * 80)

        all_checks = {
            "Dependencies": results.get("dependencies", {}),
            "System Dependencies": results.get("system_deps", {}),
            "Models": results.get("models", {}),
        }

        total_pass = 0
        total_fail = 0

        for check_name, check_results in all_checks.items():
            passed = sum(1 for v in check_results.values() if v)
            failed = len(check_results) - passed
            total_pass += passed
            total_fail += failed
            report.append(f"{check_name:<30} {passed}/{len(check_results)} passed")

            # Add failed items
            for item, status in check_results.items():
                if not status:
                    report.append(f"  ✗ {item} - MISSING/NOT INSTALLED")

        # Transcription summary
        if results.get("transcription", {}).get("success"):
            total_pass += 2  # Both models
            report.append(f"Transcription Tests         2/2 passed")
        else:
            total_fail += 1
            report.append(f"Transcription Tests         FAILED")
            if results.get("transcription", {}).get("error"):
                report.append(f"  ✗ Error: {results['transcription']['error']}")

        report.append("")
        report.append(f"OVERALL RESULT: {total_pass} passed, {total_fail} failed")

        if total_fail == 0:
            report.append("✓ ALL TESTS PASSED - System is ready for use!")
        else:
            report.append(f"✗ {total_fail} issues need to be resolved")
            report.append("")
            report.append("RECOMMENDATIONS:")
            
            if not all(results.get("dependencies", {}).values()):
                report.append("  1. Install missing Python dependencies:")
                report.append(f"     pip install -r environments/requirements_{self.PLATFORM_NAMES.get(self.current_platform, 'unknown')}.txt")
            
            if not all(results.get("system_deps", {}).values()):
                if self.current_platform == "Darwin":
                    report.append("  2. Install system dependencies (macOS):")
                    report.append("     brew install ffmpeg")
                elif self.current_platform == "Linux":
                    report.append("  2. Install system dependencies (Linux):")
                    report.append("     sudo apt-get install ffmpeg")
                elif self.current_platform == "Windows":
                    report.append("  2. Install system dependencies (Windows):")
                    report.append("     choco install ffmpeg")
            
            if not all(results.get("models", {}).values()):
                report.append("  3. Download and place models in the models/ directory")

        report.append("=" * 80)

        return "\n".join(report)

    def save_report(self, report: str):
        """Save report to file"""
        report_file = self.test_dir / f"test_report_{int(time.time())}.txt"
        with open(report_file, "w") as f:
            f.write(report)
        self.log(f"✓ Report saved to: {report_file}")
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

        # Step 1: Verify dependencies
        self.print_section("1. PYTHON DEPENDENCIES")
        results["dependencies"] = self.verify_dependencies()

        # Step 2: Check system dependencies
        self.print_section("2. SYSTEM DEPENDENCIES")
        results["system_deps"] = self.check_system_dependencies()

        # Step 3: Check models
        self.print_section("3. MODEL VERIFICATION")
        results["models"] = self.check_models()

        # Step 4: Check test audio
        self.print_section("4. TEST AUDIO")
        results["test_audio"] = self.check_test_audio()

        # Step 5: Run transcription tests
        self.print_section("5. TRANSCRIPTION TESTS")
        results["transcription"] = self.run_transcription_tests()

        # Generate and save report
        self.print_section("6. TEST REPORT")
        report = self.generate_comprehensive_report(results)
        print(report)
        report_file = self.save_report(report)

        # Save results as JSON
        results_file = self.test_dir / f"test_results_{int(time.time())}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        self.log(f"✓ Results saved to: {results_file}")

        # Return overall success
        all_deps_ok = all(results.get("dependencies", {}).values())
        all_sysdeps_ok = all(results.get("system_deps", {}).values())
        all_models_ok = all(results.get("models", {}).values())
        transcription_ok = results.get("transcription", {}).get("success", False)
        test_audio_ok = results.get("test_audio", False)

        overall_success = all_deps_ok and all_sysdeps_ok and all_models_ok and test_audio_ok and transcription_ok

        return overall_success


def main():
    """Main entry point"""
    runner = SimplePlatformTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
