import sys
sys.path.append("/home/sarcevic/fingerprinting-toolbox/")

import matplotlib.pyplot as plt
import pickle
from pprint import pprint
from utilities import *
from scheme import AKScheme
import numpy as np
from attacks import *
from datasets import *
import time
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import collections


def get_experimental_gammae(amount, data_len, fp_len):
    # returns the gammae based on calculation: data_len/(gamma*fp_len) > 1; min gamma is 1
    # gamma values are uniformelly distributed
    # todo: log distribution of gamma values, i.e. get smth like 1, 2, 4, 6, 10, 16, 25...
    min_gamma = 1
    max_gamma = int(data_len/fp_len)
    step = int((max_gamma - min_gamma) / amount)
    gammae = [g for g in range(min_gamma, max_gamma, step)]
    return gammae


def get_marks_per_attribute(path_to_fp_data, original_data):
    percentages = []
    onlyfiles = [f for f in os.listdir(path_to_fp_data) if os.path.isfile(os.path.join(path_to_fp_data, f))]

    for file in onlyfiles:
        fingerprinted_data = pd.read_csv(os.path.join(path_to_fp_data, file))
        percentage = {}
        for index in range(len(original_data.columns)):
            original = original_data[original_data.columns[index]]
            fingerprinted = fingerprinted_data[original_data.columns[index]]
            num_of_changes = len(original.compare(fingerprinted))
            percentage[original_data.columns[index]] = (num_of_changes / len(original_data)) * 100
        percentages.append(percentage)
    return percentages


def get_insights(data, target, primary_key_attribute=None, exclude=None, include=None):
    dataset = None
    if isinstance(data, pd.DataFrame):
        dataset = data
    elif isinstance(data, str):
        print('given the data path')
        dataset = pd.read_csv(data)
    if exclude is None:
        exclude = []
    exclude.append(target)
    fig,ax = plt.subplots()

    # ------------------ #
    # EXPERIMENTAL SETUP #
    # ------------------ #
    fp_len = 8  # for this also figure out a nice setup to choose a good val
    gammae = get_experimental_gammae(3, len(dataset), fp_len)
    xi = 1
    numbuyers = 10

    print('Placeholder for mean / var analysis')
    # define the scheme
    n_experiments = 2
    for exp_idx in range(n_experiments):
        for gamma in gammae:
            # todo: CHANGE SECRET KEY IF OUTER LOOP IS ADDED!
            secret_key = gamma*exp_idx
            scheme = AKScheme(gamma, xi, fp_len, secret_key, numbuyers)
            fingerprinted_data = scheme.insertion(dataset, 1, save=True,
                                                  write_to="parameter_guidelines/evaluation/gamma{}_xi{}_L{}/{}_{}.csv".format(gamma, xi, fp_len, exp_idx, int(time.time())),
                                                  exclude=exclude,
                                                  primary_key_attribute=primary_key_attribute)

    results = {}
    for gamma in gammae:
        marks_percentage_per_attribute = get_marks_per_attribute("parameter_guidelines/evaluation/gamma{}_xi{}_L{}".format(gamma, xi, fp_len), dataset)  # returns a list of 100 evaluated datasets
        pprint(marks_percentage_per_attribute)
        results[gamma] = marks_percentage_per_attribute
    attr = ['clump-thickness']
    print(np.mean(results[1][i]['bare-nuclei'] for i in range(n_experiments)))
    pprint(results)
    print('Placeholder for classification analysis')
    print('Placeholder for robustness analysis via extraction rate')
    print('Placeholder for robustness analysis against attacks')
    pass


# from how much remaining data can the fingerprint still be extracted?
# todo: create a class Dataset that contains these stuff like primary-key-attr, exclude, include and other related stuffs
def inverse_robustness(attack, scheme,
                       primary_key_attribute=None, exclude=None, n_experiments=100, confidence_rate=0.99,
                       attack_granularity=0.10):
    attack_strength = 0
    # attack_strength = attack.get_strongest(attack_granularity)  # this should return 0+attack_granularity in case of horizontal subset attack
    # attack_strength = attack.get_weaker(attack_strength, attack_granularity)
    while True:
        if isinstance(attack, VerticalSubsetAttack):
            attack_strength -= 1  # lower the strength of the attack
            if attack_strength == 0:
                break
        else:
            # in case of horizontal attack, the attack strength is actually (1-attack_strength), i.e.
            # how much data will stay in the release, not how much it will be deleted
            attack_strength += attack_granularity  # lower the strength of the attack
            if round(attack_strength, 2) >= 1.0:
                break
        robust = True
        success = n_experiments
        for exp_idx in range(n_experiments):
            # insert the data
            user = 1
            sk = exp_idx
            #fingerprinted_data = scheme.insertion(data, user, secret_key=sk, exclude=exclude,
            #                                      primary_key_attribute=primary_key_attribute)
            fingerprinted_data = pd.read_csv('parameter_guidelines/fingerprinted_data/adult/universal_g{}_x{}_l{}_u{}_sk{}.csv'.format(scheme.get_gamma(), 1,
                                                                                               scheme.get_fplen(),
                                                                                               user, sk))
            if attack_strength == -1:  # remember the strongest attack
                attack_vertical_max = len(fingerprinted_data.columns.drop('income'))
                attack_strength = attack_vertical_max - 1
            if isinstance(attack, VerticalSubsetAttack):
                attacked_data = attack.run_random(fingerprinted_data, attack_strength, seed=sk,
                                                  keep_columns=['income'])
            else:
                attacked_data = attack.run(fingerprinted_data, strength=attack_strength, random_state=sk)

            # try detection
            orig_attr = fingerprinted_data.columns.drop('income')
            suspect = scheme.detection(attacked_data, sk, exclude=exclude, primary_key_attribute=primary_key_attribute,
                                       original_attributes=orig_attr)

            if suspect != user:
                success -= 1
            if success / n_experiments < confidence_rate:
                robust = False
                print('-------------------------------------------------------------------')
                print('-------------------------------------------------------------------')
                print(
                    'Attack with strength ' + str(attack_strength) + " is too strong. Halting after " + str(exp_idx) +
                    " iterations.")
                print('-------------------------------------------------------------------')
                print('-------------------------------------------------------------------')
                break  # attack too strong, continue with a lighter one
        if robust:
            if isinstance(attack, VerticalSubsetAttack):
                attack_strength = round(attack_strength / attack_vertical_max, 2)
            return round(attack_strength, 2)
    if isinstance(attack, VerticalSubsetAttack):
        attack_strength = round(attack_strength / attack_vertical_max, 2)
    return round(attack_strength, 2)

# returns robustness (=from how much remaining data can the fingerprint still be extracted with confidence_rate based
# on n_experiments)
# can be applied for horizontal and vertical subset attack and bit-flipping attack
# attack and scheme need to be provided as instances of Attack and Scheme abstract classes, respectively
def robustness(attack, scheme, data, exclude=None, include=None, n_experiments=100, confidence_rate=0.99,
               attack_granularity=0.10):
    attack_strength = 1  # defining the strongest attack
    attack_vertical_max = -1
    # attack_strength = attack.get_strongest(attack_granularity)  # this should return 0+attack_granularity in case of horizontal subset attack
    # attack_strength = attack.get_weaker(attack_strength, attack_granularity)
    while True:
        if isinstance(attack, VerticalSubsetAttack):
            attack_strength -= 1  # lower the strength of the attack
            if attack_strength == 0 and attack_vertical_max != -1:
                break
        else:
            # how much data will stay in the release, not how much it will be deleted
            attack_strength -= attack_granularity  # lower the strength of the attack
            if round(attack_strength, 2) <= 0:  # break if the weakest attack is reached
                break
        robust = True  # for now it's robust
        success = n_experiments
        for exp_idx in range(n_experiments):
            # insert the data
            user = 1
            sk = exp_idx
            #fingerprinted_data = scheme.insertion(data, user, secret_key=sk, exclude=exclude,
            #                                      primary_key_attribute=primary_key_attribute)
            if include is None:
                if isinstance(data, GermanCredit):
                    fingerprinted_data = pd.read_csv('parameter_guidelines/fingerprinted_data/' + data.to_string() +
                                                     '/attr_subset_20' +
                                                     '/universal_g{}_x{}_l{}_u{}_sk{}.csv'.format(scheme.get_gamma(), 1,
                                                                                                       scheme.get_fplen(),
                                                                                                       user, sk))
                elif isinstance(data, Nursery):
                    fingerprinted_data = pd.read_csv('parameter_guidelines/fingerprinted_data/' + data.to_string() +
                                                     '/attr_subset_8' +
                                                     '/universal_g{}_x{}_l{}_u{}_sk{}.csv'.format(scheme.get_gamma(), 1,
                                                                                                       scheme.get_fplen(),
                                                                                                       user, sk))
            else:
                fingerprinted_data = pd.read_csv('parameter_guidelines/fingerprinted_data/' + data.to_string() +
                                                 '/attr_subset_' + str(len(include)) +
                                                 '/universal_g{}_x{}_l{}_u{}_sk{}.csv'.format(scheme.get_gamma(), 1,
                                                                                              scheme.get_fplen(),
                                                                                              user, sk))
            if isinstance(attack, VerticalSubsetAttack):
                if attack_vertical_max == -1:  # remember the strongest attack and initiate the attack strength
                    attack_vertical_max = len(fingerprinted_data.columns.drop([data.get_target_attribute(),
                                                                               data.get_primary_key_attribute()]))
                    attack_strength = attack_vertical_max - 1
                attacked_data = attack.run_random(fingerprinted_data, attack_strength,
                                                  keep_columns=[data.get_target_attribute(),
                                                                data.get_primary_key_attribute()], seed=sk)
            else:
                attacked_data = attack.run(fingerprinted_data, strength=attack_strength, random_state=sk)

            # try detection
            orig_attr = fingerprinted_data.columns.drop([data.get_target_attribute(),
                                                        data.get_primary_key_attribute()])
            #suspect = scheme.detection(attacked_data, sk, exclude=exclude,
            #                           primary_key_attribute=data.primary_key_attribute(),
            #                           original_attributes=orig_attr)
            if include is not None:
                original_attributes = pd.Series(data=include)
            else:
                original_attributes = pd.Series(
                    data=['checking_account', 'duration', 'credit_hist', 'purpose',
                          'credit_amount', 'savings', 'employment_since', 'installment_rate',
                          'sex_status', 'debtors', 'residence_since', 'property', 'age',
                          'installment_other', 'housing', 'existing_credits', 'job',
                          'liable_people', 'tel', 'foreign'])
            suspect = scheme.detection(attacked_data, secret_key=sk, primary_key_attribute='Id',
                                       original_attributes=original_attributes,
                                       target_attribute='target')

            if suspect != user:
                success -= 1
            if success / n_experiments < confidence_rate:
                robust = False
                print('-------------------------------------------------------------------')
                print('-------------------------------------------------------------------')
                print(
                    'Attack with strength ' + str(attack_strength) + " is too strong. Halting after " + str(exp_idx) +
                    " iterations.")
                print('-------------------------------------------------------------------')
                print('-------------------------------------------------------------------')
                break  # attack too strong, continue with a lighter one
        if robust:
            if isinstance(attack, VerticalSubsetAttack):
                attack_strength = round(attack_strength / attack_vertical_max, 2)
            return round(attack_strength, 2)
    if isinstance(attack, VerticalSubsetAttack):
        attack_strength = round(attack_strength / attack_vertical_max, 2)
    # todo: mirror the performance for >0.5 flipping attacks
    return round(attack_strength, 2)


def get_basic_utility(original_data, fingerprinted_data):
    '''
    Gets the simple statistics for the fingerprinted dataset
    :param original_data: pandas DataFrame object
    :param fingerprinted_data: pandas DataFrame object
    :return: dictionaries of %change, mean and variance per attribute
    '''
    modification_percentage = {}
    for index in range(len(original_data.columns)):
        original = original_data[original_data.columns[index]]
        fingerprinted = fingerprinted_data[original_data.columns[index]]
        num_of_changes = len(original.compare(fingerprinted))
        modification_percentage[original_data.columns[index]] = (num_of_changes / len(original_data)) * 100

    mean_original = [np.mean(original_data[attribute]) for attribute in original_data]
    mean_fingerprint = [np.mean(fingerprinted_data[attribute]) for attribute in fingerprinted_data]
    delta_mean = {attribute: fp - org for attribute, fp, org in zip(original_data, mean_fingerprint, mean_original)}

    var_original = [np.var(original_data[attribute]) for attribute in original_data]
    var_fingerprint = [np.var(fingerprinted_data[attribute]) for attribute in fingerprinted_data]
    delta_var = {attribute: fp - org for attribute, fp, org in zip(original_data, var_fingerprint, var_original)}

    return modification_percentage, delta_mean, delta_var


# runs deterministic experiments on data utility via KNN
def attack_utility(model, data, target, attack, attack_granularity=0.1, n_folds=10):
    X = data.drop(target, axis=1)
    y = data[target]

    attack_strength = 0
    utility = dict()
    while True:
        attack_strength += attack_granularity  # lower the strength of the attack
        if round(attack_strength, 2) >= 1.0:
            break
        # score = cross_val_score(model, X, y, cv=5)
        accuracy = []
        for fold in range(n_folds):
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=fold, shuffle=True)
            train = pd.concat([X_train, y_train], axis=1)
            attacked_train = attack.run(train, attack_strength, random_state=fold)
            attacked_X = attacked_train.drop(target, axis=1)
            attacked_y = attacked_train[target]

            model.fit(attacked_X, attacked_y)
            acc = accuracy_score(y_test, model.predict(X_test))
            accuracy.append(acc)
        utility[round(1-attack_strength, 2)] = accuracy
    return utility
    # returns estimated utility drop for each attack strength


# runs deterministic experiments on data utility via KNN
def attack_utility_knn(data, target, attack, attack_granularity=0.1, n_folds=10):
    X = data.drop(target, axis=1)
    y = data[target]

    attack_strength = 0
    utility = dict()
    while True:
        attack_strength += attack_granularity  # lower the strength of the attack
        if round(attack_strength, 2) >= 1.0:
            break
        # score = cross_val_score(model, X, y, cv=5)
        accuracy = []
        for fold in range(n_folds):
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=fold, shuffle=True)
            train = pd.concat([X_train, y_train], axis=1)
            attacked_train = attack.run(train, attack_strength, random_state=fold)
            attacked_X = attacked_train.drop(target, axis=1)
            attacked_y = attacked_train[target]

            model = KNeighborsClassifier()
            model.fit(attacked_X, attacked_y)
            acc = accuracy_score(y_test, model.predict(X_test))
            accuracy.append(acc)
        utility[round(1-attack_strength, 2)] = accuracy
    return utility
    # returns estimated utility drop for each attack strength

# runs deterministic experiments on data utility via gb
def attack_utility_gb(data, target, attack, exclude=None, attack_granularity=0.1, n_folds=10):
    X = data.drop(target, axis=1)
    # X = X.drop('Id', axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    attack_strength = 0
    utility = dict()
    while True:
        attack_strength += attack_granularity  # lower the strength of the attack
        if round(attack_strength, 2) >= 1.0:
            break
        # score = cross_val_score(model, X, y, cv=5)
        accuracy = []
        for fold in range(n_folds):
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=fold, shuffle=True)
            train = pd.concat([X_train, y_train], axis=1)
            attacked_train = attack.run(train, attack_strength, random_state=fold)
            attacked_X = attacked_train.drop(target, axis=1)
            attacked_y = attacked_train[target]

            model = GradientBoostingClassifier()
            model.fit(attacked_X, attacked_y)
            acc = accuracy_score(y_test, model.predict(X_test))
            accuracy.append(acc)
        utility[round(1-attack_strength, 2)] = accuracy
    return utility
    # returns estimated utility drop for each attack strength


def attack_utility_rf(data, target, attack, exclude=None, attack_granularity=0.1, n_folds=10):
    X = data.drop(target, axis=1)
    # X = X.drop('Id', axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    attack_strength = 0
    utility = dict()
    while True:
        attack_strength += attack_granularity  # lower the strength of the attack
        if round(attack_strength, 2) >= 1.0:
            break
        # score = cross_val_score(model, X, y, cv=5)
        accuracy = []
        for fold in range(n_folds):
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=fold, shuffle=True)
            train = pd.concat([X_train, y_train], axis=1)
            attacked_train = attack.run(train, attack_strength, random_state=fold)
            attacked_X = attacked_train.drop(target, axis=1)
            attacked_y = attacked_train[target]

            model = RandomForestClassifier(random_state=100)
            model.fit(attacked_X, attacked_y)
            acc = accuracy_score(y_test, model.predict(X_test))
            accuracy.append(acc)
        utility[round(1-attack_strength, 2)] = accuracy
    return utility


# runs deterministic experiments on data utility via gb
def vertical_attack_utility_gb(data, target, attack, gamma, exp, exclude=None, attack_granularity=0.1, n_folds=10,
                               fingerprinted_data_subdir=None):
    # this function estimates the utility based on gb classifier on attacked datasets
    # it outputs the difference in the performance compared to fingerprinted (non attacked) dataset

    # load original dataset (for model evaluation)
    if isinstance(data, Dataset):
        data_string = data.to_string()
        data = data.preprocessed()
    X = data.drop(target, axis=1)
    X = X.drop('Id', axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    # import the baseline fingerprinted data -- for now only one dataset
    # define number of experiments, i.e. number of different fingerprinted datasets -- done: exp parameter
    if fingerprinted_data_subdir is None:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/'.format(data_string)
    else:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/{}/'.format(data_string,
                                                                                         fingerprinted_data_subdir)
    fp_file_string = 'universal_g{}_x1_l8_u1_sk{}.csv'.format(gamma, exp)
    fingerprinted_data = pd.read_csv(fingerprinted_data_dir + fp_file_string)
    fingerprinted_data = GermanCredit().preprocessed(fingerprinted_data)
    X_fp = fingerprinted_data.drop(target, axis=1)
    X_fp = X_fp.drop('Id', axis=1)
    y_fp = fingerprinted_data[target]
    model = GradientBoostingClassifier(random_state=0)
    baseline_acc = fp_cross_val_score(model, X, y, X_fp, y_fp, cv=n_folds, scoring='accuracy')['test_score']
    # this is something that is already in the results

    attack_strength = 0
    utility = dict()
    while True:
        attack_strength += attack_granularity  # lower the strength of the attack
        if round(attack_strength, 2) >= 1.0:
            break
        # score = cross_val_score(model, X, y, cv=5)
        accuracy = []
        for fold in range(n_folds):
            X_train, X_test, y_train, y_test = train_test_split(X_fp, y_fp, test_size=0.2, random_state=fold, shuffle=True)
            train = pd.concat([X_train, y_train], axis=1)
            attacked_train = attack.run(train, attack_strength, random_state=fold)
            attacked_X = attacked_train.drop(target, axis=1)
            attacked_y = attacked_train[target]

            model = GradientBoostingClassifier()
            model.fit(attacked_X, attacked_y)
            acc = accuracy_score(y_test, model.predict(X_test))
            accuracy.append(acc)
        utility[round(1-attack_strength, 2)] = accuracy
    return utility
    # returns estimated utility drop for each attack strength


#def fingerprint_utility_knn(data, target, gamma, n_folds=10, n_experiments=10, data_string=None):
#    # n_folds should be consistent with experiments done on attacked data
#    if isinstance(data, Dataset):
#        data_string = data.to_string()
#        data = data.preprocessed()
#    X = data.drop(target, axis=1)
#    y = data[target]
#    model = KNeighborsClassifier()

#    fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/'.format(data_string)

#    accuracy = []
#    for exp in range(n_experiments):
#        fp_file_string = 'universal_g{}_x1_l32_u1_sk{}.csv'.format(gamma, exp)
#        fingerprinted_data = pd.read_csv(fingerprinted_data_dir+fp_file_string)
#        fingerprinted_data = Adult().preprocessed(fingerprinted_data)
#        X_fp = fingerprinted_data.drop(target, axis=1)
#        y_fp = fingerprinted_data[target]

 #       acc = fp_cross_val_score(model, X, y, X_fp, y_fp, cv=n_folds, scoring='accuracy')['test_score']
 #       accuracy.append(acc)

    # [[acc_fold1,acc_fold2,...],[],...n_experiments]
 #   return accuracy


def original_utility_knn(data, target, exclude=None, n_folds=10):
    # n_folds should be consistent with experiments done on attacked data
    # data is pandas frame
    X = data.drop(target, axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    accuracy = []
    for fold in range(n_folds):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=fold, shuffle=True)

        model = KNeighborsClassifier()
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        accuracy.append(acc)
    return accuracy


def original_utility_dt(data, target, exclude=None, n_folds=10):
    # n_folds should be consistent with experiments done on attacked data
    X = data.drop(target, axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    accuracy = []
    for fold in range(n_folds):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=fold, shuffle=True)

        model = DecisionTreeClassifier(random_state=0)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        accuracy.append(acc)
    return accuracy


def original_utility_gb(data, target, exclude=None, n_folds=10):
    # n_folds should be consistent with experiments done on attacked data
    X = data.drop(target, axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    accuracy = []
    for fold in range(n_folds):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=fold, shuffle=True)

        model = GradientBoostingClassifier(random_state=0)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        accuracy.append(acc)
    return accuracy


def original_utility_lr(data, target, exclude=None, n_folds=10):
    X = data.drop(target, axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    accuracy = []
    for fold in range(n_folds):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=fold, shuffle=True)

        model = LogisticRegression(random_state=0)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        accuracy.append(acc)
    return accuracy


# outdated
def fingerprint_utility_dt(data, target, gamma, n_folds=10, n_experiments=10, data_string=None):
    # n_folds should be consistent with experiments done on attacked data
    print('Warning: deprecated')

    if isinstance(data, Dataset):
        data_string = data.to_string()
        data = data.preprocessed()
    X = data.drop(target, axis=1)
    y = data[target]

    fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/'.format(data_string)

    accuracy = []
    for exp in range(n_experiments):
        fp_file_string = 'universal_g{}_x1_l32_u1_sk{}.csv'.format(gamma, exp)
        fingerprinted_data = pd.read_csv(fingerprinted_data_dir+fp_file_string)
        fingerprinted_data = Adult().preprocessed(fingerprinted_data)
        X_fp = fingerprinted_data.drop(target, axis=1)
        y_fp = fingerprinted_data[target]

        model = DecisionTreeClassifier(random_state=0)
        acc = fp_cross_val_score(model, X, y, X_fp, y_fp, cv=n_folds, scoring='accuracy')['test_score']
        accuracy.append(acc)

    # [[acc_fold1,acc_fold2,...],[],...n_experiments]
    return accuracy


def fingerprint_utility_gb(data, target, gamma, exclude=None, n_folds=10, n_experiments=10, data_string=None,
                           baseline_utility=False, fingerprinted_data_subdir=None):
    # n_folds should be consistent with experiments done on attacked data
    # data - original data
    print('Warning: deprecated')


    if isinstance(data, Dataset):
        data_string = data.to_string()
        data = data.preprocessed()
    X = data
    if target in data.columns:
        X = data.drop(target, axis=1)
    if 'Id' in data.columns:
        X = X.drop('Id', axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    if fingerprinted_data_subdir is None:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/'.format(data_string)
    else:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/{}/'.format(data_string,
                                                                                        fingerprinted_data_subdir)

    accuracy = []
    for exp in range(n_experiments):
        fp_file_string = 'universal_g{}_x1_l8_u1_sk{}.csv'.format(gamma, exp)
        fingerprinted_data = pd.read_csv(fingerprinted_data_dir + fp_file_string)
        fingerprinted_data = GermanCredit().preprocessed(fingerprinted_data)
        X_fp = fingerprinted_data.drop(target, axis=1)
        if 'Id' in X_fp.columns:
            X_fp = X_fp.drop('Id', axis=1)
        y_fp = fingerprinted_data[target]
        if baseline_utility:
            X_fp = X
            y_fp = y
        model = GradientBoostingClassifier(random_state=0)
        acc = fp_cross_val_score(model, X, y, X_fp, y_fp, cv=n_folds, scoring='accuracy')['test_score']
        accuracy.append(acc)
        if baseline_utility:
            break

    # [[acc_fold1,acc_fold2,...],[],...n_experiments]
    return accuracy


def fingerprint_utility_lr(data, target, gamma, exclude=None, n_folds=10, n_experiments=10, data_string=None,
                           baseline_utility=False, fingerprinted_data_subdir=None):
    # n_folds should be consistent with experiments done on attacked data
    print('Warning: deprecated')

    # data - original data

    if isinstance(data, Dataset):
        data_string = data.to_string()
        data = data.preprocessed()
    X = data
    if target in data.columns:
        X = data.drop(target, axis=1)
    if 'Id' in data.columns:
        X = X.drop('Id', axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    if fingerprinted_data_subdir is None:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/'.format(data_string)
    else:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/{}/'.format(data_string,
                                                                                        fingerprinted_data_subdir)

    accuracy = []
    for exp in range(n_experiments):
        fp_file_string = 'universal_g{}_x1_l8_u1_sk{}.csv'.format(gamma, exp)
        fingerprinted_data = pd.read_csv(fingerprinted_data_dir + fp_file_string)
        fingerprinted_data = GermanCredit().preprocessed(fingerprinted_data)
        X_fp = fingerprinted_data.drop(target, axis=1)
        if 'Id' in X_fp.columns:
            X_fp = X_fp.drop('Id', axis=1)
        y_fp = fingerprinted_data[target]
        if baseline_utility:
            X_fp = X
            y_fp = y
        model = LogisticRegression(random_state=0)
        acc = fp_cross_val_score(model, X, y, X_fp, y_fp, cv=n_folds, scoring='accuracy')['test_score']
        accuracy.append(acc)
        if baseline_utility:
            break

    # [[acc_fold1,acc_fold2,...],[],...n_experiments]
    return accuracy


def fingerprint_utility_knn(data, target, gamma, exclude=None, n_folds=10, n_experiments=10, data_string=None,
                           baseline_utility=False, fingerprinted_data_subdir=None):
    print('Warning: deprecated')
    # n_folds should be consistent with experiments done on attacked data
    # data - original data

    if isinstance(data, Dataset):
        data_string = data.to_string()
        data = data.preprocessed()
    X = data
    if target in data.columns:
        X = data.drop(target, axis=1)
    if 'Id' in data.columns:
        X = X.drop('Id', axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = data[target]

    if fingerprinted_data_subdir is None:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/'.format(data_string)
    else:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/{}/'.format(data_string,
                                                                                        fingerprinted_data_subdir)

    accuracy = []
    for exp in range(n_experiments):
        fp_file_string = 'universal_g{}_x1_l8_u1_sk{}.csv'.format(gamma, exp)
        fingerprinted_data = pd.read_csv(fingerprinted_data_dir + fp_file_string)
        fingerprinted_data = GermanCredit().preprocessed(fingerprinted_data)
        X_fp = fingerprinted_data.drop(target, axis=1)
        if 'Id' in X_fp.columns:
            X_fp = X_fp.drop('Id', axis=1)
        y_fp = fingerprinted_data[target]
        if baseline_utility:
            X_fp = X
            y_fp = y
        model = KNeighborsClassifier()
        acc = fp_cross_val_score(model, X, y, X_fp, y_fp, cv=n_folds, scoring='accuracy')['test_score']
        accuracy.append(acc)
        if baseline_utility:
            break

    # [[acc_fold1,acc_fold2,...],[],...n_experiments]
    return accuracy


def fingerprint_utility(model_name, data, target, gamma, fp_len=8, exclude=None, n_folds=10, n_experiments=10,
                        data_string=None, baseline_utility=False, fingerprinted_data_subdir=None, progress_bar=True):
    if model_name == 'knn':
        model = KNeighborsClassifier()
    elif model_name == 'lr':
        model = LogisticRegression(random_state=0)
    elif model_name == 'rf':
        model = RandomForestClassifier(random_state=0)
    elif model_name == 'gb':
        model = GradientBoostingClassifier(random_state=0)
    elif model_name == 'mlp':
        model = MLPClassifier(random_state=0, max_iter=150, n_iter_no_change=6)
    elif model_name == 'svm':
        model = SVC(random_state=0)
    else:
        model = None
        print('Invalid model name!')
        exit()

    if isinstance(data, Dataset):
        data_string = data.to_string()
        dataframe = data.preprocessed()
    X = dataframe

    if target in dataframe.columns:
        X = dataframe.drop(target, axis=1)
    if 'Id' in dataframe.columns:
        X = X.drop('Id', axis=1)
    if exclude is not None:
        X = X.drop(exclude, axis=1)
    y = dataframe[target]

    if fingerprinted_data_subdir is None:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/'.format(data_string)
    else:
        fingerprinted_data_dir = 'parameter_guidelines/fingerprinted_data/{}/{}/'.format(data_string,
                                                                                        fingerprinted_data_subdir)

    accuracy = []
    if progress_bar:
        print('|'+' '*(n_experiments-2)+'|')
    for exp in range(n_experiments):
        if progress_bar:
            sys.stdout.write('|')
        if baseline_utility:
            X_fp = X
            y_fp = y
        else:
            fp_file_string = 'universal_g{}_x1_l{}_u1_sk{}.csv'.format(gamma, fp_len, exp)
            fingerprinted_data = pd.read_csv(fingerprinted_data_dir + fp_file_string)
            fingerprinted_data = data.preprocessed(fingerprinted_data)
            X_fp = fingerprinted_data.drop(target, axis=1)
            if 'Id' in X_fp.columns:
                X_fp = X_fp.drop('Id', axis=1)
            y_fp = fingerprinted_data[target]

        acc = fp_cross_val_score(model, X, y, X_fp, y_fp, cv=n_folds, scoring='accuracy')['test_score']
        accuracy.append(acc)
        if baseline_utility:
            break
    if progress_bar:
        print()
    # [[acc_fold1,acc_fold2,...],[],...n_experiments]
    return accuracy


def attack_utility_bounds(original_utility, attack_utility):
    # returns the attack strengths that yield at least 1%, 2%, ... utility loss and
    # the largest accuracy drop of attacked data
    # the returned values are absolute
    attack_bounds = []
    max_utility_drop = np.mean(original_utility) - \
                       min(np.mean(acc) for acc in attack_utility.values())
    drop = 0.01
    while drop < max_utility_drop:
        # attack strength that yields at least 1%(or p%) of accuracy loss

        attack_strength = max([strength for strength in attack_utility
                          if np.mean(original_utility) - np.mean(attack_utility[strength])
                               <= drop])
        attack_bounds.append(attack_strength)
        drop += 0.01
    attack_bounds.append(max_utility_drop)
    return attack_bounds


#def _split_features_target(original_data, fingerprinted_data):
#    X = data.drop([target, 'sample-code-number'], axis=1)
#    y = data[target]


#def get_ML_utility():
#    # todo: also baseline models (original) should be done only once
#    X, y, X_fp, y_fp = _split_features_target(original_data, fingerprinted_data)
#    _utility_KNN()


def master_evaluation(dataset,
                      target_attribute=None, primary_key_attribute=None):
    '''
    This method outputs the full robustness and utility evaluation to user 'at glance', given the data set.
    This includes: (1) utility approximation trends and (2) expected robustness trends
    The outputs should help the user with parameter choices for their data set.

    (1) Utility evaluation shows (i) the average change in mean and variance for each attribute and (ii) average
    performance of the fingerprinted data sets using a variety of classifiers, e.g. Decision Tree,
    Logistic Regression, Gradient Boosting...
    :param dataset: path to the dataset, pandas DataFrame or class Dataset
    :param target_attribute: name of the target attribute for the dataset. Ignored if dataset is of type Dataset
    :param primary_key_attribute: name of the primary key attribute of the dataset. Ignored if dataset is of type Dataset
    :return: metadata of the experimental run
    '''
    meta = ''
    if isinstance(dataset, str):  # assumed the path is given
        data = Dataset(path=dataset, target_attribute=target_attribute, primary_key_attribute=primary_key_attribute)
    elif isinstance(dataset, pd.DataFrame):  # assumed the pd.DataFrame is given
        data = Dataset(dataframe=dataset, target_attribute=target_attribute, primary_key_attribute=primary_key_attribute)
    elif isinstance(dataset, Dataset):
        data = dataset
    else:
        print('Wrong type of input data.')
        exit()

    # EXPERIMENT RUN
    # 1) fingerprint the data (i.e. distinct secret key & distinct gamma)
    # 2) record the changes in mean and variance for each attribute
    # 3) perform the classification analysis
    # 4) robustness per se (extraction rate)
    # 5) robustness against the attacks (experimental) -> here it would make sense to compare the theoretical results

    _start_exp_run = time.time()

    # todo: for now only integer data fingerprinting is supported via AK scheme. Next up: categorical & decimal
    gamma = 2
    secret_key = 123
    scheme = AKScheme(gamma=gamma, fingerprint_bit_length=16)

    fingerprinted_data = scheme.insertion(dataset=data, secret_key=secret_key, recipient_id=0)

    changed_vals, mean, var = get_basic_utility(data.get_dataframe(), fingerprinted_data.get_dataframe())

#    get_ML_utility()

    return meta


def test_interactive_plot():
    fig, ax = plt.subplots(figsize=(14, 8))

    y = np.random.randint(0, 100, size=50)
    x = np.random.choice(np.arange(len(y)), size=10)

    line, = ax.plot(y, '-', label='line')
    dot, = ax.plot(x, y[x], 'o', label='dot')

    legend = plt.legend(loc='upper right')
    line_legend, dot_legend = legend.get_lines()
    line_legend.set_picker(True)
    line_legend.set_pickradius(10)
    dot_legend.set_picker(True)
    dot_legend.set_pickradius(10)

    graphs = {}
    graphs[line_legend] = line
    graphs[dot_legend] = dot

    def on_pick(event):
        legend = event.artist
        isVisible = legend.get_visible()

        graphs[legend].set_visible(not isVisible)
        legend.set_visible(not isVisible)

        fig.canvas.draw()

    plt.connect('pick_event', on_pick)
    plt.show()


def merge_server_results(data_name, model_name, n_experiments, fpattr):
    with open('parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'rb') as infile:
        utilities = pickle.load(infile)
    print(utilities.keys())
    with open('parameter_guidelines/evaluation/{}/from_server/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'rb') as infile:
        utilities_server = pickle.load(infile)
    print(utilities_server.keys())
    for g in utilities_server:
        utilities[g] = utilities_server[g]
    utilities_ordered = dict(collections.OrderedDict(sorted(utilities.items())))
    with open('parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'wb') as outfile:
        pickle.dump(utilities_ordered, outfile)
    print()
    print(utilities_ordered.keys())


def show_current_results(data_name, model_name, n_experiments, fpattr):
    if os.path.isfile(
            'parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(
                data_name, model_name, fpattr, n_experiments)):
        with open('parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'rb') as infile:
            utilities = pickle.load(infile)
        print('local')
        print(utilities.keys())
    if os.path.isfile(
            'parameter_guidelines/evaluation/{}/from_server/utility_fp_{}_fpattr{}_e{}.pickle'.format(
                data_name, model_name, fpattr, n_experiments)):
        with open('parameter_guidelines/evaluation/{}/from_server/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'rb') as infile:
            utilities_server = pickle.load(infile)
        print('server (as transferred to local -- might differ from actual server)')
        print(utilities_server.keys())
    exit()


def baseline(model_name, data, n_folds=5):
    baseline_accuracies = fingerprint_utility(model_name=model_name, data=data, target=data.get_target_attribute(),
                                              gamma=1, n_folds=n_folds, baseline_utility=True)
    if os.path.isfile(
            'parameter_guidelines/evaluation/{}/utility_ml_baseline.pickle'.format(data.to_string())):
        with open('parameter_guidelines/evaluation/{}/utility_ml_baseline.pickle'.format(data.to_string()), 'rb') as infile:
            baseline = pickle.load(infile)
    else:
        baseline = dict()
    baseline[model_name] = baseline_accuracies
    with open('parameter_guidelines/evaluation/{}/utility_ml_baseline.pickle'.format(data.to_string()), 'wb') as outfile:
        pickle.dump(baseline, outfile)
    pprint(baseline)
    exit()


def order_results(data_name, model_name, n_experiments, fpattr):
    if os.path.isfile(
            'parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(
                data_name, model_name, fpattr, n_experiments)):
        with open('parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'rb') as infile:
            utilities = pickle.load(infile)
        utilities_ordered = dict(collections.OrderedDict(sorted(utilities.items())))
        with open('parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'wb') as outfile:
            pickle.dump(utilities_ordered, outfile)
        print('local')
        print(utilities_ordered.keys())

    if os.path.isfile(
            'parameter_guidelines/evaluation/{}/from_server/utility_fp_{}_fpattr{}_e{}.pickle'.format(
                data_name, model_name,fpattr,  n_experiments)):
        with open('parameter_guidelines/evaluation/{}/from_server/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'rb') as infile:
            utilities_server = pickle.load(infile)
        utilities_server_ordered = dict(collections.OrderedDict(sorted(utilities_server.items())))
        with open('parameter_guidelines/evaluation/{}/from_server/utility_fp_{}_fpattr{}_e{}.pickle'.format(data_name, model_name, fpattr, n_experiments), 'wb') as outfile:
            pickle.dump(utilities_server_ordered, outfile)
        print('server')
        print(utilities_server_ordered.keys())
    exit()


if __name__ == '__main__':
    #order_results('diabetic_data', 'lr', n_experiments=20, fpattr=45)
    show_current_results('diabetic_data', 'svm', n_experiments=20, fpattr=45)
    merge_server_results('adult', 'svm', n_experiments=30, fpattr=12); exit()
    gammae = [1, 2, 3, 4, 5, 10, 18]  # 7, 8, 9, 10, 12, 15, 18]
    #gammae = [1.11, 1.25, 1.43, 1.67, 2.5]
    # utilities_knn = dict()
    attr_subset = 45
    model_name = 'svm'; print(model_name)
    data = DiabeticData()
    n_experiments = 20
    fp_len = 32
    # test_interactive_plot()
    # GRADIENT BOOSTING IS THE BEST FOR GERMAN CREDIT

    # BASELINE FOR COMPARABLE RESULTS
    baseline(model_name, data, n_folds=5)

    if os.path.isfile(
            'parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(
                data.to_string(), model_name, attr_subset, n_experiments)):
        with open('parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(
                data.to_string(), model_name, attr_subset, n_experiments),
                  'rb') as infile:
            utilities = pickle.load(infile)

    else:
        # utilities_gb = dict()
        utilities = dict()
    pprint(utilities)
    for g in gammae:
        print('({}) gamma = {}'.format(model_name, g))
        if g not in utilities:
            utilities[g] = fingerprint_utility(model_name=model_name, data=data, target=data.get_target_attribute(),
                                               gamma=g, n_folds=3, n_experiments=n_experiments, fp_len=fp_len,
                                               fingerprinted_data_subdir='attr_subset_{}'.format(attr_subset),
                                               progress_bar=True)   # disable progress bar for server
            print(utilities[g])
        # saves with every iteration so that it doesn't get interrupted by the errors
        # for parallel processes: update the utilities with up-to-date results
        if os.path.isfile(
                'parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(
                    data.to_string(), model_name, attr_subset, n_experiments)):
            with open('parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(
                    data.to_string(), model_name, attr_subset, n_experiments),
                      'rb') as infile:
                temp_utilities = pickle.load(infile)
            for g in temp_utilities:
                if g not in utilities:
                    utilities[g] = temp_utilities[g]

        with open('parameter_guidelines/evaluation/{}/utility_fp_{}_fpattr{}_e{}.pickle'.format(data.to_string(), model_name, attr_subset, n_experiments), 'wb') as outfile:
                    pickle.dump(utilities, outfile)

    # SORT THE DICTIONARY
    # UPDATES THE EXISTING RESULTS
