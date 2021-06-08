import data
import maup
import json
from tqdm import tqdm
from gerrychain import tree
from maup.indexed_geometries import IndexedGeometries

# Ignore maup warnings
import warnings; warnings.filterwarnings('ignore', 'GeoSeries.isna', UserWarning)

def generate(graph, n_districts=20, target_pop_margin=0.02):
    """Generate districts of roughly equal population,
    within `target_pop_margin` percent"""
    print('Generating districts...')
    total_pop = sum(graph.nodes[n]['population'] for n in graph.nodes)
    ideal_pop = total_pop/n_districts
    assignment = tree.recursive_tree_part(
            graph,
            parts=range(n_districts),
            pop_target=ideal_pop,
            pop_col='population',
            epsilon=target_pop_margin,
            node_repeats=2)
    return assignment


def state_assembly(units):
    """Create districts from existing state assembly districts"""
    print('Assigning census tracts to assembly districts...')
    # NOTE if this fails because of a naive coordinate system or something like that,
    # it's possible that `gcs.csv` is missing from `GDAL_DATA` (`/usr/share/gdal` by default)
    districts = data.load_districts()
    units.to_crs(districts.crs, inplace=True)
    assignment = maup.assign(units, districts)
    assert assignment.isna().sum() == 0 # Assert all units were successfully assigned
    return assignment


def service_territories(units):
    """Create districts from existing utility service territories.
    Problem with this one is it's not contiguous and
    there are many overlapping service territories"""
    print('Assigning census tracts to service territories...')
    try:
        assignment = json.load(open('data/gen/initial/service_territories.json'))
        assignment = {int(k): v for k, v in assignment.items()}
    except FileNotFoundError:
        service_territories = data.load_service_territories()
        units.to_crs(service_territories.crs, inplace=True)
        geoms = IndexedGeometries(service_territories)
        assignment = {}
        for i, unit in tqdm(units.iterrows(), total=len(units)):
            candidates = []
            for j, intersection in geoms.intersections(unit.geometry).items():
                terr = service_territories.loc[j]
                candidates.append((j, intersection.area, terr.geometry.area))

            if len(candidates) == 1:
                assignment[i] = candidates[0][0]
            elif len(candidates) > 1:
                # If multiple candidates, pick the one with the most overlap and smallest service territory
                assignment[i] = sorted(candidates, key=lambda c: (-c[1], c[2]))[0][0]
            else:
                # If no candidates, pick the closest, smallest service territory
                for j, terr in geoms.query(unit.geometry).items():
                    candidates.append((j, unit.geometry.distance(terr), terr.area))
                assignment[i] = sorted(candidates, key=lambda c: (c[1], c[2]))[0][0]
        with open('data/gen/initial/service_territories.json', 'w') as f:
            json.dump(assignment, f)

    return assignment.values()
