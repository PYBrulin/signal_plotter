""" Read the content of a csv file with pandas and plot the results"""

import argparse
import logging
import os

import numpy
import pandas
import tqdm

from signal_plotter.plot_window import plot_window

if __name__ == "__main__":
    # Parse the arguments
    parser = argparse.ArgumentParser(description="Read the content of a csv file with pandas and plot the results")
    parser.add_argument("csv_file", type=str, nargs="+", help="The csv file to read")
    parser.add_argument("-x", "--x", type=str, help="The x axis column")
    # List of columns to pre-select in the plot
    parser.add_argument("-y", "--y", type=str, nargs="+", help="The y axis columns")
    args = parser.parse_args()

    items = {}

    for csv_file in args.csv_file:
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"The file {csv_file} doesn't exist")

        # Read the csv file with a progress bar
        df = pandas.read_csv(csv_file, index_col=0)

        for column in tqdm.tqdm(df.columns, desc="Parsing columns"):
            # Check if the column is a number
            try:
                df[column] = pandas.to_numeric(df[column])
            except ValueError:
                logging.warning(f"The column {column} is not a numerical signal, skipping")
                continue

            items[os.path.splitext(os.path.basename(csv_file))[0] + "." + column] = {
                "x": numpy.ravel(df.index),
                "y": numpy.ravel(df[column]),
            }

    x_component = args.x if args.x and args.x in df.columns else df.index.name
    y_components = args.y if args.y else None

    # Plot the results
    plot_window(
        items,
        x_component=x_component,
        pre_select=y_components,
    )
