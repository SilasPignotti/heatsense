#!/usr/bin/env python3
"""
HeatSense CLI Analysis Tool

Command-line interface for running Urban Heat Island analysis.
This script provides direct access to the analysis backend for programmatic use.

Usage:
    python run_analysis.py --area "Kreuzberg" --start-date 2023-07-01 --end-date 2023-07-31
    or
    uv run run_analysis.py --area "Berlin" --start-date 2023-06-01 --end-date 2023-08-31 --mode detailed
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

try:
    from heatsense.webapp.analysis_backend import UHIAnalysisBackend
    from heatsense.config.settings import UHI_PERFORMANCE_MODES
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you have installed the dependencies:")
    print("   uv sync")
    print("   or")
    print("   pip install -e .")
    sys.exit(1)

def parse_args():
    """Parse command line arguments."""
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
        help='Output file path for results (JSON format). If not specified, prints to stdout'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def validate_date(date_string):
    """Validate date format."""
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_string}. Use YYYY-MM-DD")

def main():
    """Main CLI function."""
    args = parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔥 HeatSense - Urban Heat Island Analysis CLI")
    print("=" * 60)
    
    # Validate dates
    try:
        start_date = validate_date(args.start_date)
        end_date = validate_date(args.end_date)
        
        if start_date >= end_date:
            print("❌ Error: Start date must be before end date")
            sys.exit(1)
            
    except argparse.ArgumentTypeError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Display analysis parameters
    print(f"📍 Area: {args.area}")
    print(f"📅 Period: {args.start_date} to {args.end_date}")
    print(f"⚙️  Mode: {args.mode}")
    print(f"💾 Output: {'File' if args.output else 'temp/ directory + Console'}")
    print("=" * 60)
    
    # Initialize backend
    backend = UHIAnalysisBackend(log_level="DEBUG" if args.verbose else "INFO")
    
    try:
        # Run analysis
        result = backend.analyze(
            area=args.area,
            start_date=args.start_date,
            end_date=args.end_date,
            performance_mode=args.mode
        )
        
        # Handle output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save main result file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Results saved to: {output_path}")
            
            # Save individual GeoJSON files to temp directory if analysis was successful
            if result.get('status') == 'completed':
                data = result.get('data', {})
                temp_dir = Path('temp')
                temp_dir.mkdir(exist_ok=True)
                
                analysis_id = f"{args.area.replace(' ', '-')}_{args.start_date}_{args.end_date}_{args.mode}"
                
                # Save temperature layer
                if 'temperature_data' in data and 'geojson' in data['temperature_data']:
                    temp_path = temp_dir / f"{analysis_id}_temperature.geojson"
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        json.dump(data['temperature_data']['geojson'], f, indent=2, ensure_ascii=False)
                    print(f"   📊 Temperature data: {temp_path}")
                
                # Save hotspots layer
                if 'hotspots' in data and 'geojson' in data['hotspots']:
                    hotspots_path = temp_dir / f"{analysis_id}_heat_islands.geojson"
                    with open(hotspots_path, 'w', encoding='utf-8') as f:
                        json.dump(data['hotspots']['geojson'], f, indent=2, ensure_ascii=False)
                    print(f"   🔥 Heat islands: {hotspots_path}")
                
                # Save boundary layer
                if 'boundary' in data:
                    boundary_path = temp_dir / f"{analysis_id}_boundary.geojson"
                    with open(boundary_path, 'w', encoding='utf-8') as f:
                        json.dump(data['boundary'], f, indent=2, ensure_ascii=False)
                    print(f"   🗺️ Boundary: {boundary_path}")
                
                # Save weather stations if available
                if 'weather_stations' in data and 'geojson' in data['weather_stations']:
                    weather_path = temp_dir / f"{analysis_id}_weather_stations.geojson"
                    with open(weather_path, 'w', encoding='utf-8') as f:
                        json.dump(data['weather_stations']['geojson'], f, indent=2, ensure_ascii=False)
                    print(f"   🌡️ Weather stations: {weather_path}")
                
                # Print summary to console
                summary = data.get('summary', {})
                print("\n📊 Analysis Summary:")
                print(f"   • Mean temperature: {summary.get('temperature_overview', {}).get('mean', 'N/A')}°C")
                print(f"   • Hotspots found: {summary.get('hotspots_count', 'N/A')}")
                print(f"   • Execution time: {result.get('execution_time', 'N/A')}s")
            
        else:
            # If no output file specified but analysis successful, save to temp directory
            if result.get('status') == 'completed':
                temp_dir = Path('temp')
                temp_dir.mkdir(exist_ok=True)
                
                analysis_id = f"{args.area.replace(' ', '-')}_{args.start_date}_{args.end_date}_{args.mode}"
                default_output = temp_dir / f"{analysis_id}_result.json"
                
                with open(default_output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"📄 Full results automatically saved to: {default_output}")
                
                # Also save GeoJSON files
                data = result.get('data', {})
                if 'temperature_data' in data and 'geojson' in data['temperature_data']:
                    temp_path = temp_dir / f"{analysis_id}_temperature.geojson"
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        json.dump(data['temperature_data']['geojson'], f, indent=2, ensure_ascii=False)
                    print(f"📊 Temperature data: {temp_path}")
            
            # Print summary to stdout
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    except KeyboardInterrupt:
        print("\n🛑 Analysis stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()