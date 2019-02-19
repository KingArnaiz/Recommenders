# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import sys

sys.path.append("../../")

import argparse
import os
import pandas as pd
import surprise

try:
    from azureml.core import Run
    HAS_AML = True
    run = Run.get_context()
except ModuleNotFoundError:
    HAS_AML = False

from reco_utils.evaluation.python_evaluation import *
from reco_utils.recommender.surprise.surprise_utils import compute_predictions, compute_all_predictions

def svd_training(args):
    """
    Train Surprise SVD using the given hyper-parameters
    """
    print("Start training...")
    train_data = pd.read_pickle(path=os.path.join(args.datastore, args.train_datapath))
    test_data = pd.read_pickle(path=os.path.join(args.datastore, args.test_datapath))

    svd = surprise.SVD(random_state=args.random_state, n_epochs=args.epochs, verbose=args.verbose, biased=args.biased,
                       n_factors=args.n_factors, init_mean=args.init_mean, init_std_dev=args.init_std_dev,
                       lr_all=args.lr_all, reg_all=args.reg_all, lr_bu=args.lr_bu, lr_bi=args.lr_bi, lr_pu=args.lr_pu,
                       lr_qi=args.lr_qi, reg_bu=args.reg_bu, reg_bi=args.reg_bi, reg_pu=args.reg_pu,
                       reg_qi=args.reg_qi)

    train_set = surprise.Dataset.load_from_df(train_data, reader=surprise.Reader(args.surprise_reader)) \
        .build_full_trainset()
    svd.fit(train_set)

    print("Evaluating...")

    rating_metrics = args.rating_metrics
    if len(rating_metrics) > 0:
        predictions = compute_predictions(svd, test_data, usercol=args.usercol, itemcol=args.itemcol)
        for metric in rating_metrics:
            result = eval(metric)(test_data, predictions)
            print(metric, result)
            if HAS_AML:
                run.log(metric, result)

    ranking_metrics = args.ranking_metrics
    if len(ranking_metrics) > 0:
        all_predictions = compute_all_predictions(svd, train_data, usercol=args.usercol, itemcol=args.itemcol,
                                                  ratingcol=args.ratingcol, recommend_seen=args.recommend_seen)
        k = args.k
        for metric in ranking_metrics:
            result = eval(metric)(test_data, all_predictions, col_prediction='prediction', k=k)
            print("{}@{}".format(metric, k), result)
            if HAS_AML:
                run.log(metric, result)

    if len(ranking_metrics) == 0 and len(rating_metrics) == 0:
        raise ValueError("No metrics were specified.")


def main():
    parser = argparse.ArgumentParser()
    # Data path
    parser.add_argument('--datastore', type=str, dest='datastore', help="Datastore path")
    parser.add_argument('--train-datapath', type=str, dest='train_datapath')
    parser.add_argument('--test-datapath', type=str, dest='test_datapath')
    parser.add_argument('--surprise-reader', type=str, dest='surprise_reader')
    parser.add_argument('--usercol', type=str, dest='usercol', default='userID')
    parser.add_argument('--itemcol', type=str, dest='itemcol', default='itemID')
    parser.add_argument('--ratingcol', type=str, dest='ratingcol', default='rating')
    # Metrics
    parser.add_argument('--rating-metrics', type=str, nargs='*', dest='rating_metrics', default=[])
    parser.add_argument('--ranking-metrics', type=str, nargs='*', dest='ranking_metrics', default=[])
    parser.add_argument('--k', type=int, dest='k', default=None)
    parser.add_argument('--recommend-seen', dest='recommend_seen', action='store_true')
    # Training parameters
    parser.add_argument('--random-state', type=int, dest='random_state', default=0)
    parser.add_argument('--verbose', dest='verbose', action='store_true')
    parser.add_argument('--epochs', type=int, dest='epochs', default=30)
    parser.add_argument('--biased', dest='biased', action='store_true')
    # Hyperparameters to be tuned
    parser.add_argument('--n_factors', type=int, dest='n_factors', default=100)
    parser.add_argument('--init_mean', type=float, dest='init_mean', default=0.0)
    parser.add_argument('--init_std_dev', type=float, dest='init_std_dev', default=0.1)
    parser.add_argument('--lr_all', type=float, dest='lr_all', default=0.005)
    parser.add_argument('--reg_all', type=float, dest='reg_all', default=0.02)
    parser.add_argument('--lr_bu', type=float, dest='lr_bu', default=None)
    parser.add_argument('--lr_bi', type=float, dest='lr_bi', default=None)
    parser.add_argument('--lr_pu', type=float, dest='lr_pu', default=None)
    parser.add_argument('--lr_qi', type=float, dest='lr_qi', default=None)
    parser.add_argument('--reg_bu', type=float, dest='reg_bu', default=None)
    parser.add_argument('--reg_bi', type=float, dest='reg_bi', default=None)
    parser.add_argument('--reg_pu', type=float, dest='reg_pu', default=None)
    parser.add_argument('--reg_qi', type=float, dest='reg_qi', default=None)

    args = parser.parse_args()

    print("Args:", str(vars(args)), sep='\n')

    if HAS_AML:
        run.log('Number of epochs', args.epochs)

    svd_training(args)


if __name__ == "__main__":
    main()