from classes.base_algorithm_class import BaseAlgorithm
import networkx as nx
import pandas as pd
from colorama import init as colorama_init
from colorama import Fore, Back, Style
from pathlib import Path
from tools.helper import print_progress, normalize
import random


class SampleAlgorithm(BaseAlgorithm):
    def __init__(self):
        self.y_score = []
        self.y_true = []

    def predict(
        self,
        positive_data_set,
        negative_data_set,
        G: nx.graph,
        output_data_directory,
    ):
        """
        evaluate a random approach method on a protein protein interaction network with go term annotation.
        """
        colorama_init()
        # initialize an objext that will hold the prediction data
        data = {
            "protein": [],
            "go_term": [],
            "score": [],
            "norm_score": [],
            "true_label": [],
        }

        i = 1
        # iterate through the positive and negative dataset and calculate the method's prediction score
        for positive_protein, positive_go, negative_protein, negative_go in zip(
            positive_data_set["protein"],
            positive_data_set["go"],
            negative_data_set["protein"],
            negative_data_set["go"],
        ):
            # prediction logic for the positive and negative data set entry
            positive_score = random.random()
            negative_score = random.random()

            # input the positive data
            data["protein"].append(positive_protein)
            data["go_term"].append(positive_go)
            data["score"].append(positive_score)
            data["true_label"].append(1)

            # input the negative data
            data["protein"].append(negative_protein)
            data["go_term"].append(negative_go)
            data["score"].append(negative_score)
            data["true_label"].append(0)
            print_progress(i, len(positive_data_set["protein"]))
            i += 1

        # need to normalise the data
        normalized_data = normalize(data["score"])
        for item in normalized_data:
            data["norm_score"].append(item)

        # convert the data to a pandas dataframe and sort by highest norm_score to lowest
        df = pd.DataFrame(data)
        df = df.sort_values(by="norm_score", ascending=False)

        # output the result data
        df.to_csv(
            Path(output_data_directory, "sample_algorithm_data.csv"),
            index=False,
            sep="\t",
        )

        # ALWAYS set the class attribute variables to the norm_score and true_label
        self.y_score = df["norm_score"].to_list()
        self.y_true = df["true_label"].to_list()
