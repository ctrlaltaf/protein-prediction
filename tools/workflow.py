from sklearn.metrics import roc_curve, auc, precision_recall_curve
from tools.helper import print_progress
from sklearn.metrics import f1_score
import numpy as np
from tools.helper import add_print_statements, generate_random_colors
from pathlib import Path
import matplotlib.pyplot as plt
import random
from random import sample
import pandas as pd
from operator import itemgetter


def run_workflow(
    algorithm_classes,
    input_directory_path,
    graph_file_path,
    output_data_path,
    output_image_path,
    threshold,
    figures,
):
    print("")
    print("-" * 65)
    print("Calculating Protein Prediction")
    results = {}
    i = 1
    for algorithm_name, algorithm_class in algorithm_classes.items():
        print("")
        print(f"{i} / {len(algorithm_classes)}: {algorithm_name} Algorithm")
        current = run_algorithm(
            algorithm_class, input_directory_path, graph_file_path, output_data_path
        )
        current = run_metrics(current)
        results[algorithm_name] = current
        i += 1

    if threshold:
        run_thresholds(results, algorithm_classes, output_data_path)
        if figures:
            generate_figures(algorithm_classes, results, output_image_path)

    return results


def run_algorithm(
    algorithm_class,
    input_directory_path,
    graph_file_path,
    output_data_path,
):
    # Create an instance of the algorithm class
    algorithm = algorithm_class()

    # Predict using the algorithm
    y_score, y_true = algorithm.predict(
        input_directory_path, graph_file_path, output_data_path
    )

    # Access y_true and y_score attributes for evaluation
    algorithm.set_y_score(y_score)
    algorithm.set_y_true(y_true)

    results = {"y_true": y_true, "y_score": y_score}

    return results


def run_metrics(current):
    # Compute ROC curve and ROC area for a classifier
    current["fpr"], current["tpr"], current["thresholds"] = roc_curve(
        current["y_true"], current["y_score"]
    )
    current["roc_auc"] = auc(current["fpr"], current["tpr"])

    # Compute precision-recall curve and area under the curve for a classifier
    current["precision"], current["recall"], _ = precision_recall_curve(
        current["y_true"], current["y_score"]
    )
    current["pr_auc"] = auc(current["recall"], current["precision"])

    return current


def run_thresholds(results, algorithm_classes, output_data_path):
    print("")
    print("-" * 65)
    print("Calculating Optimal Thresholds")

    j = 1
    threshold_results = []
    # Calculate thresholding for each method w/ three threshold metrics
    for algorithm_name, metrics in results.items():
        print("")
        print(f"{j} / {len(algorithm_classes)}: {algorithm_name} Algorithm")
        # print(f"Calculating optimal thresholds: {algorithm_name}")
        # 1. Maximize the Youden’s J Statistic
        youden_j = metrics["tpr"] - metrics["fpr"]
        optimal_index_youden = np.argmax(youden_j)
        optimal_threshold_youden = metrics["thresholds"][optimal_index_youden]

        # i = 1
        # # 2. Maximize the F1 Score
        # # For each threshold, compute the F1 score
        # f1_scores = []
        # for threshold in metrics["thresholds"]:
        #     y_pred = (metrics["y_score"] >= threshold).astype(int)
        #     f1 = f1_score(metrics["y_true"], y_pred)
        #     f1_scores.append(f1)
        #     print_progress(i, len(metrics["thresholds"]))
        #     i += 1
        # optimal_index_f1 = np.argmax(f1_scores)
        # optimal_threshold_f1 = metrics["thresholds"][optimal_index_f1]

        # 3. Minimize the Distance to (0, 1) on the ROC Curve
        distances = np.sqrt((1 - metrics["tpr"]) ** 2 + metrics["fpr"] ** 2)
        optimal_index_distance = np.argmin(distances)
        optimal_threshold_distance = metrics["thresholds"][optimal_index_distance]

        threshold_results.append(algorithm_name)
        threshold_results.append(
            f"Optimal Threshold (Youden's J): {optimal_threshold_youden}"
        )
        # threshold_results.append(
        #     f"Optimal Threshold (F1 Score): {optimal_threshold_f1}"
        # )
        threshold_results.append(
            f"Optimal Threshold (Min Distance to (0,1)): {optimal_threshold_distance}"
        )

        j += 1

    add_print_statements(
        Path(output_data_path, "threshold_results.txt"), threshold_results
    )


def generate_figures(algorithm_classes, results, output_image_path):
    # Generate ROC and PR figures to compare methods

    colors = generate_random_colors(len(algorithm_classes))

    sorted_results = sort_results_by(results, "roc_auc")
    print("ROC")
    i = 0
    plt.figure()
    for algorithm_name, metrics in sorted_results.items():
        print(algorithm_name, metrics["roc_auc"])
        plt.plot(
            metrics["fpr"],
            metrics["tpr"],
            color=colors[i],
            lw=2,
            label=f"{algorithm_name} (area = %0.2f)" % metrics["roc_auc"],
        )
        i += 1

    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Receiver Operating Characteristic")
    plt.legend(loc="lower right")
    plt.savefig(Path(output_image_path, "multiple_roc_curves.png"))
    plt.show()

    sorted_results = sort_results_by(results, "pr_auc")
    print("PR")
    i = 0
    plt.figure()
    for algorithm_name, metrics in sorted_results.items():
        print(algorithm_name, metrics["pr_auc"])
        plt.plot(
            metrics["recall"],
            metrics["precision"],
            color=colors[i],
            lw=2,
            label=f"{algorithm_name} (area = %0.2f)" % metrics["pr_auc"],
        )
        i += 1
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve")
    plt.legend(loc="lower left")
    plt.savefig(Path(output_image_path, "multiple_pr_curves.png"))
    plt.show()


def sample_data(go_protein_pairs, sample_size, protein_list, G, input_directory_path):
    positive_dataset = {"protein": [], "go": []}
    negative_dataset = {"protein": [], "go": []}
    # sample the data
    for edge in sample(list(go_protein_pairs), sample_size):
        positive_dataset["protein"].append(edge[0])
        positive_dataset["go"].append(edge[1])

    i = 1

    for protein, go in zip(positive_dataset["protein"], positive_dataset["go"]):
        sample_edge = random.choice(protein_list)
        # removes if a protein has a corresponding edge to the GO term in the network
        while G.has_edge(sample_edge["id"], go):
            sample_edge = random.choice(protein_list)
        negative_dataset["protein"].append(sample_edge["id"])
        negative_dataset["go"].append(go)
        print_progress(i, sample_size)
        i += 1

    positive_df = pd.DataFrame(positive_dataset)
    negative_df = pd.DataFrame(negative_dataset)

    positive_df.to_csv(
        Path(input_directory_path, "positive_protein_go_term_pairs.csv"),
        index=False,
        sep="\t",
    )
    negative_df.to_csv(
        Path(input_directory_path, "negative_protein_go_term_pairs.csv"),
        index=False,
        sep="\t",
    )

    return positive_dataset, negative_dataset


def get_datasets(input_directory_path):
    positive_dataset = {"protein": [], "go": []}
    negative_dataset = {"protein": [], "go": []}
    with open(
        Path(input_directory_path, "positive_protein_go_term_pairs.csv"), "r"
    ) as file:
        next(file)
        for line in file:
            parts = line.strip().split("\t")
            # print(parts[0])
            positive_dataset["protein"].append(parts[0])
            positive_dataset["go"].append(parts[1])

    with open(
        Path(input_directory_path, "negative_protein_go_term_pairs.csv"), "r"
    ) as file:
        next(file)
        for line in file:
            parts = line.strip().split("\t")
            # print(parts[0])
            negative_dataset["protein"].append(parts[0])
            negative_dataset["go"].append(parts[1])

    return positive_dataset, negative_dataset


def sort_results_by(results, key):
    algorithm_tuple_list = []

    # make a list of tuples where a tuple is (algorithm_name, the metric we will be sorting by)
    for algorithm_name, metrics in results.items():
        algorithm_tuple_list.append((algorithm_name, metrics[key]))

    algorithm_tuple_list = sorted(algorithm_tuple_list, key=itemgetter(1), reverse=True)

    sorted_results = {}
    for algorithm in algorithm_tuple_list:
        sorted_results[algorithm[0]] = results[algorithm[0]]
    return sorted_results
