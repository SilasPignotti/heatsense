#!/usr/bin/env python3
"""
HeatSense command-line interface for Urban Heat Island analysis.

This script provides direct access to the UHI analysis backend for programmatic
use and batch processing. Supports various output formats and performance modes.

Dependencies:
    - heatsense: Main analysis package
    - argparse: Command-line argument parsing
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add source directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

try:
    from heatsense.config.settings import UHI_PERFORMANCE_MODES
    from heatsense.webapp.analysis_backend import UHIAnalysisBackend
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Install dependencies with:")
    print("   uv sync")
    print("   or")
    print("   pip install -e .")
    sys.exit(1)


def parse_arguments():
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        description="HeatSense - Urban Heat Island Analysis CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_analysis.py --area "Kreuzberg" --start-date 2023-07-01 --end-date 2023-07-31
  python run_analysis.py --area "Berlin" --start-date 2023-06-01 --end-date 2023-08-31 --mode detailed
  python run_analysis.py --area "Mitte" --start-date 2023-07-15 --end-date 2023-07-20 --mode preview

Available performance modes: preview, fast, standard, detailed
        """
    )
    
    parser.add_argument(
        '--area', 
        type=str, 
        required=True,
        help='Area name (Berlin district, locality, or "Berlin" for entire city)'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='Analysis start date (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        required=True,
        help='Analysis end date (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=list(UHI_PERFORMANCE_MODES.keys()),
        default='standard',
        help='Performance mode (default: standard)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path for results (JSON format). If not specified, saves to temp/ directory'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging output'
    )
    
    return parser.parse_args()


def validate_date_format(date_string: str) -> datetime:
    """Validate date string format and convert to datetime object."""
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_string}. Use YYYY-MM-DD")


def save_geojson_outputs(result_data: dict, analysis_id: str, output_dir: Path) -> None:
    """Save individual GeoJSON outputs to separate files."""
    geojson_outputs = [
        ('temperature_data', 'temperature', '📊 Temperature data'),
        ('hotspots', 'heat_islands', '🔥 Heat islands'),
        ('weather_stations', 'weather_stations', '🌡️ Weather stations'),
    ]
    
    for data_key, filename_suffix, description in geojson_outputs:
        if data_key in result_data and 'geojson' in result_data[data_key]:
            output_path = output_dir / f"{analysis_id}_{filename_suffix}.geojson"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_data[data_key]['geojson'], f, indent=2, ensure_ascii=False)
            print(f"   {description}: {output_path}")
    
    # Save boundary data if available
    if 'boundary' in result_data:
        boundary_path = output_dir / f"{analysis_id}_boundary.geojson"
        with open(boundary_path, 'w', encoding='utf-8') as f:
            json.dump(result_data['boundary'], f, indent=2, ensure_ascii=False)
        print(f"   🗺️ Boundary: {boundary_path}")


def print_analysis_summary(result: dict) -> None:
    """Display analysis summary information."""
    data = result.get('data', {})
    summary = data.get('summary', {})
    
    print("\n📊 Analysis Summary:")
    
    # Temperature overview
    temp_overview = summary.get('temperature_overview', {})
    if 'mean' in temp_overview:
        print(f"   • Mean temperature: {temp_overview['mean']:.1f}°C")
    
    # Hotspots count
    hotspots_count = summary.get('hotspots_count', 'N/A')
    print(f"   • Heat hotspots found: {hotspots_count}")
    
    # Execution time
    execution_time = result.get('execution_time', 'N/A')
    if isinstance(execution_time, (int, float)):
        print(f"   • Execution time: {execution_time:.1f}s")
    else:
        print(f"   • Execution time: {execution_time}")


def main():
    """Execute main CLI functionality."""
    args = parse_arguments()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Display analysis configuration
    print("🔥 HeatSense - Urban Heat Island Analysis CLI")
    print("=" * 60)
    
    try:
        # Validate date inputs
        start_date = validate_date_format(args.start_date)
        end_date = validate_date_format(args.end_date)
        
        if start_date >= end_date:
            print("❌ Error: Start date must be before end date")
            sys.exit(1)
            
    except argparse.ArgumentTypeError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    print(f"📍 Area: {args.area}")
    print(f"📅 Period: {args.start_date} to {args.end_date}")
    print(f"⚙️ Performance mode: {args.mode}")
    print(f"💾 Output: {'Custom file' if args.output else 'temp/ directory'}")
    print("=" * 60)
    
    # Initialize analysis backend
    backend = UHIAnalysisBackend(log_level="DEBUG" if args.verbose else "INFO")
    
    try:
        # Execute analysis
        result = backend.analyze(
            area=args.area,
            start_date=args.start_date,
            end_date=args.end_date,
            performance_mode=args.mode
        )
        
        # Prepare output directory and filename
        analysis_id = f"{args.area.replace(' ', '-')}_{args.start_date}_{args.end_date}_{args.mode}"
        
        if args.output:
            # Save to specified output file
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Results saved to: {output_path}")
        else:
            # Save to default temp directory
            temp_dir = Path('temp')
            temp_dir.mkdir(exist_ok=True)
            
            default_output = temp_dir / f"{analysis_id}_result.json"
            with open(default_output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Results saved to: {default_output}")
        
        # Save individual GeoJSON outputs if analysis completed successfully
        if result.get('status') == 'completed':
            output_dir = Path(args.output).parent if args.output else Path('temp')
            save_geojson_outputs(result.get('data', {}), analysis_id, output_dir)
            print_analysis_summary(result)
        else:
            print(f"⚠️ Analysis status: {result.get('status', 'unknown')}")
            if 'errors' in result:
                for error in result['errors']:
                    print(f"   ❌ {error}")
            
    except KeyboardInterrupt:
        print("\n🛑 Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()