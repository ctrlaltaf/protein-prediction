from classes.overlapping_neighbors_class import OverlappingNeighbors
from classes.overlapping_neighbors_v2_class import OverlappingNeighborsV2
from classes.overlapping_neighbors_v3_class import OverlappingNeighborsV3
from classes.protein_degree_class import ProteinDegree
from classes.protein_degree_v2_class import ProteinDegreeV2
from classes.protein_degree_v3_class import ProteinDegreeV3
from classes.sample_algorithm import SampleAlgorithm
import matplotlib.pyplot as plt
from random import sample
from pathlib import Path
from tools.helper import print_progress
import os
import sys
import pandas as pd
from colorama import init as colorama_init
from tools.helper import (
    create_ppi_network,
    read_specific_columns,
    print_progress,
    export_graph_to_pickle,
)
from tools.workflow import run_workflow, sample_data


def main():
    colorama_init()
    if not os.path.exists("output"):
        os.makedirs("output")
    if not os.path.exists("output/dataset"):
        os.makedirs("output/dataset")
    if not os.path.exists("output/data"):
        os.makedirs("output/data")
    if not os.path.exists("output/images"):
        os.makedirs("output/images")

    interactome_path = Path("./network/interactome-flybase-collapsed-weighted.txt")
    go_association_path = Path("./network/fly_proGo.csv")
    output_data_path = Path("./output/data/")
    output_image_path = Path("./output/images/")
    dataset_directory_path = Path("./output/dataset")
    graph_file_path = Path(dataset_directory_path, "graph.pickle")
    sample_size = 10000

    interactome_columns = [0, 1, 4, 5]
    interactome = read_specific_columns(interactome_path, interactome_columns, "\t")

    go_inferred_columns = [0, 2]
    go_protein_pairs = read_specific_columns(
        go_association_path, go_inferred_columns, ","
    )

    protein_list = []

    G, protein_list = create_ppi_network(interactome, go_protein_pairs)

    export_graph_to_pickle(G, graph_file_path)

    positive_dataset, negative_dataset = sample_data(
        go_protein_pairs, sample_size, protein_list, G, dataset_directory_path
    )

    # Define algorithm classes and their names
    algorithm_classes = {
        "OverlappingNeighbors": OverlappingNeighbors,
        # "OverlappingNeighborsV2": OverlappingNeighborsV2,
        # "OverlappingNeighborsV3": OverlappingNeighborsV3,
        # "ProteinDegree": ProteinDegree,
        # "ProteinDegreeV2": ProteinDegreeV2,
        # "ProteinDegreeV3": ProteinDegreeV3,
        # "SampleAlgorithm": SampleAlgorithm,
    }

    results = run_workflow(
        algorithm_classes,
        dataset_directory_path,
        graph_file_path,
        output_data_path,
        output_image_path,
    )

    sys.exit()


if __name__ == "__main__":
    main()
