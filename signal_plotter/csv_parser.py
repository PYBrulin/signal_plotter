""" Read the content of a csv file with pandas and plot the results"""

import argparse
import glob
import logging
import os

import numpy
import pandas
import tqdm

from signal_plotter.plot_window import plot_window


class ColoredFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    magenta = "\x1b[35;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    fmt = "[%(levelname)1.1s] %(asctime)s %(filename)s:%(lineno)d - %(message)s"
    FORMATS = {
        logging.DEBUG: magenta + fmt + reset,
        logging.INFO: grey + fmt + reset,
        logging.WARNING: yellow + fmt + reset,
        logging.ERROR: red + fmt + reset,
        logging.CRITICAL: bold_red + fmt + reset,
    }

    def format(self, record) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


if __name__ == "__main__":
    logger = logging.getLogger('plot_window_tree')
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    colored_formatter = ColoredFormatter()
    stream_handler.setFormatter(colored_formatter)
    logger.addHandler(stream_handler)

    # Parse the arguments
    parser = argparse.ArgumentParser(description="Read the content of a csv file with pandas and plot the results")
    parser.add_argument("csv_file", type=str, nargs="+", help="The csv file to read")
    parser.add_argument("-x", "--x", type=str, help="The x axis column")
    # List of columns to pre-select in the plot
    parser.add_argument("-y", "--y", type=str, nargs="+", help="The y axis columns")
    args = parser.parse_args()

    items = {}

    csv_files = args.csv_file

    for csv_file in args.csv_file:
        # Check if the csv_file string represent a regex
        if any(c in csv_file for c in "*?"):
            files = glob.glob(csv_file)
            if not files:
                raise FileNotFoundError(f"No file found with the pattern {csv_file}")
            csv_files.remove(csv_file)
            csv_files.extend(files)

    for csv_file in csv_files:
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

            items[((os.path.splitext(os.path.basename(csv_file))[0] + ".") if len(args.csv_file) > 1 else "") + column] = {
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
