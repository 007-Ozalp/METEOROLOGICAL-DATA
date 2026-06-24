
## python run_pipeline_ETL.py <file1.csv> <file2.csv> --merge_column IDSTATION --output_dir ./out --region EU


import pandas as pd
import argparse
import os

def read_and_process_csv(file_path1, file_path2, merge_column='IDSTATION'):
    """
    Reads two CSV files, processes them to convert string representations of numbers,
    and merges them on a specified column.

    Parameters:
    - file_path1: str, path to the first CSV file to be read.
    - file_path2: str, path to the second CSV file to be read.
    - merge_column: str, the column name on which to merge the two DataFrames.

    Returns:
    - DataFrame: A pandas DataFrame resulting from the merge of the two processed DataFrames.
    """
    def read_csv_with_fallback(file_path):
        """Reads a CSV file with UTF-8 encoding, falling back to Latin-1 if necessary."""
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except Exception:
            return pd.read_csv(file_path, encoding='latin1')

    def convert_value(value):
        """Converts string representations of numbers to their appropriate types."""
        if isinstance(value, str):
            # Remove any thousands separators (periods) and replace decimal comma with a dot
            value = value.replace('.', '').replace(',', '.')
            # Try to convert to int first
            try:
                return int(value)
            except ValueError:
                # If conversion to int fails, try to convert to float
                try:
                    return float(value)
                except ValueError:
                    return value  # Return original value if it cannot be converted
        return value

    def process_dataframe(df):
        """Processes the DataFrame to convert values and format the DAY column."""
        # Convert all values in the DataFrame
        df = df.map(convert_value)
        # Convert the DAY column to datetime format if it exists
        if 'DAY' in df.columns:
            df['DAY'] = pd.to_datetime(df['DAY'], format='%d-%b-%y', errors='coerce')
        return df

    # Read and process both CSV files
    df1 = read_csv_with_fallback(file_path1)
    df2 = read_csv_with_fallback(file_path2)

    df1 = process_dataframe(df1)
    df2 = process_dataframe(df2)

    # Merge the two DataFrames on the specified column
    merged_df = pd.merge(df1, df2, on=merge_column, how='inner')

    # Convert columns to appropriate types after merging
    for col in merged_df.columns:
        if 'ID' in col:  # Check if the column name contains 'ID'
            # Check if all values are whole numbers (including NaN)
            if (merged_df[col].dropna() % 1 == 0).all():
                # Convert to int64, allowing NaN to remain as NaN
                merged_df[col] = merged_df[col].astype('Int64')  # Use 'Int64' for nullable integers

    return merged_df

def filter_and_save_eu(merged_df, output_dir):
    """
    Filters the merged DataFrame for European latitude and longitude ranges
    and saves the result to a CSV file.

    Parameters:
    - merged_df: DataFrame, the merged DataFrame to filter.
    - output_dir: str, directory to save the output CSV file.
    """
    # Convert LATITUDE and LONGITUDE to numeric, coercing errors
    merged_df['LATITUDE'] = pd.to_numeric(merged_df['LATITUDE'], errors='coerce')
    merged_df['LONGITUDE'] = pd.to_numeric(merged_df['LONGITUDE'], errors='coerce')

    # Filter for European coordinates
    merged_df_eu = merged_df[(merged_df['LATITUDE'] >= 30) & (merged_df['LATITUDE'] <= 72) &
                              (merged_df['LONGITUDE'] >= -10) & (merged_df['LONGITUDE'] <= 46)]
    merged_df_eu = merged_df_eu.sort_values(by='DAY', ascending=True)

    # Calculate start_date and end_date from the merged DataFrame
    start_date = merged_df['DAY'].min().strftime('%Y%m%d') if 'DAY' in merged_df.columns else 'unknown_start'
    end_date = merged_df['DAY'].max().strftime('%Y%m%d') if 'DAY' in merged_df.columns else 'unknown_end'

    # Construct the output filename for the EU data
    output_filename_eu = f"STATIONS_EU_{start_date}_{end_date}.csv"
    output_path_eu = os.path.join(output_dir, output_filename_eu)

    # Save the filtered DataFrame to the output CSV file
    merged_df_eu.to_csv(output_path_eu, index=False, encoding='utf-8')


def save_merged_data(merged_df, output_dir):
    """
    Saves the merged DataFrame to a CSV file.

    Parameters:
    - merged_df: DataFrame, the merged DataFrame to save.
    - output_dir: str, directory to save the output CSV file.
    """
    merged_df = merged_df.sort_values(by='DAY', ascending=True)

    start_date = merged_df['DAY'].min().strftime('%Y%m%d') if 'DAY' in merged_df.columns else 'unknown_start'
    end_date = merged_df['DAY'].max().strftime('%Y%m%d') if 'DAY' in merged_df.columns else 'unknown_end'
    output_filename = f"STATIONS_{start_date}_{end_date}.csv"
    output_path = os.path.join(output_dir, output_filename)

    # Save the merged DataFrame to the output CSV file
    merged_df.to_csv(output_path, index=False)

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Process and merge two CSV files.')
    parser.add_argument('file1', type=str, help='Path to the first CSV file')
    parser.add_argument('file2', type=str, help='Path to the second CSV file')
    parser.add_argument('--merge_column', type=str, default='IDSTATION', help='Column name to merge on (default: IDSTATION)')
    parser.add_argument('--output_dir', type=str, required=True, help='Directory to save the output CSV file')
    parser.add_argument('--region', type=str, choices=['EU', 'ALL'], help='Region to filter (default: EU)', default='EU')

    args = parser.parse_args()

    # Read and process the CSV files
    merged_df = read_and_process_csv(args.file1, args.file2, args.merge_column)

    # Select the first and last rows
    selected_rows = pd.concat([merged_df.head(1), merged_df.tail(1)])

    # Print the resulting DataFrame
    print("Merged DataFrame:")
    print(merged_df)

    # Print the data types of all columns
    print("\nData types of all columns:")
    print(merged_df.dtypes)

    # If the region is EU, filter and save the EU data
    if args.region == 'EU':
        filter_and_save_eu(merged_df, args.output_dir)
        print("Filtered and saved data for the EU region.")
    
    # If the region is ALL, save the merged DataFrame
    if args.region == 'ALL':
        save_merged_data(merged_df, args.output_dir)
        print("Saved merged data for all regions.")

if __name__ == '__main__':
    main()