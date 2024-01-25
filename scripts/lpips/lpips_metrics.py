import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas


def load_from_csv(filename):
    return pandas.read_csv(filename, index_col=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-i", "--input-csv", action="append", required=True)
    opt = parser.parse_args()
    inputs_csv = [Path(file) for file in opt.input_csv]
    datas = [load_from_csv(input_csv) for input_csv in inputs_csv]
    mins = [data.to_numpy().min(axis=0) for data in datas]
    plt.boxplot(
        mins,
        patch_artist=True,
        labels=[input_csv.stem.replace("+", "\n") for input_csv in inputs_csv]
    )
    plt.xlabel("Benchmark datasets")
    plt.ylabel("Min-LPIPS")
    plt.show()
