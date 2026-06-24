
## python run_pipeline_QC.py <input_csv> <output_dir>

import pandas as pd
import os
import argparse
from datetime import datetime, timedelta
import inspect
import logging
import sys

# Configure logging to both terminal and file
def setup_logging(log_file_path):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger()

def check_consecutive_day_difference(input_csv, variable_name, start_date_str='', end_date_str=''):
    if not variable_name.startswith("TEMPERATURE_"):
        logger.info(f"Skipping REJECTED RULE analysis for '{variable_name}'. Not a TEMPERATURE_ variable.")
        return

    df = pd.read_csv(input_csv)
    df['DAY'] = pd.to_datetime(df['DAY'], errors='coerce')

    if variable_name not in df.columns:
        raise ValueError(f"Column '{variable_name}' not found.")
    if 'DAY' not in df.columns:
        raise ValueError("Column 'DAY' not found.")

    df = df.sort_values(by=['IDSTATION', 'DAY'])
    results = []
    all_results = []

    for station_id, group in df.groupby('IDSTATION'):
        previous_row = None

        for _, row in group.iterrows():
            if previous_row is not None:
                is_consecutive = (row['DAY'] - previous_row['DAY']).days == 1
                
                if is_consecutive:
                    temp_diff = abs(row[variable_name] - previous_row[variable_name])
                    status = "NOT OK" if temp_diff > 30 else "OK"
                else:
                    status = "OK"
            else:
                status = "OK"

            if status == "NOT OK":
                results.append({
                    'IDSTATION': station_id,
                    'DAY': row['DAY'],
                    variable_name: row[variable_name],
                    'Previous Day': previous_row['DAY'],
                    'Previous Value': previous_row[variable_name],
                    'Status': status,
                    'Days Between': (row['DAY'] - previous_row['DAY']).days,
                    'Temp Difference': abs(row[variable_name] - previous_row[variable_name]),
                    'LATITUDE': row.get('LATITUDE'),
                    'LONGITUDE': row.get('LONGITUDE'),
                    'COUNTRY': row.get('COUNTRY'),
                    'ISO_3166_1_CODE2': row.get('ISO_3166_1_CODE2')
                })
            
            all_results.append({
                'IDSTATION': station_id,
                'DAY': row['DAY'],
                variable_name: row[variable_name],
                'Status': status,
                'LATITUDE': row.get('LATITUDE'),
                'LONGITUDE': row.get('LONGITUDE'),
                'COUNTRY': row.get('COUNTRY'),
                'ISO_3166_1_CODE2': row.get('ISO_3166_1_CODE2')
            })

            previous_row = row

    results_df = pd.DataFrame(results)
    all_results_df = pd.DataFrame(all_results)

    if results_df.empty:
        logger.info("No problematic temperature differences found for consecutive days.")
        return

    not_ok_results_df = results_df[results_df['Status'] == "NOT OK"]
    
    logger.info(f"Found {len(not_ok_results_df)} cases where consecutive days had >30 temperature difference")

    base_name = os.path.splitext(os.path.basename(input_csv))[0]
    
    if not not_ok_results_df.empty:
        date_ranges = not_ok_results_df.groupby('IDSTATION')['DAY'].agg(['min', 'max']).reset_index()
        date_ranges.columns = ['IDSTATION', 'Start Date', 'End Date']
        not_ok_results_df = not_ok_results_df.merge(date_ranges, on='IDSTATION')
        
        output_csv_not_ok = os.path.join(
            os.path.dirname(input_csv),
            f"{base_name}_{variable_name}_DIFFERENCE_NOTOK_consecutive_days_{start_date_str}_to_{end_date_str}.csv"
        )
        not_ok_results_df.to_csv(output_csv_not_ok, index=False)
        logger.info(f"Problematic cases saved to {output_csv_not_ok}")
    else:
        logger.info("All consecutive day temperature differences are within acceptable range.")

    #output_csv_all = os.path.join(
    #    os.path.dirname(input_csv),
    #    f"{base_name}_{variable_name}_ALL_DIFFERENCE_OK_consecutive_days_{start_date_str}_to_{end_date_str}.csv"
    #)
    #all_results_df.to_csv(output_csv_all, index=False)
    #logger.info(f"All results saved to {output_csv_all}")

def find_and_save_consecutive_empty_cells(input_csv, n=22, start_date_str='', end_date_str=''):
    df = pd.read_csv(input_csv)
    rows_with_consecutive_nans = []

    for index, row in df.iterrows():
        count = 0
        for value in row:
            if pd.isna(value):
                count += 1
                if count >= n:
                    rows_with_consecutive_nans.append(index)
                    break
            else:
                count = 0

    empty_cells_rows = df.loc[rows_with_consecutive_nans]
    total_stations = len(df['IDSTATION'].unique())
    stations_with_empty = len(empty_cells_rows['IDSTATION'].unique())

    logger.info(f"Total stations: {total_stations}")
    logger.info(f"Stations with {n} consecutive empty cells: {stations_with_empty}")

    base_name = os.path.splitext(os.path.basename(input_csv))[0]
    output_csv = os.path.join(
        os.path.dirname(input_csv),
        f"{base_name}_consecutive_empty_cells_{n}_variables_{start_date_str}_to_{end_date_str}.csv"
    )
    empty_cells_rows.to_csv(output_csv, index=False)
    logger.info(f"Saved {len(empty_cells_rows['IDSTATION'].unique())} stations to {output_csv}")

def find_complete_time_series(input_csv, variable_name, start_date_str='', end_date_str=''):
    df = pd.read_csv(input_csv)

    if variable_name not in df.columns:
        raise ValueError(f"Column '{variable_name}' not found.")
    if 'DAY' not in df.columns:
        raise ValueError("Column 'DAY' not found.")

    results = []
    for station_id in df['IDSTATION'].unique():
        station_data = df[df['IDSTATION'] == station_id]
        
        if station_data[variable_name].notna().all():
            for _, row in station_data.iterrows():
                results.append({
                    'IDSTATION': station_id,
                    'DAY': row['DAY'],
                    variable_name: row[variable_name],
                    'LATITUDE': row.get('LATITUDE'),
                    'LONGITUDE': row.get('LONGITUDE'),
                    'COUNTRY': row.get('COUNTRY'),
                    'ISO_3166_1_CODE2': row.get('ISO_3166_1_CODE2')
                })

    results_df = pd.DataFrame(results)
    unique_stations = results_df['IDSTATION'].nunique()
    logger.info(f"Stations with complete time series for '{variable_name}': {unique_stations}")

    if results_df.empty:
        logger.info("No stations found with complete time series.")
        return

    base_name = os.path.splitext(os.path.basename(input_csv))[0]
    output_csv = os.path.join(
        os.path.dirname(input_csv),
        f"{base_name}_complete_time_series_{variable_name}_{start_date_str}_to_{end_date_str}.csv"
    )
    results_df.to_csv(output_csv, index=False)
    logger.info(f"Complete time series saved to {output_csv}")

def find_empty_days(input_csv, variable_name, start_date_str='', end_date_str=''):
    df = pd.read_csv(input_csv)
    df['DAY'] = pd.to_datetime(df['DAY'], errors='coerce')

    if variable_name not in df.columns:
        raise ValueError(f"Column '{variable_name}' not found.")
    if 'DAY' not in df.columns:
        raise ValueError("Column 'DAY' not found.")

    results = []
    for station_id in df['IDSTATION'].unique():
        station_data = df[df['IDSTATION'] == station_id]
        all_days = pd.date_range(start=station_data['DAY'].min(), end=station_data['DAY'].max())
        
        for day in all_days:
            if day not in station_data['DAY'].values:
                results.append({
                    'IDSTATION': station_id,
                    'DAY': day,
                    'VARIABLE NAME': 'MISSING',
                    'LATITUDE': station_data['LATITUDE'].iloc[0] if 'LATITUDE' in station_data else None,
                    'LONGITUDE': station_data['LONGITUDE'].iloc[0] if 'LONGITUDE' in station_data else None,
                    'COUNTRY': station_data['COUNTRY'].iloc[0] if 'COUNTRY' in station_data else None,
                    'ISO_3166_1_CODE2': station_data['ISO_3166_1_CODE2'].iloc[0] if 'ISO_3166_1_CODE2' in station_data else None,
                    'START': station_data['DAY'].min().date(),
                    'END': station_data['DAY'].max().date()
                })
            elif pd.isna(station_data.loc[station_data['DAY'] == day, variable_name].values[0]):
                results.append({
                    'IDSTATION': station_id,
                    'DAY': day,
                    'VARIABLE NAME': 'MISSING',
                    'LATITUDE': station_data['LATITUDE'].iloc[0] if 'LATITUDE' in station_data else None,
                    'LONGITUDE': station_data['LONGITUDE'].iloc[0] if 'LONGITUDE' in station_data else None,
                    'COUNTRY': station_data['COUNTRY'].iloc[0] if 'COUNTRY' in station_data else None,
                    'ISO_3166_1_CODE2': station_data['ISO_3166_1_CODE2'].iloc[0] if 'ISO_3166_1_CODE2' in station_data else None,
                    'START': station_data['DAY'].min().date(),
                    'END': station_data['DAY'].max().date()
                })

    results_df = pd.DataFrame(results)
    unique_stations = results_df['IDSTATION'].nunique()
    logger.info(f"Stations with missing days: {unique_stations}")

    if results_df.empty:
        logger.info("No missing days found.")
        return

    base_name = os.path.splitext(os.path.basename(input_csv))[0]
    output_csv = os.path.join(
        os.path.dirname(input_csv),
        f"{base_name}_missing_days_for_{variable_name}_{start_date_str}_to_{end_date_str}.csv"
    )
    results_df.to_csv(output_csv, index=False)
    logger.info(f"Missing days results saved to {output_csv}")

def find_consecutive_integer_days(input_csv, variable_name, start_date_str='', end_date_str=''):
    n_rules = {
        'TEMPERATURE_MIN': [8],
        'TEMPERATURE_MAX': [8],
        'TEMPERATURE_AVG': [8],
        'WINDSPEED': [8],
        'PRECIPITATION': [20, 30, 60, 91, 182],
        'RADIATION': [10]
    }

    try:
        # Load and validate data
        df = pd.read_csv(input_csv)
        df['DAY'] = pd.to_datetime(df['DAY'], errors='coerce')

        # Check for required columns
        required_columns = ['IDSTATION', 'DAY', variable_name]
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Column '{col}' not found. Skipping.")
                return

        # Filter out rows with NaN values for the target variable
        valid_df = df[df[variable_name].notna() & df['DAY'].notna()]

        # Sort and filter data
        valid_df = valid_df.sort_values(['IDSTATION', 'DAY'])

        # Optional date filtering
        if start_date_str:
            valid_df = valid_df[valid_df['DAY'] >= pd.to_datetime(start_date_str)]
        if end_date_str:
            valid_df = valid_df[valid_df['DAY'] <= pd.to_datetime(end_date_str)]

        # Determine n values
        var_prefix = next((k for k in n_rules.keys() if variable_name.startswith(k)), None)
        n_values = n_rules[var_prefix] if var_prefix else [8]

        for n in n_values:
            results = []
            if len(valid_df) < n:
                logger.info(f"Not enough data points for {n}-day analysis of {variable_name}")
                continue

            # Create a new DataFrame with the Consecutive column added properly
            processed_df = valid_df.assign(
                Consecutive=(valid_df[variable_name] != valid_df[variable_name].shift()).cumsum()
            )

            # Group and process
            for (station_id, consecutive_id, value), group in processed_df.groupby(['IDSTATION', 'Consecutive', variable_name]):
                if len(group) >= n:
                    # Verify consecutive days
                    day_diffs = group['DAY'].diff().dt.days
                    if all(day_diffs[1:] == 1):  # All diffs should be exactly 1 day
                        results.extend([
                            {
                                'IDSTATION': station_id,
                                'DAY': row['DAY'],
                                variable_name: value,
                                'LATITUDE': row['LATITUDE'],
                                'LONGITUDE': row['LONGITUDE'],
                                'COUNTRY': row['COUNTRY'],
                                'ISO_3166_1_CODE2': row['ISO_3166_1_CODE2'],
                                'Consecutive_Days': n
                            }
                            for _, row in group.iterrows()
                        ])

            if not results:
                logger.info(f"No consecutive integers for {variable_name} in {n}-day sequences.")
                continue

            # Save results
            output_df = pd.DataFrame(results)
            base_name = os.path.splitext(os.path.basename(input_csv))[0]
            output_file = f"{base_name}_{n}_flatliners_{variable_name}"
            if start_date_str or end_date_str:
                output_file += f"_{start_date_str}_to_{end_date_str}"
            output_file += ".csv"
            
            output_path = os.path.join(os.path.dirname(input_csv), output_file)
            output_df.to_csv(output_path, index=False)
            logger.info(f"Found {len(output_df)} entries for {n}-day consecutive sequences of {variable_name}. Saved to {output_path}")

    except Exception as e:
        logger.error(f"Error processing {variable_name}: {str(e)}")

def main(input_csv, output_dir):
    global logger  # Declare logger as global
    df = pd.read_csv(input_csv)
    df['DAY'] = pd.to_datetime(df['DAY'], errors='coerce')

    # Define start and end dates based on the DAY column in the input
    start_date = df['DAY'].min()
    end_date = df['DAY'].max()

    filtered_df = df[(df['DAY'] >= start_date) & (df['DAY'] <= end_date)].copy()

    operational_folder = f"TS_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
    full_output_path = os.path.join(output_dir, operational_folder)
    os.makedirs(full_output_path, exist_ok=True)

    # Set up logging to save to log.txt in the operational folder
    log_file_path = os.path.join(full_output_path, 'log.txt')
    logger = setup_logging(log_file_path)  # Initialize logger here

    filtered_csv = os.path.join(full_output_path, os.path.basename(input_csv).replace('.csv', f'{start_date.strftime("%Y-%m-%d")}_to_{end_date.strftime("%Y-%m-%d")}.csv'))
    filtered_df.to_csv(filtered_csv, index=False)
    
    logger.info("\nOutput configuration:")
    logger.info(f"  - Base input directory: {os.path.abspath(os.path.dirname(input_csv))}")
    logger.info(f"  - Output directory: {os.path.abspath(full_output_path)}")
    logger.info(f"  - Reading Aggregated TS: {os.path.abspath(filtered_csv)}\n")

    #logger.info(f"Filtered data saved to: {os.path.abspath(filtered_csv)}")
    #logger.info(f"All analysis results will be saved in: {os.path.abspath(full_output_path)}\n")

    variable_names = ['TEMPERATURE_MAX', 'TEMPERATURE_MIN', 'TEMPERATURE_AVG', 'PRECIPITATION', 'WINDSPEED', 'RADIATION']
    
    for variable_name in variable_names:
        logger.info(f"Running analyses for variable: {variable_name}")
        
        analyses = [
            {
                'function': find_and_save_consecutive_empty_cells,
                'args': {'input_csv': filtered_csv, 'n': 22}
            },
            #{
            #    'function': find_complete_time_series,
            #   'args': {'input_csv': filtered_csv, 'variable_name': variable_name}
            #},
            {
                'function': check_consecutive_day_difference,
                'args': {'input_csv': filtered_csv, 'variable_name': variable_name}
            },
            {
                'function': find_empty_days,
                'args': {'input_csv': filtered_csv, 'variable_name': variable_name}
            },
            {
                'function': find_consecutive_integer_days,
                'args': {'input_csv': filtered_csv, 'variable_name': variable_name}
            }
        ]
        
        date_args = {
            'start_date_str': start_date.strftime('%Y-%m-%d'),
            'end_date_str': end_date.strftime('%Y-%m-%d')
        }
        
        for analysis in analyses:
            func_name = analysis['function'].__name__
            logger.info(f"\nRunning {func_name} for {variable_name}...")
            
            args = analysis['args'].copy()
            func_params = inspect.signature(analysis['function']).parameters
            
            for date_param in ['start_date_str', 'end_date_str']:
                if date_param in func_params:
                    args[date_param] = date_args[date_param]
            
            if 'input_csv' in args:
                args['input_csv'] = filtered_csv
            
            analysis['function'](**args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze all TS station data.")
    parser.add_argument("input_csv", help="Input CSV file path")
    parser.add_argument("output_dir", help="Base output directory path")
    
    args = parser.parse_args()
   
    main(args.input_csv, args.output_dir)
