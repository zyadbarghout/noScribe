#!/usr/bin/env python3
"""
CI Environment Validation Script
Validates that the GitHub Actions environment is properly configured before running tests
"""

import os
import sys
import platform
import subprocess
import json
from pathlib import Path

class CIValidator:
    def __init__(self):
        self.system = platform.system()
        self.machine = platform.machine()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.issues = []
        self.warnings = []
        self.successes = []
    
    def log(self, message, level="INFO"):
        """Print formatted log message"""
        levels = {
            "INFO": "ℹ️",
            "SUCCESS": "✓",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }
        icon = levels.get(level, "ℹ️")
        print(f"{icon} [{level}] {message}")
    
    def check_environment(self):
        """Run all validation checks"""
        print("=" * 80)
        print("CI ENVIRONMENT VALIDATION")
        print("=" * 80)
        print()
        
        self.log(f"System: {self.system} ({self.machine})")
        self.log(f"Python: {self.python_version}")
        self.log(f"Python executable: {sys.executable}")
        print()
        
        # Run checks
        self.check_python_version()
        self.check_pip()
        self.check_ffmpeg()
        self.check_audio_file()
        self.check_models()
        self.check_required_packages()
        self.check_disk_space()
        
        # Print summary
        print()
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"✓ Passed: {len(self.successes)}")
        print(f"⚠️ Warnings: {len(self.warnings)}")
        print(f"❌ Failed: {len(self.issues)}")
        print()
        
        if self.warnings:
            print("Warnings:")
            for warning in self.warnings:
                self.log(warning, "WARNING")
            print()
        
        if self.issues:
            print("Issues:")
            for issue in self.issues:
                self.log(issue, "ERROR")
            print()
            return False
        
        return True
    
    def check_python_version(self):
        """Verify Python version is supported"""
        version_tuple = (sys.version_info.major, sys.version_info.minor)
        if version_tuple >= (3, 9) and version_tuple <= (3, 11):
            self.successes.append(f"Python version {self.python_version} is supported")
        else:
            self.issues.append(f"Python version {self.python_version} is not supported (require 3.9-3.11)")
    
    def check_pip(self):
        """Check pip is working"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                pip_version = result.stdout.strip().split()[-2]
                self.successes.append(f"pip is working (version {pip_version})")
            else:
                self.issues.append(f"pip check failed: {result.stderr}")
        except Exception as e:
            self.issues.append(f"Failed to check pip: {e}")
    
    def check_ffmpeg(self):
        """Check ffmpeg is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                self.successes.append(f"ffmpeg is available: {version_line}")
            else:
                self.issues.append("ffmpeg not working properly")
        except FileNotFoundError:
            self.issues.append("ffmpeg not found in PATH")
        except Exception as e:
            self.issues.append(f"Failed to check ffmpeg: {e}")
    
    def check_audio_file(self):
        """Check test audio file exists"""
        audio_file = Path("test_resources/test_audio.mp3")
        if audio_file.exists():
            size_mb = audio_file.stat().st_size / (1024 * 1024)
            self.successes.append(f"Test audio file found: {audio_file} ({size_mb:.2f} MB)")
        else:
            self.warnings.append(f"Test audio file not found at {audio_file} - will generate synthetic audio")
    
    def check_models(self):
        """Check Whisper models are available"""
        models_dir = Path("models")
        if not models_dir.exists():
            self.issues.append(f"Models directory not found: {models_dir}")
            return
        
        models = ["fast", "precise"]
        for model in models:
            model_path = models_dir / model / "model.bin"
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                self.successes.append(f"Model '{model}' found: {size_mb:.1f} MB")
            else:
                self.warnings.append(f"Model '{model}' not found at {model_path}")
    
    def check_required_packages(self):
        """Check required Python packages are installed"""
        required = {
            "faster_whisper": "faster-whisper",
            "torch": "torch",
            "torchaudio": "torchaudio",
            "customtkinter": "customtkinter",
            "PIL": "Pillow",
            "yaml": "PyYAML",
        }
        
        print()
        print("Checking Python packages...")
        missing = []
        
        for import_name, package_name in required.items():
            try:
                __import__(import_name)
                self.successes.append(f"Package '{package_name}' is installed")
            except ImportError:
                self.issues.append(f"Package '{package_name}' is NOT installed")
                missing.append(package_name)
        
        if missing:
            print()
            self.log(f"Missing packages: {', '.join(missing)}", "ERROR")
    
    def check_disk_space(self):
        """Check available disk space"""
        try:
            if self.system != "Windows":
                result = subprocess.run(
                    ["df", "-h", "."],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[-1].split()
                    if len(parts) >= 4:
                        available = parts[3]
                        self.successes.append(f"Available disk space: {available}")
        except Exception as e:
            self.warnings.append(f"Could not check disk space: {e}")
    
    def generate_report(self, filename="ci_validation_report.json"):
        """Generate a JSON report of the validation"""
        report = {
            "system": self.system,
            "machine": self.machine,
            "python_version": self.python_version,
            "successes": self.successes,
            "warnings": self.warnings,
            "issues": self.issues,
            "passed": len(self.issues) == 0
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report


def main():
    validator = CIValidator()
    passed = validator.check_environment()
    
    # Generate report
    report = validator.generate_report()
    
    if not passed:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
