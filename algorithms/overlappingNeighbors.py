import matplotlib.pyplot as plt
import networkx as nx
from random import sample
import pandas as pd
import numpy as np
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import random
from sklearn.metrics import roc_curve, auc, f1_score
from pathlib import Path


def read_specific_columns(file_path, columns):
    try:
        with open(file_path, "r") as file:
            next(file)
            data = []
            for line in file:
                parts = line.strip().split("\t")
                selected_columns = []
                for col in columns:
                    selected_columns.append(parts[col])
                data.append(selected_columns)
            return data
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def create_ppi_network(fly_interactome, fly_GO_term):
    print("")
    print("Initializing network")
    i = 1
    totalProgress = len(fly_interactome) + len(fly_GO_term)
    G = nx.Graph()
    protein_protein_edge = 0
    protein_go_edge = 0
    protein_node = 0
    go_node = 0

    # go through fly interactome, add a new node if it doesnt exists already, then add their physical interactions as edges
    for line in fly_interactome:
        if not G.has_node(line[2]):
            G.add_node(line[2], name=line[0], type="protein")
            protein_node += 1

        if not G.has_node(line[3]):
            G.add_node(line[3], name=line[1], type="protein")
            protein_node += 1

        G.add_edge(line[2], line[3], type="protein_protein")
        protein_protein_edge += 1
        print_progress(i, totalProgress)
        i += 1

    # Proteins annotated with a GO term have an edge to a GO term node
    for line in fly_GO_term:
        if not G.has_node(line[1]):
            G.add_node(line[1], type="go_term")
            go_node += 1

        G.add_edge(line[1], line[0], type="protein_go_term")
        protein_go_edge += 1
        print_progress(i, totalProgress)
        i += 1

    print("")
    print("")
    print("network summary")

    print("protein-protein edge count: ", protein_protein_edge)
    print("protein-go edge count: ", protein_go_edge)
    print("protein node count: ", protein_node)
    print("go node count: ", go_node)
    print("total edge count: ", len(G.edges()))
    print("total node count: ", len(G.nodes()))

    return G


def getNeighbors(G: nx.Graph, node, edgeType):
    res = G.edges(node, data=True)
    neighbors = []
    for edge in res:
        if edge[2]["type"] == edgeType:
            neighborNode = [edge[1], edge[2]]
            neighbors.append(neighborNode)

    return neighbors


def getGoAnnotatedProteinCount(G: nx.Graph, nodeList, goTerm):
    count = 0
    for element in nodeList:
        if G.has_edge(element[0], goTerm):
            count += 1
    return count


def print_progress(current, total, bar_length=65):
    # Calculate the progress as a percentage
    percent = float(current) / total
    # Determine the number of hash marks in the progress bar
    arrow = "-" * int(round(percent * bar_length) - 1) + ">"
    spaces = " " * (bar_length - len(arrow))

    # Choose color based on completion
    if current < total:
        color = Fore.YELLOW
    else:
        color = Fore.GREEN

    # Construct the progress bar string
    progress_bar = f"[{arrow + spaces}] {int(round(percent * 100))}%"

    # Print the progress bar with color, overwriting the previous line
    print(f"\r{color}{progress_bar}{Style.RESET_ALL}", end="")


def overlappingNeighbors(
    interactome_path: Path,
    go_path: Path,
    output_data_path: Path,
    output_image_path: Path,
    sampleSize: int,
):
    """
    evaluate overlapping neighbors method on a protein protein interaction network with go term annotation.
    """
    colorama_init()
    print("-" * 65)
    print("overlapping neighbors algorithm")

    flybase_interactome_file_path = interactome_path
    gene_association_file_path = go_path

    flybase_columns = [0, 1, 4, 5]
    fly_interactome = read_specific_columns(
        flybase_interactome_file_path, flybase_columns
    )

    fly_GO_columns = [1, 4]
    fly_GO_term = read_specific_columns(gene_association_file_path, fly_GO_columns)

    G = create_ppi_network(fly_interactome, fly_GO_term)

    positiveProteinGoTermPairs = []
    negativeProteinGoTermPairs = []
    d = {
        "protein": [],
        "goTerm": [],
        "proteinNeighbor": [],
        "goProteinEdge": [],
        "goEdge": [],
        "fScore": [],
    }

    print("")
    print("Sampling Data")

    totalSamples = sampleSize

    for edge in sample(list(fly_GO_term), totalSamples):
        positiveProteinGoTermPairs.append(edge)

    tempPairs = positiveProteinGoTermPairs.copy()
    i = 1
    for edge in positiveProteinGoTermPairs:
        sampleEdge = random.choice(tempPairs)
        tempPairs.remove(sampleEdge)
        # removes duplicate proteins and if a protein has a corresponding edge to the GO term in the network
        while sampleEdge[0] == edge[0] and not G.has_edge(sampleEdge[0], edge[1]):
            print("Found a duplicate or has an exisitng edge")
            tempPairs.append(sampleEdge)
            sampleEdge = random.choice(tempPairs)
            tempPairs.remove(sampleEdge)
        negativeProteinGoTermPairs.append([sampleEdge[0], edge[1]])
        print_progress(i, totalSamples)
        i += 1

    print("")
    print("")
    print("Calculating Protein Prediction")

    # have two sets of positive and negative protein-go_term pairs
    # for each pair, calculate the score of how well they predict whether a protein should be annotated to a GO term.
    # 50% of the data are proteins that are annotated to a GO term
    # 50% of the data are proteins that are not annotated to a GO term
    # score equation (1 + number of GoAnnotatedProteinCount) / (number of positiveProProNeighbor + number of positiveGoNeighbor)

    data = {
        "protein": [],
        "goTerm": [],
        "proProNeighbor": [],
        "goNeighbor": [],
        "goAnnotatedProProNeighbors": [],
        "score": [],
    }
    i = 1
    for positiveEdge, negativeEdge in zip(
        positiveProteinGoTermPairs, negativeProteinGoTermPairs
    ):

        # calculate the score for the positive set
        positiveProProNeighbor = getNeighbors(G, positiveEdge[0], "protein_protein")
        positiveGoNeighbor = getNeighbors(G, positiveEdge[1], "protein_go_term")
        positiveGoAnnotatedProteinCount = getGoAnnotatedProteinCount(
            G, positiveProProNeighbor, positiveEdge[1]
        )
        positiveScore = (1 + positiveGoAnnotatedProteinCount) / (
            len(positiveProProNeighbor) + len(positiveGoNeighbor)
        )

        # calculate the score for the negative set
        negativeProProNeighbor = getNeighbors(G, negativeEdge[0], "protein_protein")
        negativeGoNeighbor = getNeighbors(G, negativeEdge[1], "protein_go_term")
        negativeGoAnnotatedProteinCount = getGoAnnotatedProteinCount(
            G, negativeProProNeighbor, negativeEdge[1]
        )
        negativeScore = (1 + negativeGoAnnotatedProteinCount) / (
            len(negativeProProNeighbor) + len(negativeGoNeighbor)
        )

        # input positive and negative score to data
        data["protein"].append(positiveEdge[0])
        data["goTerm"].append(positiveEdge[1])
        data["proProNeighbor"].append(len(positiveProProNeighbor))
        data["goNeighbor"].append(len(positiveGoNeighbor))
        data["goAnnotatedProProNeighbors"].append(positiveGoAnnotatedProteinCount)
        data["score"].append(positiveScore)

        data["protein"].append(negativeEdge[0])
        data["goTerm"].append(negativeEdge[1])
        data["proProNeighbor"].append(len(negativeProProNeighbor))
        data["goNeighbor"].append(len(negativeGoNeighbor))
        data["goAnnotatedProProNeighbors"].append(negativeGoAnnotatedProteinCount)
        data["score"].append(negativeScore)

        print_progress(i, totalSamples)
        i += 1

    #prepare for roc curve by annotating the score by postiive or negative
    y_true = []
    y_scores = []

    i = 1
    for score in data["score"]:
        if i % 2 == 1:
            y_true.append(1)
        else:
            y_true.append(0)
        y_scores.append(score)
        i += 1

    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)

    print("")
    print("")
    print("Calculating optimal thresholds")

    # 1. Maximize the Youden’s J Statistic
    youden_j = tpr - fpr
    optimal_index_youden = np.argmax(youden_j)
    optimal_threshold_youden = thresholds[optimal_index_youden]

    i = 1
    # 2. Maximize the F1 Score
    # For each threshold, compute the F1 score
    f1_scores = []
    for threshold in thresholds:
        y_pred = (y_scores >= threshold).astype(int)
        f1 = f1_score(y_true, y_pred)
        f1_scores.append(f1)
        print_progress(i, len(thresholds))
        i += 1
    optimal_index_f1 = np.argmax(f1_scores)
    optimal_threshold_f1 = thresholds[optimal_index_f1]

    # 3. Minimize the Distance to (0, 1) on the ROC Curve
    distances = np.sqrt((1 - tpr) ** 2 + fpr**2)
    optimal_index_distance = np.argmin(distances)
    optimal_threshold_distance = thresholds[optimal_index_distance]

    print("")
    print("")
    print("-" * 65)
    print("Results")
    print("")

    # Print the optimal thresholds for each approach
    print(Fore.YELLOW + "Optimal Threshold (Youden's J):", optimal_threshold_youden)
    print("Optimal Threshold (F1 Score):", optimal_threshold_f1)
    print("Optimal Threshold (Min Distance to (0,1)):", optimal_threshold_distance)
    print(Style.RESET_ALL +  "")


    df = pd.DataFrame(data)
    df.to_csv(output_data_path, index=False, sep="\t")

    return (data, y_true, y_scores)