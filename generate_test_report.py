#!/usr/bin/env python3
"""
Comprehensive Platform Test Report Generator
Shows detailed results from test execution across platforms
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class TestReportGenerator:
    """Generate comprehensive test reports"""

    def __init__(self):
        self.app_dir = Path(__file__).parent.absolute()
        self.test_dir = self.app_dir / "platform_test_results"

    def find_latest_results(self) -> Optional[Path]:
        """Find the latest test results JSON file"""
        if not self.test_dir.exists():
            return None

        json_files = list(self.test_dir.glob("test_results_*.json"))
        if not json_files:
            return None

        return sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]

    def load_results(self, file_path: Path) -> Dict:
        """Load test results from JSON file"""
        with open(file_path, 'r') as f:
            return json.load(f)

    def format_section(self, title: str) -> str:
        """Format a section header"""
        return f"\n{'=' * 100}\n{title:^100}\n{'=' * 100}\n"

    def format_subsection(self, title: str) -> str:
        """Format a subsection header"""
        return f"\n{'-' * 100}\n{title}\n{'-' * 100}\n"

    def generate_environment_report(self, results: Dict) -> str:
        """Generate environment information section"""
        report = self.format_section("ENVIRONMENT INFORMATION")

        report += f"Platform:              {results.get('platform')} {results.get('architecture')}\n"
        report += f"Python Version:        {results.get('python_version')}\n"
        report += f"Test Timestamp:        {results.get('timestamp')}\n"

        return report

    def generate_dependencies_report(self, results: Dict) -> str:
        """Generate dependencies report"""
        report = self.format_section("PYTHON DEPENDENCIES")

        deps = results.get("dependencies", {})
        if not deps:
            return report + "No dependency information available\n"

        passed = sum(1 for v in deps.values() if v)
        total = len(deps)

        report += f"Summary: {passed}/{total} dependencies installed\n"
        report += self.format_subsection("Dependency Status")

        for dep, status in sorted(deps.items()):
            icon = "✓" if status else "✗"
            status_text = "INSTALLED" if status else "MISSING"
            report += f"{icon} {dep:<50} {status_text}\n"

        if passed < total:
            report += "\n⚠ Missing dependencies:\n"
            for dep, status in sorted(deps.items()):
                if not status:
                    report += f"  - {dep}\n"

        return report

    def generate_system_report(self, results: Dict) -> str:
        """Generate system dependencies report"""
        report = self.format_section("SYSTEM DEPENDENCIES")

        sys_deps = results.get("system_deps", {})
        if not sys_deps:
            return report + "No system dependency information available\n"

        passed = sum(1 for v in sys_deps.values() if v)
        total = len(sys_deps)

        report += f"Summary: {passed}/{total} system dependencies available\n"
        report += self.format_subsection("System Dependency Status")

        for dep, status in sorted(sys_deps.items()):
            icon = "✓" if status else "✗"
            status_text = "AVAILABLE" if status else "NOT FOUND"
            report += f"{icon} {dep:<50} {status_text}\n"

        if passed < total:
            report += "\n⚠ Missing system dependencies:\n"
            for dep, status in sorted(sys_deps.items()):
                if not status:
                    report += f"  - {dep}\n"

        return report

    def generate_models_report(self, results: Dict) -> str:
        """Generate models report"""
        report = self.format_section("MODELS")

        models = results.get("models", {})
        if not models:
            return report + "No model information available\n"

        passed = sum(1 for v in models.values() if v)
        total = len(models)

        report += f"Summary: {passed}/{total} models present\n"
        report += self.format_subsection("Model Status")

        for model, status in sorted(models.items()):
            icon = "✓" if status else "✗"
            status_text = "PRESENT" if status else "MISSING"
            report += f"{icon} {model.upper():<50} {status_text}\n"

        if passed < total:
            report += "\n⚠ Missing models:\n"
            for model, status in sorted(models.items()):
                if not status:
                    report += f"  - {model}\n"

        return report

    def generate_transcription_report(self, results: Dict) -> str:
        """Generate transcription test report"""
        report = self.format_section("TRANSCRIPTION TEST RESULTS")

        trans = results.get("transcription", {})
        if not trans:
            return report + "No transcription results available\n"

        if not trans.get("success"):
            error = trans.get("error", "Unknown error")
            report += f"✗ FAILED - {error}\n"
            return report

        report += "✓ Tests completed successfully\n"
        report += self.format_subsection("Model Results")

        for model_name, model_result in trans.get("models", {}).items():
            if model_result:
                report += f"\n{model_name.upper()} Model: ✓ SUCCESS\n"
                report += f"  Language:               {model_result.get('language', 'N/A')}\n"
                report += f"  Language Probability:  {model_result.get('language_probability', 0):.1%}\n"
                report += f"  Audio Duration:        {model_result.get('duration', 0):.2f} seconds\n"
                report += f"  Model Load Time:       {model_result.get('load_time_seconds', 0):.2f} seconds\n"
                report += f"  Transcription Time:    {model_result.get('transcription_time_seconds', 0):.2f} seconds\n"
                report += f"  Segments Generated:    {model_result.get('segments_count', 0)}\n"

                # Show sample segments
                segments = model_result.get("segments", [])
                if segments:
                    report += f"\n  Sample Transcription (first 3 segments):\n"
                    for i, seg in enumerate(segments[:3], 1):
                        start = seg.get('start', 0)
                        end = seg.get('end', 0)
                        text = seg.get('text', '')
                        report += f"    [{start:6.2f}s - {end:6.2f}s] {text}\n"

                    if len(segments) > 3:
                        report += f"\n  ... and {len(segments) - 3} more segments\n"
            else:
                report += f"\n{model_name.upper()} Model: ✗ FAILED\n"

        return report

    def generate_summary_report(self, results: Dict) -> str:
        """Generate summary and recommendations"""
        report = self.format_section("TEST SUMMARY & RECOMMENDATIONS")

        # Count results
        deps_pass = sum(1 for v in results.get("dependencies", {}).values() if v)
        deps_total = len(results.get("dependencies", {}))

        sys_pass = sum(1 for v in results.get("system_deps", {}).values() if v)
        sys_total = len(results.get("system_deps", {}))

        models_pass = sum(1 for v in results.get("models", {}).values() if v)
        models_total = len(results.get("models", {}))

        trans_pass = 2 if results.get("transcription", {}).get("success") else 0

        total_pass = deps_pass + sys_pass + models_pass + trans_pass
        total_fail = (deps_total - deps_pass) + (sys_total - sys_pass) + (models_total - models_pass) + (2 - trans_pass)

        report += f"Python Dependencies:   {deps_pass}/{deps_total} passed\n"
        report += f"System Dependencies:   {sys_pass}/{sys_total} passed\n"
        report += f"Models:                {models_pass}/{models_total} passed\n"
        report += f"Transcription Tests:   {trans_pass}/2 passed\n"
        report += f"\nOVERALL:               {total_pass} passed, {total_fail} failed\n"

        if total_fail == 0:
            report += "\n✓✓✓ ALL TESTS PASSED ✓✓✓\n"
            report += "Your environment is ready for noScribe transcription testing!\n"
        else:
            report += f"\n✗ {total_fail} issues need to be resolved\n"
            report += self.format_subsection("Recommendations")

            # Missing dependencies
            missing_deps = [d for d, v in results.get("dependencies", {}).items() if not v]
            if missing_deps:
                report += "\n1. Install missing Python dependencies:\n"
                platform_name = results.get("platform", "unknown")
                if platform_name == "Darwin":
                    arch = results.get("architecture", "")
                    if arch == "arm64":
                        req_file = "environments/requirements_macOS_arm64.txt"
                    else:
                        req_file = "environments/requirements_macOS_x86_64.txt"
                elif platform_name == "Linux":
                    req_file = "environments/requirements_linux.txt"
                elif platform_name == "Windows":
                    req_file = "environments/requirements_win_cpu.txt"
                else:
                    req_file = "requirements.txt"

                report += f"\n   pip install -r {req_file}\n"

            # Missing system dependencies
            missing_sys = [d for d, v in results.get("system_deps", {}).items() if not v]
            if missing_sys:
                report += "\n2. Install missing system dependencies:\n"
                platform_name = results.get("platform", "unknown")

                if platform_name == "Darwin":
                    report += "\n   # macOS (using Homebrew)\n"
                    report += "   brew install " + " ".join(missing_sys) + "\n"
                elif platform_name == "Linux":
                    report += "\n   # Linux (using apt)\n"
                    report += "   sudo apt-get update\n"
                    report += "   sudo apt-get install -y " + " ".join(missing_sys) + "\n"
                elif platform_name == "Windows":
                    report += "\n   # Windows (using Chocolatey)\n"
                    report += "   choco install " + " ".join(missing_sys) + "\n"

            # Missing models
            missing_models = [m for m, v in results.get("models", {}).items() if not v]
            if missing_models:
                report += "\n3. Download and place missing models:\n"
                for model in missing_models:
                    report += f"\n   - Place {model} model in: models/{model}/\n"
                    report += f"     (Should contain: config.json, model.bin, tokenizer.json, vocabulary.json)\n"

        return report

    def generate_full_report(self, results: Dict) -> str:
        """Generate complete test report"""
        report = ""
        report += "\n"
        report += "╔" + "=" * 98 + "╗\n"
        report += "║" + " " * 98 + "║\n"
        report += "║" + "NOSCRIBE PLATFORM TEST REPORT".center(98) + "║\n"
        report += "║" + f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(98) + "║\n"
        report += "║" + " " * 98 + "║\n"
        report += "╚" + "=" * 98 + "╝\n"

        report += self.generate_environment_report(results)
        report += self.generate_dependencies_report(results)
        report += self.generate_system_report(results)
        report += self.generate_models_report(results)
        report += self.generate_transcription_report(results)
        report += self.generate_summary_report(results)

        report += "\n" + "=" * 100 + "\n"
        report += "END OF REPORT\n"
        report += "=" * 100 + "\n"

        return report

    def run(self):
        """Run the report generator"""
        results_file = self.find_latest_results()

        if not results_file:
            print("❌ No test results found!")
            print(f"Expected results in: {self.test_dir}")
            sys.exit(1)

        print(f"📋 Loading results from: {results_file}")

        results = self.load_results(results_file)
        report = self.generate_full_report(results)

        print(report)

        # Save report to file
        report_file = self.test_dir / f"comprehensive_report_{int(datetime.now().timestamp())}.txt"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\n✓ Report saved to: {report_file}")


def main():
    """Main entry point"""
    generator = TestReportGenerator()
    generator.run()


if __name__ == "__main__":
    main()
