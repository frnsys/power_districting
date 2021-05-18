# From <https://raw.githubusercontent.com/PrincetonUniversity/gerrymander-geoprocessing/master/edit_shapefiles.py>

import numpy as np
import pandas as pd

# Areal interpolation
def distribute_values(df_source, source_cols, df_target, target_cols=False,
                      distribute_type='fractional', distribute_on='area',
                      distribute_round=False):
    '''
    Distribute attribute values of source geometries into the target geometries

    An example of this would be calculating population in generated precincts.
    We would take census blocks (the source geometries) and sum up their
    values into the precincts (target geometries). This is an example of
    aggregation

    Another example would be racial census tract data and disaggregating it to
    the census block level. This is an example of disaggregation

    There are two types of aggregation. fractional or winner take all. For
    disaggregation, we will rarely if ever use winner take all

    We can distribute values on area or on another attribute such as population
    However, theis aggregation attribute must be in the target dataframe

    For source geometries that do not intersect with any large geometries, we
    find the nearest centroid

    We give an option to round values and always retain totals. We als give an
    option to save the updated large shapefile if given a path

    Arguments:
        df_source:
            source shapefile providing the values to distribute

        source_cols:
            LIST of names of attributes in df_source to distribute

        df_target:
            target shapefile receiving values being distributed

        target_cols:
            LIST of names of attributes to create df_target. Elements
            in this list correpond to elements in source_cols with the same
            index. Default is just the name of the columns in the list
            source_cols

        distribute_type:
            'fractional' or 'winner take all'. Self-explantory.
            default is 'fractional'

        distribute_on:
            Either area or an attribute in target_df to distribute
            values proportional to. For disaggregation usually do not want to
            use area as the distributing attribute.

        distribute_round:
            whether to round values. If True, then we will
            round values such that we retain totals. If False, will simply
            leave distributed values as floats

    Output:
        edited df_target dataframe'''

    # Handle default for target_cols
    if target_cols is False:
            target_cols = source_cols

    # Check that target_cols and source_cols have same number of attributes
    if len(source_cols) != len(target_cols):
        print('Different number of source_cols and target_cols')
        return False

    # Check that source_cols are actually in dataframe
    if not set(source_cols).issubset(set(df_source.columns)):
        print('source_cols are not in dataframe')
        return False

    # Check that the type is either fractional area or winner take all
    if distribute_type != 'fractional':
        if distribute_type != 'winner take all':
            print('incorrect aggregation type')
            return False

    # If we are not distributing on area check if the distributing attribute
    # is in the dataframe
    if distribute_on != 'area' and distribute_on not in df_target.columns:
        print('aggregation attribute not in dataframe')
        return False

    # Let the index of ths large dataframe be an integer for indexing purposes
    df_target.index = df_target.index.astype(int)

    # Drop target_cols in large shp
    drop_cols = set(target_cols).intersection(set(df_target.columns))
    df_target = df_target.drop(columns=drop_cols)

    # Initialize the new series in the large shp
    for col in target_cols:
        df_target[col] = 0.0

    # Ensure that source columns are floats for consisting adding
    for col in source_cols:
        df_source[col] = df_source[col].astype(float)

    # construct r-tree spatial index
    si = df_target.sindex

    # Get centroid for each geometry in target shapefile
    df_target['centroid'] = df_target['geometry'].centroid

    # Find appropriate match between geometries
    for ix, row in df_source.iterrows():

        # initialize fractional area series, this will give what ratio to
        # aggregate to each target geometry
        frac_agg = pd.Series(dtype=float)

        # Get potential matches
        source_poly = row['geometry']
        matches = [df_target.index[i] for i in
                   list(si.intersection(source_poly.bounds))]

        # Only keep matches that have intersections
        matches = [m for m in matches
                   if df_target.at[m, 'geometry'].intersection(
                   source_poly).area > 0]

        # No intersections. Find nearest centroid
        if len(matches) == 0:
            source_centroid = source_poly.centroid
            dist_series = df_target['centroid'].apply(lambda x:
                                                source_centroid.distance(x))
            frac_agg.at[dist_series.idxmin()] = 1

        # Only one intersecting geometry
        elif len(matches) == 1:
            frac_agg.at[matches[0]] = 1

        # More than one intersecting geometry
        else:
            agg_df = df_target.loc[matches, :]

            # Aggregate on proper column
            if distribute_on == 'area':
                frac_agg = agg_df['geometry'].apply(lambda x:
                                                    x.intersection(
                                                    source_poly).area /
                                                    source_poly.area)

                # Add proportion that does not intersect to the target geometry
                # with the largest intersection
                leftover = 1 - frac_agg.sum()
                frac_agg.at[frac_agg.idxmax()] += leftover

            else:
                agg_df[distribute_on] = agg_df[distribute_on].astype(float)
                agg_col_sum = agg_df[distribute_on].sum()
                # print(agg_col_sum)
                frac_agg = agg_df[distribute_on].apply(lambda x:
                                                       float(x) / agg_col_sum)

        # Update value for target geometry depending on aggregate type
        for j, col in enumerate(target_cols):
            # Winner take all update
            if distribute_type == 'winner take all':
                target_ix = frac_agg.idxmax()
                df_target.loc[target_ix, col] += df_source.loc[ix,
                                                             source_cols[j]]

            # Fractional update
            elif distribute_type == 'fractional':
                # Add the correct fraction
                for ix2, val in frac_agg.iteritems():
                    df_target.loc[ix2, col] += df_source.loc[
                        ix, source_cols[j]] * val

                # Round if necessary
                if distribute_round:

                    # round and find the indexes to round up
                    round_down = df_target[col].apply(lambda x: np.floor(x))
                    decimal_val = df_target[col] - round_down
                    n = int(np.round(decimal_val.sum()))
                    round_up_ix = list(decimal_val.nlargest(n).index)

                    # Round everything down and then increment the ones that
                    # have the highest decimal value
                    df_target[col] = round_down
                    for ix3 in round_up_ix:
                        df_target.loc[ix3, col] += 1

    # Set column value as integer
    if distribute_round:
        df_target[col] = df_target[col].astype(int)

    # Save and return. also drop centroid attribute
    df_target = df_target.drop(columns=['centroid'])
    return df_target
