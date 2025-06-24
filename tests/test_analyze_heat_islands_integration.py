#!/usr/bin/env python3
"""
Integration tests for the analyze_heat_islands.py script.

This test suite verifies the complete functionality of the urban heat island analysis script,
including parameter handling, file validation, error handling, and output generation.
"""

import pytest
import subprocess
import sys
from pathlib import Path
from datetime import date
import tempfile
import shutil


class TestAnalyzeHeatIslandsIntegration:
    """Integration tests for the analyze_heat_islands.py script."""
    
    @pytest.fixture
    def script_path(self):
        """Get the path to the analyze_heat_islands.py script."""
        return Path(__file__).parent.parent / "scripts" / "data_processing" / "analyze_heat_islands.py"
    
    @pytest.fixture
    def test_data_paths(self):
        """Get paths to test data files."""
        project_root = Path(__file__).parent.parent
        return {
            "city_boundary": project_root / "data" / "raw" / "boundaries" / "berlin_admin_boundaries.geojson",
            "landuse_data": project_root / "data" / "raw" / "landcover" / "berlin_corine_landcover.geojson",
            "weather_data": project_root / "data" / "processed" / "weather" / "berlin_temperature_20220101_to_20221231_interpolated.geojson"
        }
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for tests."""
        temp_dir = tempfile.mkdtemp(prefix="uhi_test_")
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_script_exists(self, script_path):
        """Test that the script file exists."""
        assert script_path.exists(), f"Script not found at {script_path}"
        assert script_path.is_file(), f"Script path is not a file: {script_path}"
    
    def test_data_files_exist(self, test_data_paths):
        """Test that all required data files exist."""
        for name, path in test_data_paths.items():
            assert path.exists(), f"Required data file not found: {name} at {path}"
            assert path.is_file(), f"Data path is not a file: {name} at {path}"
    
    def test_help_output(self, script_path):
        """Test that the script provides help information."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Help command failed: {result.stderr}"
        assert "usage:" in result.stdout, "Help output missing usage information"
        assert "--city-boundary" in result.stdout, "Help output missing city-boundary option"
        assert "--landuse-data" in result.stdout, "Help output missing landuse-data option"
        assert "--weather-data" in result.stdout, "Help output missing weather-data option"
        assert "--start-date" in result.stdout, "Help output missing start-date option"
        assert "--end-date" in result.stdout, "Help output missing end-date option"
        assert "--output-dir" in result.stdout, "Help output missing output-dir option"
        assert "--cloud-threshold" in result.stdout, "Help output missing cloud-threshold option"
    
    def test_default_parameters(self, script_path, temp_output_dir):
        """Test script execution with default parameters."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--output-dir", str(temp_output_dir)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Default parameters test failed: {result.stderr}"
        assert "✅ Analysis completed successfully!" in result.stdout, "Success message not found"
        
        # Check that output files were created
        analysis_summary = temp_output_dir / "analysis_summary.txt"
        assert analysis_summary.exists(), "Analysis summary file not created"
        
        # Check summary content
        with open(analysis_summary, 'r') as f:
            content = f.read()
            assert "Urban Heat Island Analysis Summary" in content
            assert "Date range: 2022-01-01 to 2022-12-31" in content
            assert "Cloud threshold: 20%" in content
            assert "Grid cell size: 100m" in content
            assert "Hotspot threshold: 0.9" in content
    
    def test_custom_parameters(self, script_path, temp_output_dir):
        """Test script execution with custom parameters."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--start-date", "2022-06-01",
                "--end-date", "2022-08-31",
                "--output-dir", str(temp_output_dir),
                "--cloud-threshold", "15"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Custom parameters test failed: {result.stderr}"
        assert "✅ Analysis completed successfully!" in result.stdout, "Success message not found"
        
        # Check that output files were created
        analysis_summary = temp_output_dir / "analysis_summary.txt"
        assert analysis_summary.exists(), "Analysis summary file not created"
        
        # Check summary content with custom parameters
        with open(analysis_summary, 'r') as f:
            content = f.read()
            assert "Date range: 2022-06-01 to 2022-08-31" in content
            assert "Cloud threshold: 15.0%" in content
    
    def test_custom_data_paths(self, script_path, temp_output_dir, test_data_paths):
        """Test script execution with custom data paths."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--city-boundary", str(test_data_paths["city_boundary"]),
                "--landuse-data", str(test_data_paths["landuse_data"]),
                "--weather-data", str(test_data_paths["weather_data"]),
                "--output-dir", str(temp_output_dir)
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Custom data paths test failed: {result.stderr}"
        assert "✅ Analysis completed successfully!" in result.stdout, "Success message not found"
    
    def test_invalid_date_format(self, script_path):
        """Test error handling for invalid date format."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--start-date", "2022-13-01"  # Invalid month
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 1, "Script should exit with error code 1 for invalid date"
        assert "Error parsing dates:" in result.stdout, "Date parsing error message not found"
        assert "month must be in 1..12" in result.stdout, "Specific date error not found"
    
    def test_invalid_end_date(self, script_path):
        """Test error handling for invalid end date."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--end-date", "2022-02-30"  # Invalid day for February
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 1, "Script should exit with error code 1 for invalid end date"
        assert "Error parsing dates:" in result.stdout, "Date parsing error message not found"
    
    def test_missing_city_boundary_file(self, script_path):
        """Test error handling for missing city boundary file."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--city-boundary", "nonexistent_boundary.geojson"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 1, "Script should exit with error code 1 for missing city boundary"
        assert "City boundary file not found:" in result.stdout, "Missing file error message not found"
    
    def test_missing_landuse_data_file(self, script_path):
        """Test error handling for missing land use data file."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--landuse-data", "nonexistent_landuse.geojson"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 1, "Script should exit with error code 1 for missing land use data"
        assert "Land use data file not found:" in result.stdout, "Missing file error message not found"
    
    def test_missing_weather_data_file(self, script_path):
        """Test error handling for missing weather data file."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--weather-data", "nonexistent_weather.geojson"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 1, "Script should exit with error code 1 for missing weather data"
        assert "Weather data file not found:" in result.stdout, "Missing file error message not found"
    
    def test_logging_output(self, script_path, temp_output_dir):
        """Test that logging output is generated correctly."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--output-dir", str(temp_output_dir)
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Logging test failed: {result.stderr}"
        
        # Check that log messages are present in stderr (Python logging outputs to stderr)
        log_messages = [
            "=== Urban Heat Island Analysis for Berlin ===",
            "City boundary:",
            "Land use data:",
            "Weather data:",
            "Date range: 2022-01-01 to 2022-12-31",
            "Cloud threshold: 20%",
            "UrbanHeatIslandAnalyzer initialized successfully",
            "Starting heat island analysis using existing weather data",
            "Note: Using existing weather data instead of satellite data",
            "Analysis completed successfully!",
            "Temperature analysis: Weather data processed",
            "Hotspot analysis: Analysis completed",
            "Land use correlations: Analysis completed",
            "Creating visualization...",
            "Results saved to:",
            "Summary saved to:"
        ]
        
        for message in log_messages:
            assert message in result.stderr, f"Log message not found: {message}"
    
    def test_output_directory_creation(self, script_path, temp_output_dir):
        """Test that output directory is created if it doesn't exist."""
        # Remove the temp directory to test creation
        if temp_output_dir.exists():
            shutil.rmtree(temp_output_dir)
        
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--output-dir", str(temp_output_dir)
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Output directory creation test failed: {result.stderr}"
        assert temp_output_dir.exists(), "Output directory was not created"
        assert temp_output_dir.is_dir(), "Output path is not a directory"
    
    def test_cloud_threshold_parameter(self, script_path, temp_output_dir):
        """Test that cloud threshold parameter is handled correctly."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--output-dir", str(temp_output_dir),
                "--cloud-threshold", "25.5"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Cloud threshold test failed: {result.stderr}"
        
        # Check that the cloud threshold is logged correctly (in stderr)
        assert "Cloud threshold: 25.5%" in result.stderr, "Cloud threshold not logged correctly"
        
        # Check that it appears in the summary
        analysis_summary = temp_output_dir / "analysis_summary.txt"
        with open(analysis_summary, 'r') as f:
            content = f.read()
            assert "Cloud threshold: 25.5%" in content, "Cloud threshold not in summary"
    
    def test_all_parameters_combined(self, script_path, temp_output_dir, test_data_paths):
        """Test script with all parameters specified."""
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                "--city-boundary", str(test_data_paths["city_boundary"]),
                "--landuse-data", str(test_data_paths["landuse_data"]),
                "--weather-data", str(test_data_paths["weather_data"]),
                "--start-date", "2022-07-01",
                "--end-date", "2022-07-31",
                "--output-dir", str(temp_output_dir),
                "--cloud-threshold", "10"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"All parameters test failed: {result.stderr}"
        assert "✅ Analysis completed successfully!" in result.stdout, "Success message not found"
        
        # Check summary content
        analysis_summary = temp_output_dir / "analysis_summary.txt"
        with open(analysis_summary, 'r') as f:
            content = f.read()
            assert "Date range: 2022-07-01 to 2022-07-31" in content
            assert "Cloud threshold: 10.0%" in content


if __name__ == "__main__":
    # Run tests directly if script is executed
    pytest.main([__file__, "-v"]) 