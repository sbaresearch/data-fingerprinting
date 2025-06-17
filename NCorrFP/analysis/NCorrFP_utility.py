import sys, os
project_root = os.path.abspath(os.path.join(os.getcwd()))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import datasets
from datasets import Adult
import csv
import pandas as pd
import argparse
import os
from datetime import datetime
import numpy as np

from sklearn import preprocessing
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
import xgboost as xgb


def utility(dataset='adult', save_results='utility'):
    """

    """
    print('NCorr-FP: Utility.\nData: {}'.format(dataset))
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    save_results += f"_{dataset}_{timestamp}.csv"  # out file
    csv_columns = ["model", "gamma", "k", "fp_len", "score_avg", "score_std"]

    # Create CSV file with headers only if it doesn't exist
    if not os.path.exists(save_results):
        with open(save_results, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(csv_columns)

    # --- Read data --- #
    data = None
    if dataset == 'adult':
        data = Adult()
    if data is None:
        exit('Please provide a valid dataset name ({})'.format(datasets.__all__))

    # cleaning the data
    # original_data.dropna()
    data.dataframe = data.dataframe.dropna()
    # encode categorical features and drop redundant
    data.number_encode_categorical()
    data.dataframe = data.dataframe.drop(['fnlwgt', 'education'], axis=1)

    X = data.get_features()
    y = data.get_target()
    scaler = preprocessing.StandardScaler()
    X = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)

    # the hyperparameter optimisation is in the separate notebook (NCorrFP analysis adult utility)
    xgb_best_params = {'subsample': 0.5, 'reg_alpha': 0.01, 'n_estimators': 160, 'max_depth': 10,
                       'learning_rate': 0.009, 'gamma': 0.0, 'colsample_bytree': 0.9}
    lr_best_params = {"solver": "newton-cg", "C": 10}
    rf_best_params = {"n_estimators": 120, "criterion": "entropy"}

    mlp_best_params = {'solver': 'adam', 'learning_rate': 'invscaling', 'hidden_layer_sizes': (50,), 'alpha': 0.001,
                       'activation': 'relu'}

    le = preprocessing.LabelEncoder()
    y = le.fit_transform(y)
    n_exp = 10
    results = []
    secret_key = 100

    categorical_attributes = list(data.categorical_attributes)
    categorical_attributes.remove('income')
    categorical_attributes.remove('education')
    fp_len = 128
    recipient_id = 0
    gamma = [2, 4, 8, 16, 32]
    ks = [300]  # 300
    # phis = [0.6, 0.9, 0.95]

    print('Parameters:\n\t-fingerprint length: {}\n\t-gamma: {}\n\t-k: {}\n\t-phi: 0.75'.format(fp_len, gamma, ks)) #, phis))

    GB_results_all = dict()
    XBG_results_all = dict()
    RF_results_all = dict()
    LR_results_all = dict()
    MLP_results_all = dict()

    for g in gamma:
        for k in ks:
#            for phi in phis:
            GB_results = []
            LR_results = []
            RF_results = []
            XGB_results = []
            MLP_results = []
            for n in range(n_exp):
                file_name = "adult_gamma{}_k{}_fingerprint_length{}_n_recipients20_sk{}_id{}_codetardos.csv".format(g, k, fp_len, secret_key+n, recipient_id)
                file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fp_datasets', 'NCorrFP',
                                         data.name + "-fp", file_name)
                fp_dataset = pd.read_csv(file_path)
                # same prepocessing as above
                fp_dataset = fp_dataset.drop(["Id", "income", 'fnlwgt', 'education'], axis=1)
                fp_dataset = fp_dataset.dropna()
                for cat in categorical_attributes:
                    label_enc = preprocessing.LabelEncoder()  # the current version of label encoder works in alphanumeric order
                    fp_dataset[cat] = label_enc.fit_transform(fp_dataset[cat])

                fp_dataset = pd.DataFrame(scaler.fit_transform(fp_dataset), columns=fp_dataset.columns)

                fp_dataset = fp_dataset.values
                # hyperparameter seach

                XGB_model = xgb.XGBClassifier(**xgb_best_params)
                XGB_scores = cross_val_score(XGB_model, fp_dataset, y, cv=10)
                XGB_results.append(np.mean(XGB_scores))
                #
                LR_model = LogisticRegression(**lr_best_params)
                LR_scores = cross_val_score(LR_model, fp_dataset, y, cv=10)
                LR_results.append(np.mean(LR_scores))
                #
                RF_model = RandomForestClassifier(**rf_best_params)
                RF_scores = cross_val_score(RF_model, fp_dataset, y, cv=10)
                RF_results.append(np.mean(RF_scores))

                MLP_model = MLPClassifier(**mlp_best_params)
                MLP_scores = cross_val_score(MLP_model, fp_dataset, y, cv=10)
                MLP_results.append(np.mean(MLP_scores))

                # print(secret_key)
            with open(save_results, mode='a', newline='') as f:
                writer = csv.writer(f)

                for model_name, results in zip(
                        ["GradientBoosting", "XGBoost", "LogisticRegression", "RandomForest", "MLP"],
                        [GB_results, XGB_results, LR_results, RF_results, MLP_results]
                ):
                    if results:  # Ensure there are results to log
                        score_avg = np.mean(results)
                        score_std = np.std(results)
                        writer.writerow([model_name, g, k, fp_len, score_avg, score_std])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Load a dataset with optional configurations.")
    # Required positional argument
    parser.add_argument("dataset", type=str, help="Dataset name.")
    # Parse arguments
    args = parser.parse_args()

    utility(args.dataset)
