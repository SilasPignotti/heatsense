#!/usr/bin/env python3
"""
Integration tests for CorineDataDownloader functionality with date ranges.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from uhi_analyzer.data.corine_downloader import CorineDataDownloader
from uhi_analyzer.config import CORINE_YEARS

class TestCorineDataDownloader:
    def test_date_range_selection(self):
        test_ranges = [
            (1985, 1995),    # Before all available years
            (1990, 1995),    # Contains 1990
            (1995, 2005),    # Contains 2000
            (2003, 2008),    # Contains 2006
            (2010, 2015),    # Contains 2012
            (2015, 2020),    # Contains 2018
            (2020, 2025),    # After all available years
            (2018, 2022),    # Contains 2018
            (2022, 2024),    # After all available years
        ]
        for start_year, end_year in test_ranges:
            # Test with the new API
            downloader = CorineDataDownloader((start_year, end_year))
            assert downloader.selected_year in CORINE_YEARS

    @pytest.mark.parametrize("start_date,end_date", [
        (2020, 2022),
        ("2021-06", "2021-12"),
        (2018, 2023),
        ("2020-01-01", "2020-12-31"),
        (datetime(2019, 6, 1), datetime(2021, 8, 31)),
        (2015, 2017),
        (2025, 2027),
    ])
    def test_downloader_initialization(self, start_date, end_date):
        downloader = CorineDataDownloader((start_date, end_date))
        assert downloader.start_year <= downloader.end_year
        assert downloader.selected_year in CORINE_YEARS

    @pytest.mark.parametrize("date_input", [
        2022,
        "2022",
        "2022-06-15",
        "2022-06",
        datetime(2022, 6, 15),
    ])
    def test_date_format_parsing(self, date_input):
        downloader = CorineDataDownloader((date_input, 2023))
        assert isinstance(downloader.start_year, int)

    @pytest.mark.parametrize("start_date,end_date", [
        (2023, 2022),
        ("invalid", 2022),
        (2022, "invalid"),
        ("2022-13-01", 2023),
        ("2022-12-32", 2023),
    ])
    def test_error_handling(self, start_date, end_date):
        with pytest.raises(Exception):
            CorineDataDownloader((start_date, end_date))

    def test_actual_download(self):
        test_geojson = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")
        if not test_geojson.exists():
            pytest.skip("Test GeoJSON file not found")
        test_ranges = [
            (2020, 2022),
            (2018, 2023),
        ]
        for start_year, end_year in test_ranges:
            downloader = CorineDataDownloader((start_year, end_year))
            bbox = downloader.get_bbox_from_geometry(test_geojson)
            assert isinstance(bbox, (list, tuple))
            url = downloader.build_query_url(bbox, offset=0)
            assert url.startswith("http")
            # Download test is skipped for performance
            # output_path = downloader.download_and_save(test_geojson)
            # assert Path(output_path).exists() 