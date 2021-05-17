## Notes

TODO document:

- EJ data source
- Add additional constraints: crossover districts, EJ data
- Incorporate energy infrastructure as a constraint?

## Usage

1. Run `gen_graph.py` to generate the district graph data.
    - Whenever you want to include different data in the initial graph, update `keep_layers` in that file, and re-run.
    - This produces `gen/graph.json`
2. Run `gen_districts.py` to generate districting proposals.

## Data

`data/src/ny_legislative_boundaries`
NYS Legislative Boundaries (includes US Congressional, State Senate and State Assembly Districts in New York State)
Revised: February 2021
<https://gis.ny.gov/gisdata/inventories/details.cfm?DSID=1360>

`data/src/ny_tracts`
<https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_36_tract.zip>

`data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb`
<https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-data.html>
<https://www2.census.gov/geo/tiger/TIGER_DP/2018ACS/ACS_2018_5YR_TRACT_36.gdb.zip>
Metadata: <https://www2.census.gov/geo/tiger/TIGER_DP/2018ACS/Metadata/TRACT_METADATA_2018.txt>

Possibly useful: <https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html>

## Census units

> Census tracts are statistical subdivisions of a county that aim to have roughly 4,000 inhabitants. Tract boundaries are usually visible features, such as roads or rivers, but they can also follow the boundaries of national parks, military reservations, or American Indian reservations. Tracts are designed to be fairly homogeneous with respect to demographic and economic conditions when they are first established. When a census tract experiences growth and the internal population grows beyond 8,000 persons, the tract is split up. This review and revision process is conducted every decade with collaboration from local planning agencies.
>
> A block group is a subdivision of a census tract and contains a cluster of blocks. Block groups usually have between 250 and 550 housing units.
>
> A census block is the smallest geographic census unit. Blocks can be bounded by visible features—such as streets—or by invisible boundaries, such as city limits. Census blocks are often the same as ordinary city blocks. Census blocks change every decade.

![From <https://learn.arcgis.com/en/related-concepts/united-states-census-geography.htm>](assets/census_units.png)
