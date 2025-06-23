"""
Script to visualize the Corine Land Cover data for Berlin.

Usage:
    uv run src/uhi_analyzer/visualization/plot_berlin_corine_landcover.py

Requirements:
    - geopandas
    - matplotlib
"""
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

# Path to the Berlin Corine Land Cover GeoJSON
DATA_PATH = Path("data/raw/landcover/berlin_corine_landcover_2018.geojson")
# Path to the Berlin administrative boundary GeoJSON
BOUNDARY_PATH = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")


def main() -> None:
    """Load and plot the Berlin Corine Land Cover data by 'Code_18', with Berlin outline."""
    gdf = gpd.read_file(DATA_PATH)
    boundary = gpd.read_file(BOUNDARY_PATH)

    # CRS-Abgleich
    if boundary.crs != gdf.crs:
        boundary = boundary.to_crs(gdf.crs)

    if 'Code_18' not in gdf.columns:
        print("Spalte 'Code_18' nicht gefunden. Verfügbare Spalten:", gdf.columns.tolist())
        return

    n_classes = gdf['Code_18'].nunique()
    print(f"Anzahl unterschiedlicher Landnutzungsklassen (Code_18): {n_classes}")
    print(f"Vorhandene Klassen: {sorted(gdf['Code_18'].unique())}")

    # Plot nach Landnutzungsklasse
    ax = gdf.plot(
        column='Code_18',
        categorical=True,
        legend=True,
        figsize=(12, 12),
        edgecolor="k",
        alpha=0.7,
        cmap="tab20" if n_classes <= 20 else "tab20b"
    )
    # Berliner Umriss als Overlay
    boundary.boundary.plot(ax=ax, color="black", linewidth=2, label="Berlin Umriss")

    plt.title("Berlin Corine Land Cover nach Code_18 mit Umriss")
    plt.axis("off")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main() 