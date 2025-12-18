#!/usr/bin/env python3
"""
PowerApps Solution Exporter

A CLI tool to download and export unmanaged PowerApps solutions from 
Dynamics 365 / Power Platform using the PowerApps CLI (pac).
"""

import subprocess
import sys
import os
import threading
import time
import itertools
from datetime import datetime
from pathlib import Path


class Spinner:
    """Animated spinner to show activity during long-running operations."""
    
    def __init__(self, message: str = "Processing"):
        self.message = message
        self.spinning = False
        self.spinner_thread = None
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.start_time = None
    
    def _spin(self):
        """Internal method that runs the spinner animation."""
        frame_cycle = itertools.cycle(self.frames)
        while self.spinning:
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            frame = next(frame_cycle)
            sys.stdout.write(f"\r{frame} {self.message}... [{time_str}]  ")
            sys.stdout.flush()
            time.sleep(0.1)
    
    def start(self):
        """Start the spinner animation."""
        self.spinning = True
        self.start_time = time.time()
        self.spinner_thread = threading.Thread(target=self._spin)
        self.spinner_thread.start()
    
    def stop(self, success: bool = True):
        """Stop the spinner and show final status."""
        self.spinning = False
        if self.spinner_thread:
            self.spinner_thread.join()
        
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        
        # Clear the line and show final status
        sys.stdout.write("\r" + " " * 60 + "\r")
        if success:
            print(f"✅ {self.message} completed in {time_str}")
        else:
            print(f"❌ {self.message} failed after {time_str}")


def run_pac_command(args: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a pac CLI command and return the result."""
    cmd = ["pac"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False
        )
        return result
    except FileNotFoundError:
        print("\n❌ Error: PowerApps CLI (pac) is not installed or not in PATH.")
        print("\nInstall it using one of these methods:")
        print("  • .NET:      dotnet tool install --global Microsoft.PowerApps.CLI.Tool")
        print("  • Windows:   Download from https://aka.ms/PowerAppsCLI")
        print("  • macOS:     brew install microsoft/mssql-release/powerapps-cli")
        print("\nAfter installation, restart your terminal and try again.")
        sys.exit(1)


def check_pac_installed() -> bool:
    """Check if the pac CLI is installed and accessible."""
    print("🔍 Checking for PowerApps CLI (pac)...")
    result = run_pac_command(["help"])
    
    # pac help returns info even on "error" - check for version string in output
    output = result.stdout + result.stderr if result.stderr else result.stdout
    if "Microsoft PowerPlatform CLI" in output or "Version:" in output:
        # Extract version from output
        for line in output.split('\n'):
            if "Version:" in line:
                version = line.strip()
                print(f"✅ Found pac CLI: {version}")
                return True
        print("✅ Found pac CLI")
        return True
    else:
        print("❌ pac CLI check failed.")
        return False


def get_auth_profiles() -> list[dict]:
    """Get list of existing authentication profiles."""
    result = run_pac_command(["auth", "list"])
    
    profiles = []
    if result.returncode == 0 and result.stdout:
        lines = result.stdout.strip().split('\n')
        # Parse the output - looking for profile entries
        for line in lines:
            if "Active" in line or "http" in line.lower():
                profiles.append({"raw": line})
    
    return profiles


def ensure_authenticated() -> bool:
    """Check if authenticated, prompt to authenticate if not."""
    print("\n🔐 Checking authentication status...")
    
    result = run_pac_command(["auth", "list"])
    
    # Check if we have any active profiles
    has_active = False
    if result.returncode == 0 and result.stdout:
        output = result.stdout.lower()
        # Look for indicators of active authentication
        if "active" in output or ("http" in output and "universal" not in output.lower()):
            # Filter out header lines
            lines = result.stdout.strip().split('\n')
            for line in lines:
                # Skip header/separator lines
                if '---' in line or 'Index' in line or not line.strip():
                    continue
                if 'http' in line.lower() and 'crm' in line.lower():
                    has_active = True
                    break
    
    if has_active:
        print("✅ Found existing authentication profile.")
        print("\n📋 Current profiles:")
        print(result.stdout)
        
        use_existing = input("\nUse existing profile? (Y/n): ").strip().lower()
        if use_existing in ['', 'y', 'yes']:
            return True
    
    # Need to create new auth
    print("\n📝 No active profile found or creating new one...")
    print("This will open a browser window for you to sign in.\n")
    
    env_url = input("Enter your environment URL (e.g., https://yourorg.crm.dynamics.com): ").strip()
    
    if not env_url:
        print("❌ Environment URL is required.")
        return False
    
    # Ensure URL has https://
    if not env_url.startswith("http"):
        env_url = f"https://{env_url}"
    
    print(f"\n🌐 Opening browser for authentication to: {env_url}")
    print("Please complete the sign-in process in your browser...\n")
    
    # Run auth create - this will open browser
    auth_result = run_pac_command(["auth", "create", "--url", env_url], capture_output=False)
    
    if auth_result.returncode == 0:
        print("\n✅ Authentication successful!")
        return True
    else:
        print("\n❌ Authentication failed. Please try again.")
        return False


def list_solutions() -> list[dict]:
    """List all available solutions in the environment and return them with indices."""
    print("\n📦 Fetching available solutions...")
    
    result = run_pac_command(["solution", "list"])
    
    if result.returncode != 0:
        print("❌ Failed to fetch solutions. Make sure you're authenticated.")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return []
    
    # Parse solution details from output
    solutions = []
    if result.stdout:
        lines = result.stdout.strip().split('\n')
        for line in lines:
            # Skip header and separator lines
            if '---' in line or 'Unique Name' in line or not line.strip():
                continue
            # Try to extract solution details
            parts = line.split()
            if parts and not parts[0].startswith('-'):
                # Extract unique name (first column)
                unique_name = parts[0]
                # Try to get the rest of the info
                solutions.append({
                    'unique_name': unique_name,
                    'raw_line': line
                })
    
    if not solutions:
        print("No solutions found or unable to parse output.")
        return []
    
    # Display solutions with numbered index
    print("\n" + "=" * 70)
    print("AVAILABLE SOLUTIONS")
    print("=" * 70)
    print(f"{'#':<4} {'Unique Name':<30} {'Friendly Name':<25} {'Version'}")
    print("-" * 70)
    
    for idx, sol in enumerate(solutions, 1):
        # Parse the raw line to extract columns
        parts = sol['raw_line'].split()
        unique_name = parts[0] if len(parts) > 0 else ""
        
        # The friendly name might have spaces and be in the middle
        # Version is typically at the end, and Managed (True/False) is last
        # Format: UniqueName FriendlyName... Version Managed
        if len(parts) >= 3:
            version = parts[-2] if parts[-1] in ['True', 'False'] else parts[-1]
            managed = parts[-1] if parts[-1] in ['True', 'False'] else ""
            # Everything between unique_name and version is the friendly name
            friendly_parts = parts[1:-2] if managed else parts[1:-1]
            friendly_name = " ".join(friendly_parts)
        else:
            friendly_name = ""
            version = ""
        
        # Truncate friendly name if too long
        if len(friendly_name) > 24:
            friendly_name = friendly_name[:21] + "..."
        
        print(f"{idx:<4} {unique_name:<30} {friendly_name:<25} {version}")
    
    print("-" * 70)
    print(f"Total: {len(solutions)} solutions")
    
    return solutions


def export_solution(solution_name: str, output_dir: str = "./exports") -> bool:
    """Export a solution by name to the specified directory."""
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{solution_name}_{timestamp}.zip"
    full_path = output_path / filename
    
    print(f"\n📥 Exporting solution: {solution_name}")
    print(f"   Output: {full_path}")
    print("   Type: Unmanaged")
    print()
    
    # Start spinner for visual feedback
    spinner = Spinner(f"Exporting {solution_name}")
    spinner.start()
    
    # Run the export command (capture output so it doesn't interfere with spinner)
    result = None
    try:
        result = run_pac_command([
            "solution", "export",
            "--name", solution_name,
            "--path", str(full_path),
            "--managed", "false",
            "--overwrite"
        ], capture_output=True)
    finally:
        # Always stop spinner
        success = result is not None and result.returncode == 0 and full_path.exists()
        spinner.stop(success=success)
    
    if result is None:
        print(f"\n❌ Failed to run export command")
        return False
    
    if result.returncode == 0:
        # Verify file was created
        if full_path.exists():
            file_size = full_path.stat().st_size / (1024 * 1024)  # Convert to MB
            print(f"   📁 File: {full_path}")
            print(f"   📊 Size: {file_size:.2f} MB")
            return True
        else:
            print("\n⚠️  Export command completed but file was not found.")
            print(f"   Expected location: {full_path}")
            # Show any output that might help debug
            if result.stdout:
                print(f"   Output: {result.stdout}")
            return False
    else:
        print(f"\n❌ Failed to export solution: {solution_name}")
        print("   Please verify the solution name is correct.")
        if result.stderr:
            print(f"   Error: {result.stderr}")
        return False


def main():
    """Main entry point for the solution exporter."""
    print("=" * 60)
    print("  PowerApps Solution Exporter")
    print("  Export unmanaged solutions from Dynamics 365 / Power Platform")
    print("=" * 60)
    
    # Step 1: Check pac CLI is installed
    if not check_pac_installed():
        sys.exit(1)
    
    # Step 2: Ensure we're authenticated
    if not ensure_authenticated():
        print("\n❌ Authentication required to continue.")
        sys.exit(1)
    
    # Step 3: List available solutions
    solutions = list_solutions()
    
    if not solutions:
        print("❌ No solutions available to export.")
        sys.exit(1)
    
    # Step 4: Get solution selection from user
    print("\n" + "-" * 70)
    selection = input("Enter the number of the solution to export (or 'q' to quit): ").strip()
    
    if selection.lower() == 'q':
        print("👋 Goodbye!")
        sys.exit(0)
    
    # Validate selection
    try:
        idx = int(selection)
        if idx < 1 or idx > len(solutions):
            print(f"❌ Invalid selection. Please enter a number between 1 and {len(solutions)}.")
            sys.exit(1)
        solution_name = solutions[idx - 1]['unique_name']
    except ValueError:
        # Allow direct name input as fallback
        solution_name = selection
        if not solution_name:
            print("❌ Solution name is required.")
            sys.exit(1)
        print(f"ℹ️  Using direct name input: {solution_name}")
    
    # Step 5: Export the solution
    success = export_solution(solution_name)
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 Export complete!")
        print("=" * 60)
        
        # Offer to export another
        another = input("\nExport another solution? (y/N): ").strip().lower()
        if another in ['y', 'yes']:
            export_another_solution()
    else:
        sys.exit(1)


def export_another_solution():
    """Allow user to export another solution without re-authenticating."""
    # List solutions again
    solutions = list_solutions()
    
    if not solutions:
        print("❌ No solutions available to export.")
        return
    
    print("\n" + "-" * 70)
    selection = input("Enter the number of the solution to export (or 'q' to quit): ").strip()
    
    if selection.lower() == 'q':
        print("👋 Goodbye!")
        return
    
    # Validate selection
    try:
        idx = int(selection)
        if idx < 1 or idx > len(solutions):
            print(f"❌ Invalid selection. Please enter a number between 1 and {len(solutions)}.")
            return
        solution_name = solutions[idx - 1]['unique_name']
    except ValueError:
        solution_name = selection
        if not solution_name:
            print("❌ Solution name is required.")
            return
        print(f"ℹ️  Using direct name input: {solution_name}")
    
    # Export the solution
    success = export_solution(solution_name)
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 Export complete!")
        print("=" * 60)
        
        another = input("\nExport another solution? (y/N): ").strip().lower()
        if another in ['y', 'yes']:
            export_another_solution()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Export cancelled by user.")
        sys.exit(0)

