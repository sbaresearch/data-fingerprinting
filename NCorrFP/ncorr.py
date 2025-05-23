import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import random
from collections import Counter
import matplotlib.pyplot as plt
from numpy import ndarray
from scipy.stats import gaussian_kde
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import BallTree
from bitstring import BitArray
import hashlib
import bitstring
import copy

from fp_codes import tardos
from utils import *
from fp_codes.tardos import *
import datasets

_MAXINT = 2**31 - 1


def init_balltrees(correlated_attributes, relation, dist_metric_discrete="hamming", dist_metric_continuous="minkowski",
                   categorical_attributes=None, show_messages=True):
    """
    Initialises balltrees for neighbourhood search.
    Balltrees for correlated attributes are created from the attribute's correlated attributes.
    Balltrees for other attributes are created from all other attributes.
    A known limitation is that at the moment there is no good way to resolve distances between mixed types.
    Args:
        dist_metric_discrete (str): distance metric for discrete attributes
        dist_metric_continuous (str): distance metric for continuous attributes
        categorical_attributes (list): a list of categorical attributes
        correlated_attributes: (strictly) a list of lists (groups) of correlated attributes
        relation: the DataFrame of the dataset

    Returns: a dictionary (attribute name: balltree)

    """
    start_training_balltrees = time.time()
    # ball trees from all-except-one attribute and all attributes
    balltree = dict()

    for attr in relation.columns:
        # get the index of a list of correlated attributes to attr; if attr is not correlated then return None
        index = next((i for i, sublist in enumerate(correlated_attributes) if attr in sublist), None)
        if index is not None:  # if attr is part of any group of correlations
            # use a metric that fits with the data type
            subdata = relation[correlated_attributes[index]].drop(attr, axis=1)
        else:  # if attr is not correlated to anything
            subdata = relation.drop(attr, axis=1)

        #subdata.to_numpy()
        # Balltree does not support callable functions
        # balltree[attr] = BallTree(subdata, metric=lambda x, y: hybrid_distance(x, y, categorical_idx, continuous_idx, dist_metric_discrete, dist_metric_continuous))
        balltree[attr] = BallTree(subdata, metric=dist_metric_discrete if attr in categorical_attributes else dist_metric_continuous)

    if show_messages:
        print("Training balltrees in: " + str(round(time.time() - start_training_balltrees, 4)) + " sec.")
    return balltree


def merge_mutually_correlated_groups(megalist):
    # Iteratively merge lists that have any common elements
    merged = []

    for sublist in megalist:
        # Find all existing lists in merged that share elements with the current sublist
        to_merge = [m for m in merged if any(elem in m for elem in sublist)]

        # Remove the lists that will be merged from merged
        for m in to_merge:
            merged.remove(m)

        # Merge the current sublist with the found lists and add back to merged
        merged.append(set(sublist).union(*to_merge))

    # Convert sets back to lists
    return [list(group) for group in merged]


def parse_correlated_attrs(correlated_attributes, relation):
    """
    Checks the validity of passed arguments for correlated attributes. They can be either a list, list of lists or None.
    Args:
        correlated_attributes: argument provided by the user
        relation: pandas DataFrame dataset

    Returns: list of groups (lists) of correlated attributes

    """
    # correlated attributes are treated always as a list of lists even if there is only one group of corr. attributes
    if correlated_attributes is None:
        if 'Id' in relation.columns:
            relation = relation.drop('Id', axis=1)
        correlated_attributes = [relation.columns[:]]  # everything is correlated if not otherwise specified
        # Check if the input is a list of lists
    elif isinstance(correlated_attributes, list) and all(isinstance(i, list) for i in correlated_attributes):
        # It's a list of lists; multiple groups of correlated attributes
        # If there are multiple correlation groups with the same attribute, we consider them all mutually correlated
        correlated_attributes = merge_mutually_correlated_groups(correlated_attributes)
        correlated_attributes = [pd.Index(corr_group) for corr_group in correlated_attributes]
    elif isinstance(correlated_attributes, list):
        # It's a single list
        correlated_attributes = [pd.Index(correlated_attributes)]
    else:
        raise ValueError("Input correlated_attributes must be either a list or a list of lists")
    return correlated_attributes


def sample_from_area(data, percent=0.1, num_samples=1, dense=True, plot=False, seed=0):
    """
    Samples from the most dense areas of distribution, excluding a specified percentile.
    The distribution is estimated using Gaussian Kernel Density Estimation method
    Args:
        data: data points
        percent: bottom percentile to exclude from dense sampling, or include in low-density sampling
        num_samples: number of sampled values
        dense: whether to sample from most dense areas, or low density areas (distribution tails)
        plot: True/False; whether to plot the density distributions

    Returns: a list of sampled values

    """
    # Create a KDE based on the data (PDF estimation)
    try:
        kde = gaussian_kde(data)
    except np.linalg.LinAlgError as e:  # when the data points are too similar to each other (or exactly the same)
        return data[0]

    # Create a range of values to evaluate the PDF
    n_points = len(data) * 10  # dynamic num of points adds on runtime but does not improve estimations
    x = np.linspace(min(data), max(data), 100)  # n_points)  # 1000)
    pdf_values = kde(x)

    # Identify the threshold to exclude a percentage of the densest areas
    threshold = np.percentile(pdf_values, percent*100)

    # Mask the CDF to only include values within the percentile range
    if dense or (max(data) == min(data)):
        # design decision: sampling from uniform distribution is always the same
        # the alternative that potentially leads to less errors: sample a value outside the distribution
        mask = (pdf_values >= threshold)
    else:
        mask = (pdf_values < threshold)

    # Re-normalize the masked PDF and CDF
#    with warnings.catch_warnings(record=True) as w:
    masked_pdf = np.where(mask, pdf_values, 0)
    masked_cdf = np.cumsum(masked_pdf)
    masked_cdf /= masked_cdf[-1]
#        if len(w) > 0:
#            exit(data)

    # Inverse transform sampling from the adjusted CDF
    generator = np.random.default_rng(seed)
    random_values = generator.random(num_samples)
    sampled_values = np.interp(random_values, masked_cdf, x)

    # Plot the PDF, masked PDF, and the sampled values
    if plot:
        plt.plot(x, pdf_values, label='Original PDF (estimate)')
        plt.plot(x, masked_pdf, label='Modified PDF ({}th percentile)'.format(int(100*percent)))
        plt.scatter(sampled_values, [0] * num_samples, color='red', label='Sampled Values', zorder=5)
        plt.hist(data, bins=10, density=True, alpha=0.3, label='Neighbourhood data points')
        if dense:
            plt.title('Sampling from high density areas (mark bit = 1)')
        else:
            plt.title('Sampling from low density areas (mark bit = 0)')
        plt.xlabel('Values')
        plt.ylabel('Density')
        plt.legend()
        plt.show()

    return sampled_values


def is_from_dense_area(sample, data, percent):
    # Create a KDE based on the data (PDF estimation)
    # print(data)
    try:
        kde = gaussian_kde(data)
    except np.linalg.LinAlgError as e:  # a strictly uniform distribution of data
        return True

    # Create a range of values to evaluate the PDF
    x = np.linspace(min(data), max(data), 100)  # 1000)
    pdf_values = kde(x)

    # Identify the threshold to exclude a percentage of the densest areas
    threshold = np.percentile(pdf_values, percent * 100)
    mask = (pdf_values >= threshold)  # mask for the dense area
    # Dictionary so that we can query the area with the sample point
    area = dict(zip(np.round(x, 6), mask))
    # Round the key to the closest one to the sample
    k = min(area.keys(), key=lambda y: abs(y - sample))

    return area[k]


def mark_categorical_value_old(neighbours, mark_bit):
    """
    Marks a categorical value based on the frequencies in the neighbourhood and the mark bit.
    If mark bit is 1, the new value will be the most frequent one in the neighbourhood, otherwise sampling from
    remaining values is performed weighted by their frequency in the neighbourhood.
    Args:
        neighbours: a list of values
        mark_bit: 0 or 1

    Returns: categorical value

    """
    possible_values = neighbours
    frequencies = dict()
    if len(possible_values) != 0:
        for value in set(possible_values):
            f = possible_values.count(value) / len(possible_values)
            frequencies[value] = f
        # sort the values by their frequency
        frequencies = {k: v for k, v in sorted(frequencies.items(), key=lambda item: item[1], reverse=True)}
        if mark_bit == 0 and len(frequencies.keys()) > 1:
            # choose among less frequent values, weighted by their frequencies
            norm_freq = list(frequencies.values())[1:] / np.sum(list(frequencies.values())[1:])
            marked_attribute = np.random.choice(list(frequencies.keys())[1:], 1, p=norm_freq)[0]
        else:  # choose the most frequent value
            marked_attribute = list(frequencies.keys())[0]
    else:
        marked_attribute = None
    return marked_attribute


def mark_categorical_value(neighbourhood, mark_bit, percentile=0.75):
    """
    Marks a categorical value based on neighbourhood frequencies and the mark bit.

    Args:
        neighbourhood (list): List of categorical values in the neighbourhood.
        mark_bit (int): 1 to sample from the most frequent group, 0 to sample from the remaining values.
        percentile (float): Threshold for splitting into frequent and less frequent groups (0-1).

    Returns:
        str: The sampled value based on the mark bit and neighbourhood distribution.
    """
    # Calculate frequencies
    value_counts = Counter(neighbourhood)
    total_count = sum(value_counts.values())

    # If only one unique value exists, return it regardless of the mark bit
    if len(value_counts) == 1:
        return next(iter(value_counts.keys()))

    # Sort values by frequency (ascending)
    sorted_items = sorted(value_counts.items(), key=lambda x: (-x[1], x[0]), reverse=True)

    # Divide values into most and least frequent
    cumulative_sum = 0
    less_frequent = []

    for i, (value, count) in enumerate(sorted_items):
        if cumulative_sum / total_count >= percentile and i < len(sorted_items) - 1:
            break
        less_frequent.append(value)
        cumulative_sum += count

    # Handle ties
    last_count = sorted_items[len(less_frequent) - 1][1]
    for value, count in sorted_items[len(less_frequent):]:
        if count == last_count and len(less_frequent) < len(sorted_items) - 1:
            less_frequent.append(value)
        else:
            break

    # Most frequent group
    most_frequent = [value for value, _ in sorted_items if value not in less_frequent]

    # Ensure at least one value remains in each group
    if not most_frequent:
        most_frequent.append(less_frequent.pop())
    elif not less_frequent:
        less_frequent.append(most_frequent.pop())
#    print(most_frequent)
#    print(less_frequent)
    # most_frequent, less_frequent = get_frequency_groups()
    # Sample from the appropriate group based on the mark bit
    if mark_bit == 1:
        return random.choices(most_frequent, weights=[value_counts[val] for val in most_frequent])[0]
    else:
        return random.choices(less_frequent, weights=[value_counts[val] for val in less_frequent])[0]


def mark_continuous_value(neighbours, mark_bit, percentile=0.75, round_to_existing=True, plot=False, seed=0):
    """
    Marks a continuous value based on the neighbourhood of its record in the dataset and the mark bit.
    Provided the neighbourhood values, the distribution of continuous variable is estimated using Gaussian Kernel
    Density Estimation. From the obtained distribution, the new value is sampled based on the mark bit. If the mark bit
    is 1, the value is sampled from a specified percentile, otherwise below.
    Args:
        neighbours: a list of values
        mark_bit: integer 0 or 1
        percentile: percentile for sampling from distribution; float (0, 1.0)
        round_to_existing: True/False; whether to round the sampled value to the closest value from the neighbourhood
        plot: True/False; whether to plot the resulting sampling
        seed (int): seed for reproducibility
    Returns: new continuous value
    """
    sampling_from_dense = True if mark_bit == 1 else False
    sampled_value = sample_from_area(data=neighbours, percent=percentile, dense=sampling_from_dense, plot=plot,
                                        seed=seed)

    if round_to_existing:  # we are choosing the closest existing value from the sampling area todo
        closest_neighbours = sorted(list(set(neighbours)), key=lambda x: abs(x - sampled_value))
        rounded_value = closest_neighbours.pop(0)
        while is_from_dense_area(sample=rounded_value, data=neighbours, percent=percentile) != sampling_from_dense:
            if len(closest_neighbours) == 0:
                rounded_value = sorted(list(set(neighbours)), key=lambda x: abs(x - sampled_value))[0]
                break
            rounded_value = closest_neighbours.pop(0)
        sampled_value = rounded_value
    return sampled_value


def get_mark_bit_old(is_categorical, attribute_val, neighbours, relation_fp, attr_name, percentile=0.75):
    if not isinstance(relation_fp, pd.DataFrame):
        relation_fp = relation_fp.dataframe
    indices = list(relation_fp.index)
    if is_categorical:
        possible_values = []
        for neighb in neighbours:
            neighb = indices[neighb]  # balltree resets the index so querying by index only fails for horizontal attacks, so we have to keep track of indices like this
            possible_values.append(relation_fp.at[neighb, attr_name])
        frequencies = dict()
        if len(possible_values) != 0:
            for value in set(possible_values):
                f = possible_values.count(value) / len(possible_values)
                frequencies[value] = f
            # sort the values by their frequency
            frequencies = {k: v for k, v in
                           sorted(frequencies.items(), key=lambda item: item[1], reverse=True)}
        if attribute_val == list(frequencies.keys())[0]:
            mark_bit = 1
        else:
            mark_bit = 0
    else:
        # recover whether the attr_val comes from the dense area or not
        mark_bit = 1 if is_from_dense_area(sample=attribute_val, data=neighbours, percent=percentile) else 0

    return mark_bit


def is_from_most_frequent(sample, neighbourhood, percentile):
    '''
    Decides whether the sample belongs to the most frequent subset of domain values given the percentile.
    Args:
        sample: data point
        neighbourhood: domain values
        percentile: cut off between most and least frequent

    Returns: True if the sample is one of the most frequent values in the neighbourhood, otherwise false

    '''
    # Calculate frequencies
#    possible_values = []
#    indices = list(relation.index)
#    for neighb in neighbours:
#        neighb = indices[
#            neighb]  # balltree resets the index so querying by index only fails for horizontal attacks, so we have to keep track of indices like this
#        possible_values.append(relation.at[neighb, attr_name])

    value_counts = Counter(neighbourhood)
    total_count = sum(value_counts.values())

    # If only one unique value exists, return 1
    if len(value_counts) == 1:
        return True

    # Sort values by frequency (ascending)
    sorted_items = sorted(value_counts.items(), key=lambda x: (-x[1], x[0]), reverse=True)

    # Divide values into most and less frequent
    cumulative_sum = 0
    less_frequent = []

    for i, (val, count) in enumerate(sorted_items):
        if cumulative_sum / total_count >= percentile and i < len(sorted_items) - 1:
            break
        less_frequent.append(val)
        cumulative_sum += count

    # Handle ties
    last_count = sorted_items[len(less_frequent) - 1][1]
    for val, count in sorted_items[len(less_frequent):]:
        if count == last_count and len(less_frequent) < len(sorted_items) - 1:
            less_frequent.append(val)
        else:
            break

    # Most frequent group
    most_frequent = [val for val, _ in sorted_items if val not in less_frequent]

    # Ensure at least one value remains in each group
    if not most_frequent:
        most_frequent.append(less_frequent.pop())
    elif not less_frequent:
        less_frequent.append(most_frequent.pop())

    # Determine the mark bit
    if sample in most_frequent:
        return True
    else:
        return False


def get_mark_bit(is_categorical, attribute_val, neighbours, relation_fp, attr_name, percentile=0.75):
    """
    Determines whether the given value corresponds to mark bit 1 (most frequent group)
    or mark bit 0 (less frequent group).

    Args:


    Returns:
        int: 1 if the value is in the most frequent group, 0 if it is in the less frequent group.
    """
#    if not isinstance(relation_fp, pd.DataFrame):
#        relation_fp = relation_fp.dataframe

    if is_categorical:
        mark_bit = 1 if is_from_most_frequent(sample=attribute_val, neighbourhood=neighbours, percentile=percentile) else 0
    else:
        # recover whether the attr_val comes from the dense area or not
        mark_bit = 1 if is_from_dense_area(sample=attribute_val, data=neighbours, percent=percentile) else 0

    return mark_bit


def create_hash_fingerprint(secret_key, recipient_id, fingerprint_bit_length):
    """

    Args:
        secret_key: owner's secret
        recipient_id: recipient of the fingerprint
        fingerprint_bit_length: length in bits

    Returns: fingerprint

    """
    # seed is generated by concatenating secret key with recipients id
    shift = 10
    # seed is 42 bit long
    seed = (secret_key << shift) + recipient_id
    digest_size = int(fingerprint_bit_length / 8)
    b = hashlib.blake2b(key=seed.to_bytes(6, 'little'), digest_size=digest_size)
    fingerprint = BitArray(hex=b.hexdigest())
    # convert to numpy array for consistency
    fingerprint = np.array(list(fingerprint.bin), dtype=int)
    return fingerprint


def decode_hash_fingerprint(fingerprint, secret_key, total_recipients):
    """

    Args:
        fingerprint: bit sequence that represents the suspicious fingerprint
        secret_key: owner's secret

    Returns: a dictionary (recipient_id: matching confidence)

    """
    shift = 10
    fingerprint_bit_length = len(fingerprint)
    # calculate the matching score for each recipient

    # for each recipient calculate the confidence by a percentage of position-wise bit matching
    confidence = dict()
    for recipient_id in range(total_recipients):
        recipient_seed = (secret_key << shift) + recipient_id
        digest_size = int(fingerprint_bit_length / 8)
        b = hashlib.blake2b(key=recipient_seed.to_bytes(6, 'little'),
                            digest_size=digest_size)
        recipient_fp = BitArray(hex=b.hexdigest())
        recipient_fp = recipient_fp.bin
        # convert to numpy array for consistency
        recipient_fp = np.array(list(recipient_fp), dtype=int)
        confidence[recipient_id] = np.sum(recipient_fp == fingerprint) / len(fingerprint)
#        # exact matching
#        if np.array_equal(recipient_fp, fingerprint):
#            return recipient_id
    return confidence


class NCorrFP():
    # supports the dataset size of up to 1,048,576 entries
    __primary_key_len = 20

    def __init__(self, gamma=1, xi=1, fingerprint_bit_length=32, number_of_recipients=100, distance_based=False,
                 d=0, k=50, distance_metric_discrete="hamming", distance_metric_continuous='minkowski',
                 fingerprint_code_type='hash'):
        """

        Args:
            gamma: embedding ratio - probability of a single row to get marked is 1/gamma
            xi: number of modifiable LSBs if applicable
            fingerprint_bit_length: length of a fingerprint in bits
            number_of_recipients: total number of recipients
            distance_based: if True, the neighbourhoods are calculated using max distance d, otherwise using cardinality k
            d: max distance of the neighbourhood (inclusive); used if distance_based=True
            k: cardinality of the neighbourhood; used in distance_based=False
            distance_metric_discrete: name of the distance metric for discreete attributes
            distance_metric_continuous: name of the distance metric for continuous attributes (supports all standard sklearn metrics)
            fingerprint_code_type: options - hash, tardos
        """
        self.gamma = gamma
        self.xi = xi
        self.fingerprint_bit_length = fingerprint_bit_length
        self.number_of_recipients = number_of_recipients
        self.distance_based = distance_based  # if False, then fixed-size-neighbourhood-based with k=10 - default
        if distance_based:
            self.d = d
        else:
            self.k = k
        self._INIT_MESSAGE = "NCorrFP - initialised.\n\t(Correlation-preserving NN-based fingerprinting scheme.)\n" \
                             "Embedding started...\n" \
                             "\tgamma: " + str(self.gamma) + "\n\tfingerprint length: " + \
                             str(self.fingerprint_bit_length) + "\n\tdistance based: " + str(self.distance_based)
        self.dist_metric_discrete = distance_metric_discrete
        self.dist_metric_continuous = distance_metric_continuous
        self.fingerprint_code_type = fingerprint_code_type
        self.count = None  # the most recent fingerprint bit-wise counts
        self.detected_fp = None  # the most recently detected fingerprint
        self.insertion_iter_log = []  # tracks the most recent insertion
        self.detection_iter_log = []  # tracts the most recent detection

    def create_fingerprint(self, recipient_id, secret_key, show_messages=True):
        """
        Creates a fingerprint for a recipient with the given ID
        :param recipient_id: identifier of a data copy recipient
        :param secret_key: owner's secret key used to fingerprint the data
        :param show_messages: whether to print out the messages related to execution
        :return: fingerprint (BitArray)

        """
        __valid_types = ['hash', 'tardos']
        if recipient_id < 0 or recipient_id >= self.number_of_recipients:
            print("Please specify valid recipient id. (note: this version assumes a sequential IDs, hence valid IDs "
                  "are int between 0 and {}.)".format(self.number_of_recipients-1))
            exit()

        if self.fingerprint_code_type == 'hash':
            fingerprint = create_hash_fingerprint(secret_key=secret_key,
                                    fingerprint_bit_length=self.fingerprint_bit_length,
                                    recipient_id=recipient_id)
        elif self.fingerprint_code_type == 'tardos':
            fingerprint = tardos.generate(secret_key=secret_key,
                                                    recipient_id=recipient_id,
                                                    fp_len=self.fingerprint_bit_length)
        else:
            fingerprint = None
            exit('Please specify valid type of fingerprint code ({})'.format(__valid_types))
        if show_messages:
            fp_msg = "\nGenerated a {} fingerprint for recipient {}: {}".format(self.fingerprint_code_type,
                                                                                recipient_id,
                                                                                list_to_string(fingerprint))
            print(fp_msg)
        return fingerprint

    def exact_matching_scores(self, fingerprint, secret_key):
        """
        Returns matching scores for each reiccpient and the detected fingerprint
        :param fingerprint: string of characters describing binary representation of a fingerprint or a bitstring
        :param secret_key: owner's secret key used to fingerprint the data
        :return:
        """
        if isinstance(fingerprint, bitstring.BitArray):
            fingerprint: ndarray = np.array(list(fingerprint.bin), dtype=int)

        scores = dict()
        if self.fingerprint_code_type == 'hash':
            scores = decode_hash_fingerprint(fingerprint, secret_key, self.number_of_recipients)
        elif self.fingerprint_code_type == 'tardos':
            scores = tardos.exact_matching_scores(fingerprint, secret_key, self.number_of_recipients)
        scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
        scores = {k: float(v) for k, v in scores.items()}

        return scores

    def insertion(self, dataset_name, recipient_id, secret_key, primary_key_name=None, outfile=None,
                  correlated_attributes=None, save_computation=True, phi=0.75):
        """
        Embeds a fingerprint into the data using NCorrFP algorithm.
        Args:
            dataset_name: string name of the predefined test dataset
            recipient_id: unique identifier of the recipient
            secret_key: owner's secret key
            primary_key_name: optional - name of the primary key attribute. If not specified, index is used
            outfile:  optional - name of the output file for writing fingerprinted dataset
            correlated_attributes: optional - list of names of correlated attributes. If multiple groups of correlated attributes exist, they collectivelly need to be passed as a list of lists. If not specified, all attributes will be used for neighbourhood search.

        Returns: fingerprinted dataset (pandas.DataFrame)

        """
        print("Start the NCorr fingerprint insertion algorithm. This might take a afew minutes.")
        if secret_key is not None:
            self.secret_key = secret_key
        # it is assumed that the first column in the dataset is the primary key
        if isinstance(dataset_name, datasets.Dataset):
            self.dataset = dataset_name
            relation = dataset_name.dataframe.copy()
            primary_key_name = dataset_name.get_primary_key_attribute()
            if correlated_attributes is None:
                correlated_attributes = dataset_name.correlated_attributes
        elif isinstance(dataset_name, pd.DataFrame):
            relation = dataset_name.copy()
        else:
            relation, primary_key_name = import_dataset_from_file(dataset_name, primary_key_name)
            if correlated_attributes is None:
                correlated_attributes = extract_mutually_correlated_groups(relation,
                                                                           threshold_num=0.70, threshold_cat=0.45)
        # number of numerical attributes minus primary key
        number_of_num_attributes = len(relation.select_dtypes(exclude='object').columns) - 1
        # number of non-numerical attributes
        number_of_cat_attributes = len(relation.select_dtypes(include='object').columns)
        # total number of attributes
        tot_attributes = number_of_num_attributes + number_of_cat_attributes
        print("\tgamma: " + str(self.gamma) +
              "\n\tk: " + str(self.k) +
              "\n\tcorrelated attributes: " + str(correlated_attributes))

        self.recipient_id = recipient_id
        fingerprint = self.create_fingerprint(recipient_id, secret_key)
        self.fingerprint = fingerprint
        print("Inserting the fingerprint...\n")

        start = time.time()
        time_profile = {'query_time': 0, 'write_time': 0, 'read_time': 0, 'mark_time': 0}

        # label encoder - needed for balltrees
        categorical_attributes = relation.select_dtypes(include='object').columns
        label_encoders = dict()
        for cat in categorical_attributes:
            label_enc = LabelEncoder()
            relation[cat] = label_enc.fit_transform(relation[cat])
            label_encoders[cat] = label_enc

        correlated_attributes = parse_correlated_attrs(correlated_attributes, relation)
        # ball trees from user-specified or calculated correlated attributes; normalised dataset for better distance calculation
        relation_norm = (relation - relation.min()) / (relation.max() - relation.min())
        if 'Id' in relation.columns:
            relation_wo_id = relation.drop('Id', axis=1)
        else:
            relation_wo_id = relation
        self.balltree = init_balltrees(correlated_attributes, relation_wo_id, self.dist_metric_discrete,
                                  self.dist_metric_continuous, categorical_attributes=categorical_attributes)

        fingerprinted_relation = relation.copy()
        self.insertion_iter_log = []  # reset iteration log
        for r in relation.iterrows():
            # r[0] is an index of a row = primary key
            # seed = concat(secret_key, primary_key)
            seed = int((self.secret_key << self.__primary_key_len) + r[1].iloc[0])  # first column must be primary key
            random.seed(seed)

            # selecting the tuple
            if random.choices([0, 1], [1 / self.gamma, 1 - 1 / self.gamma]) == [0]:  # gamma can be a float
                iteration = {'seed': seed, 'row_index': r[1].iloc[0]}
                # selecting the attribute
                attr_idx = random.randint(0, _MAXINT) % tot_attributes + 1  # +1 to skip the prim key
                read_start = time.time()
                attr_name = r[1].index[attr_idx]
                attribute_val = r[1].iloc[attr_idx]
                iteration['attribute'] = attr_name

                read_end = time.time()
                time_profile['read_time'] += read_end - read_start

                # select fingerprint bit
                fingerprint_idx = random.randint(0, _MAXINT) % self.fingerprint_bit_length
                iteration['fingerprint_idx'] = fingerprint_idx

                fingerprint_bit = fingerprint[fingerprint_idx]
                iteration['fingerprint_bit'] = fingerprint_bit

                # select mask and calculate the mark bit
                mask_bit = random.randint(0, _MAXINT) % 2
                iteration['mask_bit'] = mask_bit

                mark_bit = (mask_bit + fingerprint_bit) % 2
                iteration['mark_bit'] = mark_bit

                marked_attribute = attribute_val
                # fp information: if mark_bit = fp_bit xor mask_bit is 1 then take the most frequent value,
                # # # otherwise one of the less frequent ones

                # selecting attributes for knn search -> this is user specified
                # get the index of a group of correlated attributes to attr; if attr is not correlated then return None
                corr_group_index = next((i for i, sublist in enumerate(correlated_attributes) if attr_name in sublist), None)
                # if attr_name in correlated_attributes:
                if corr_group_index is not None:
                    other_attributes = correlated_attributes[corr_group_index].tolist().copy()
                    other_attributes.remove(attr_name)
                    bt = self.balltree[attr_name]
                else:
                    other_attributes = r[1].index.tolist().copy()
                    other_attributes.remove(attr_name)
                    if 'Id' in other_attributes:
                        other_attributes.remove('Id')
                    bt = self.balltree[attr_name]
                if self.distance_based:
                    querying_start = time.time()
                    neighbours, dist = bt.query_radius([relation[other_attributes].loc[r[0]]], r=self.d,
                                                       return_distance=True, sort_results=True)
                    querying_end = time.time()
                    time_profile['query_time'] += querying_end-querying_start
 #                   print('Balltree querying in {} seconds.'.format(round(querying_end-querying_start, 8)))
                else:
                    # nondeterminism - non chosen tuples with max distance
                    if not save_computation:
                        querying_start = time.time()
                        dist, neighbours = bt.query([relation[other_attributes].loc[r[0]]], k=self.k)
                        querying_end = time.time()
                        time_profile['query_time'] += querying_end-querying_start
 #                       print('Balltree querying (1st) in {} seconds.'.format(round(querying_end - querying_start, 8)))
                        dist = dist[0].tolist()
                        radius = np.ceil(max(dist) * 10 ** 6) / 10 ** 6  # ceil the float max dist to 6th decimal
                        querying_start = time.time()
                        neighbours, dist = bt.query_radius(
                            [relation[other_attributes].loc[r[0]]], r=radius, return_distance=True,
                            sort_results=True)  # the list of neighbours is first (and only) element of the returned list
                        querying_end = time.time()
                        time_profile['query_time'] += querying_end-querying_start
#                        print('Balltree querying (2nd) in {} seconds.'.format(round(querying_end - querying_start, 8)))
                        neighbours = neighbours[0].tolist()
                    else: # we allow the flag for saving computation which requires only one query function but might result in non-determinism
                        querying_start = time.time()
#                        print(relation[other_attributes].loc[r[0]])
                        # query the normalised record
                        dist, neighbours = bt.query([relation[other_attributes].loc[r[0]]], k=3*self.k)  # query with extra neighbourhs
#                        print(dist)
                        k_dist = dist[0][self.k - 1]  # Distance of the kth nearest neighbor
                        neighbours = neighbours[0][dist[0] <= k_dist]  # Get k neighbours plus the ties
                        querying_end = time.time()
                        time_profile['query_time'] += querying_end-querying_start
#                        print('Balltree querying (efficient) in {} seconds.'.format(round(querying_end - querying_start, 8)))
                iteration['neighbors'] = neighbours
                iteration['dist'] = dist

                marking_start = time.time()
                neighbourhood = relation.iloc[neighbours][attr_name].tolist()
                if attr_name in categorical_attributes:
                    marked_attribute = mark_categorical_value(neighbourhood, mark_bit, percentile=phi)
                    iteration['new_value'] = label_encoders[attr_name].inverse_transform([marked_attribute])[0]
                else:
                    marked_attribute = mark_continuous_value(neighbourhood, mark_bit, seed=seed, percentile=phi)
                    iteration['new_value'] = marked_attribute

                marking_end = time.time()
                time_profile['mark_time'] += marking_end - marking_start

                writing_time_start = time.time()
                fingerprinted_relation.at[r[0], r[1].keys()[attr_idx]] = marked_attribute
                self.insertion_iter_log.append(iteration)
                writing_time_end = time.time()
                time_profile['write_time'] += writing_time_end - writing_time_start
#                print('Writing one fingerprinted value in {} seconds.'.format(round(writing_time_end-writing_time_start, 8)))

        # delabeling
        for cat in categorical_attributes:
            fingerprinted_relation[cat] = label_encoders[cat].inverse_transform(fingerprinted_relation[cat])

        print("Fingerprint inserted.")
        if secret_key is None:
            write_dataset(fingerprinted_relation, "categorical_neighbourhood", "blind/" + dataset_name,
                          [self.gamma, self.xi],
                          recipient_id)
        runtime = time.time() - start
        # if runtime < 1:
        #     print("Runtime: " + str(round(runtime*1000, 2)) + " ms.")
        # else:
        #     print("Runtime: " + str(round(runtime, 2)) + " sec.")
        # print(time_profile)
        if outfile is not None:
            fingerprinted_relation.to_csv(outfile, index=False)
        return fingerprinted_relation

    def detection(self, dataset, secret_key, primary_key=None, correlated_attributes=None, original_columns=None,
                  save_computation=True, balltree=None, phi=0.75):
        """

        Args:
            dataset: suspicious dataset containing a fingerprint
            secret_key: (int) owner's secret key
            primary_key:
            correlated_attributes: a list of correlated attributes (or a list of lists of correlated attributes)
            original_columns: a list of original columns in the dataset
            save_computation: if True, some non-determinism is introuduced to cut off lengthy calculations

        Returns:
            recipient_no: identification of the recipient of detected fingerprint
            detected_fp: detected fingerprint bitstring
            count: array of bit-wise fingerprint votes

        """
        print("Start NCorr fingerprint detection algorithm ...")
        print("\tgamma: " + str(self.gamma) +
              "\n\tk: " + str(self.k) +
              "\n\tfp length: " + str(self.fingerprint_bit_length) +
              "\n\ttotal # recipients: " + str(self.number_of_recipients) +
              "\n\tcorrelated attributes: " + str(correlated_attributes))

        relation_fp = read_data(dataset)
        self.relation_fp = relation_fp
        # indices = list(relation_fp.dataframe.index)
        # number of numerical attributes minus primary key
        number_of_num_attributes = len(relation_fp.dataframe.select_dtypes(exclude='object').columns) - 1
        number_of_cat_attributes = len(relation_fp.dataframe.select_dtypes(include='object').columns)
        tot_attributes = number_of_num_attributes + number_of_cat_attributes
        categorical_attributes = relation_fp.dataframe.select_dtypes(include='object').columns

        attacked_columns = []
        if original_columns is not None:  # aligning with original schema (in case of vertical attacks)
            if "Id" in original_columns:
                original_columns.remove("Id")
            for orig_col in original_columns:
                if orig_col not in relation_fp.columns:
                    # fill in
                    relation_fp.dataframe[orig_col] = 0
                    attacked_columns.append(orig_col)
            # rearrange in the original order
            if "Id" in relation_fp.dataframe:
                relation_fp.dataframe = relation_fp.dataframe[["Id"] + original_columns]
                relation_fp.dataframe = relation_fp.dataframe[["Id"] + original_columns]
            else:
                relation_fp.dataframe = relation_fp.dataframe[original_columns]
            tot_attributes += len(attacked_columns)

        # encode the categorical values
        label_encoders = dict()
        for cat in categorical_attributes:
            label_enc = LabelEncoder()
            relation_fp.dataframe[cat] = label_enc.fit_transform(relation_fp.dataframe[cat])
            label_encoders[cat] = label_enc

        start = time.time()
        correlated_attributes = parse_correlated_attrs(correlated_attributes, relation_fp.dataframe)
        relation_fp_norm = (relation_fp.dataframe - relation_fp.dataframe.min()) / (relation_fp.dataframe.max() - relation_fp.dataframe.min())
        if balltree is None:
            if 'Id' in relation_fp.dataframe.columns:
                relation_fp_wo_id = relation_fp.dataframe.drop('Id', axis=1)
            else:
                relation_fp_wo_id = relation_fp.dataframe
            balltree = init_balltrees(correlated_attributes, relation_fp_wo_id,
                                      self.dist_metric_discrete, self.dist_metric_continuous, categorical_attributes)

        count = [[0, 0] for x in range(self.fingerprint_bit_length)]
        self.detection_iter_log = []  # reset the iteration log
        for r in relation_fp.dataframe.iterrows():
            seed = int((secret_key << self.__primary_key_len) + r[1].iloc[0])  # primary key must be the first column
            random.seed(seed)
            # this tuple was marked
            if random.choices([0, 1], [1 / self.gamma, 1 - 1 / self.gamma]) == [0]:
                iteration = {'seed': seed, 'row_index': r[1].iloc[0]}

                # this attribute was marked (skip the primary key)
                attr_idx = random.randint(0, _MAXINT) % tot_attributes + 1  # add 1 to skip the primary key
                attr_name = r[1].index[attr_idx]
                if attr_name in attacked_columns:  # if this columns was deleted by VA, don't collect the votes
                    continue
                iteration['attribute'] = attr_name

                attribute_val = r[1].iloc[attr_idx]
                iteration['attribute_val'] = attribute_val

                # fingerprint bit
                fingerprint_idx = random.randint(0, _MAXINT) % self.fingerprint_bit_length
                iteration['fingerprint_idx'] = fingerprint_idx

                # mask
                mask_bit = random.randint(0, _MAXINT) % 2
                iteration['mask_bit'] = mask_bit

                corr_group_index = next((i for i, sublist in enumerate(correlated_attributes) if attr_name in sublist), None)
                if corr_group_index is not None:  # if attr_name is in correlated attributes
                    other_attributes = correlated_attributes[corr_group_index].tolist().copy()
                    other_attributes.remove(attr_name)
                    bt = balltree[attr_name]
                else:
                    other_attributes = r[1].index.tolist().copy()
                    other_attributes.remove(attr_name)
                    if "Id" in other_attributes:
                        other_attributes.remove('Id')
                    bt = balltree[attr_name]
                if self.distance_based:
                    neighbours, dist = bt.query_radius([relation_fp.dataframe[other_attributes].loc[r[1].iloc[0]]], r=self.d,
                                                       return_distance=True, sort_results=True)
                else:  # if it's neighbourhood-cardinality-based
                    if not save_computation:
                        # find the neighborhood of cardinality k (non-deterministic)
                        dist, neighbours = bt.query([relation_fp.dataframe[other_attributes].loc[r[1].iloc[0]]], k=self.k)
                        dist = dist[0].tolist()
                        # solve nondeterminism: get all other elements of max distance in the neighbourhood
                        radius = np.ceil(max(dist) * 10 ** 6) / 10 ** 6  # ceil the float max dist to 6th decimal
                        neighbours, dist = bt.query_radius(
                            [relation_fp.dataframe[other_attributes].loc[r[1].iloc[0]]], r=radius, return_distance=True,
                            sort_results=True)
                        neighbours = neighbours[0].tolist()  # the list of neighbours was first (and only) element of the returned list
                        dist = dist[0].tolist()

                    else:  # we allow potential non-determinism to reduce the execusion time
                        dist, neighbours = bt.query([relation_fp.dataframe[other_attributes].loc[r[0]]], k=3*self.k)
                        k_dist = dist[0][self.k - 1]
                        neighbours = neighbours[0][dist[0] <= k_dist]  # get k neighbours plus the ties

                iteration['neighbors'] = neighbours
                iteration['dist'] = dist

                # check the frequencies of the values
                neighbourhood = relation_fp.dataframe.iloc[neighbours][attr_name].tolist()  # target values
                if len(set(neighbourhood)) == 1:
                    # the mark bit is undecided so we don't update the votes
                    iteration['mark_bit'] = -1
                    iteration['fingerprint_bit'] = -1
                else:
                    mark_bit = get_mark_bit(is_categorical=(attr_name in categorical_attributes),
                                            attribute_val=attribute_val, neighbours=neighbourhood,
                                            relation_fp=relation_fp, attr_name=attr_name, percentile=phi)
                    fingerprint_bit = (mark_bit + mask_bit) % 2
                    count[fingerprint_idx][fingerprint_bit] += 1
                    iteration['mark_bit'] = mark_bit
                    iteration['fingerprint_bit'] = fingerprint_bit

                iteration['count_state'] = copy.deepcopy(count)

                self.detection_iter_log.append(iteration)

        # this fingerprint template will be upside-down from the real binary representation
        fingerprint_template = [2] * self.fingerprint_bit_length
        # recover fingerprint
        for i in range(self.fingerprint_bit_length):
            # certainty of a fingerprint value
            T = 0.50
            if count[i][0] + count[i][1] != 0:
                if count[i][0] / (count[i][0] + count[i][1]) > T:
                    fingerprint_template[i] = 0
                elif count[i][1] / (count[i][0] + count[i][1]) > T:
                    fingerprint_template[i] = 1

        self.detected_fp = fingerprint_template
        print("Fingerprint detected: " + list_to_string(self.detected_fp))
        self.count = count
#        print(count) # uncomment to see the votes

        # first step in fp attribution: exact matching scores
        exact_match_scores = self.exact_matching_scores(fingerprint_template, secret_key)
#        print("The fingerprint is matched with probabilities:")
#        print(exact_match_scores) # uncomment to see the exact scores for all recipients
#        recipient_no = self.detect_potential_traitor(fingerprint_template, secret_key)
#        if recipient_no >= 0:
#            print("Fingerprint belongs to Recipient " + str(recipient_no))
#        else:
#            print("None suspected.")
        if self.fingerprint_code_type == 'tardos':
            collusion_scores = tardos.score_users(fingerprint_template, secret_key, self.number_of_recipients)
 #           print('Collusion scores: ', collusion_scores) # uncomment to see the collusion codes
        runtime = time.time() - start
        # if runtime < 1:
        #     print("Runtime: " + str(int(runtime)*1000) + " ms.")
        # else:
        #     print("Runtime: " + str(round(runtime, 2)) + " sec.")
        return fingerprint_template, count, exact_match_scores

    def detect_colluders(self, pirate_fingerprint, secret_key, threshold=1):
        """
        Detect colluders by calculating suspicion scores based on the pirate fingerprint.

        Args:
        codes (np.ndarray): Matrix of fingerprint codes for all users.
        pirate_fingerprint (np.ndarray): The pirate fingerprint obtained from collusion.
        t (float): The factor for standard deviation affecting the threshold for accusation. Larger values lead to more confidence.

        Returns:
        list: List of suspected colluders (user indices). List of suspicion scores.
        """
        codebook = np.array([self.create_fingerprint(recipient_id=i, secret_key=secret_key, show_messages=False)
                             for i in range(self.number_of_recipients)])

        n_users, code_length = codebook.shape
        suspicion_scores = np.zeros(n_users)

        # Calculate suspicion score for each user
        for i in range(n_users):
            for j in range(code_length):
                if codebook[i][j] == pirate_fingerprint[j]:
                    suspicion_scores[i] += np.log(2)  # Positive contribution for matching bit
                else:
                    suspicion_scores[i] += np.log(1)  # No contribution for non-matching bit (log(1) = 0)

        threshold = suspicion_scores.mean() + threshold * suspicion_scores.std()

        # Accuse users whose suspicion score exceeds the threshold
        suspected_colluders = [i for i, score in enumerate(suspicion_scores) if score >= threshold]

        return suspected_colluders, suspicion_scores


#    @deprecated("This function is about to be removed. Use scheme.insertion_iter_log instead.")
    def demo_insertion(self, dataset_name, recipient_id, secret_key, primary_key_name=None, outfile=None,
                       correlated_attributes=None):
#        warnings.warn(
#            "This function is deprecated and will be removed in future versions. Use NCorrFP.demo.insertion "
#            "instead",
#            DeprecationWarning,
#            stacklevel=2
#        )
        print("Start the demo NCorr fingerprint insertion algorithm...")
        print("\tgamma: " + str(self.gamma) + "\n\tcorrelated attributes: " + str(correlated_attributes))
        if secret_key is not None:
            self.secret_key = secret_key
        # it is assumed that the first column in the dataset is the primary key
        if isinstance(dataset_name, datasets.Dataset):
            relation = dataset_name.dataframe
            primary_key_name = dataset_name.get_primary_key_attribute()
        else:
            relation, primary_key = import_dataset_from_file(dataset_name, primary_key_name)
        # number of numerical attributes minus primary key
        number_of_num_attributes = len(relation.select_dtypes(exclude='object').columns) - 1
        # number of non-numerical attributes
        number_of_cat_attributes = len(relation.select_dtypes(include='object').columns)
        # total number of attributes
        tot_attributes = number_of_num_attributes + number_of_cat_attributes

        fingerprint = self.create_fingerprint(recipient_id, secret_key)
        # print("\nGenerated fingerprint for recipient " + str(recipient_id) + ": " + str(fingerprint))
        print("Inserting the fingerprint...\n")

        start = time.time()

        # label encoder
        categorical_attributes = relation.select_dtypes(include='object').columns
        label_encoders = dict()
        for cat in categorical_attributes:
            label_enc = LabelEncoder()
            relation[cat] = label_enc.fit_transform(relation[cat])
            label_encoders[cat] = label_enc

        correlated_attributes = parse_correlated_attrs(correlated_attributes, relation)
        # ball trees from user-specified correlated attributes
        balltree = init_balltrees(correlated_attributes, relation.drop('Id', axis=1),
                                  self.dist_metric_discrete, self.dist_metric_continuous, categorical_attributes)

        fingerprinted_relation = relation.copy()
        iter_log = []
        for r in relation.iterrows():
            # r[0] is an index of a row = primary key
            # seed = concat(secret_key, primary_key)
            seed = (self.secret_key << self.__primary_key_len) + r[1].iloc[0]  # first column must be primary key
            random.seed(seed)
            # selecting the tuple
            if random.choices([0, 1], [1 / self.gamma, 1 - 1 / self.gamma]) == [0]:
                iteration = {'seed': seed, 'row_index': r[1].iloc[0]}
                # selecting the attribute
                attr_idx = random.randint(0, _MAXINT) % tot_attributes + 1  # +1 to skip the prim key
                attr_name = r[1].index[attr_idx]
                attribute_val = r[1][attr_idx]
                iteration['attribute'] = attr_name

                # select fingerprint bit
                fingerprint_idx = random.randint(0, _MAXINT) % self.fingerprint_bit_length
                iteration['fingerprint_idx'] = fingerprint_idx
                fingerprint_bit = fingerprint[fingerprint_idx]
                iteration['fingerprint_bit'] = fingerprint_bit
                # select mask and calculate the mark bit
                mask_bit = random.randint(0, _MAXINT) % 2
                iteration['mask_bit'] = mask_bit
                mark_bit = (mask_bit + fingerprint_bit) % 2
                iteration['mark_bit'] = mark_bit

                marked_attribute = attribute_val
                # fp information: if mark_bit = fp_bit xor mask_bit is 1 then take the most frequent value,
                # # # otherwise the second most frequent

                # selecting attributes for knn search -> this is user specified
                # get the index of a group of correlated attributes to attr; if attr is not correlated then return None
                corr_group_index = next((i for i, sublist in enumerate(correlated_attributes) if attr_name in sublist),
                                        None)
                # if attr_name in correlated_attributes:
                if corr_group_index is not None:
                    other_attributes = correlated_attributes[corr_group_index].tolist().copy()
                    other_attributes.remove(attr_name)
                    bt = balltree[attr_name]
                else:
                    other_attributes = r[1].index.tolist().copy()
                    other_attributes.remove(attr_name)
                    other_attributes.remove('Id')
                    bt = balltree[attr_name]
                if self.distance_based:
                    neighbours, dist = bt.query_radius([relation[other_attributes].loc[r[0]]], r=self.d,
                                                       return_distance=True, sort_results=True)

                else:
                    # nondeterminism - non chosen tuples with max distance
                    dist, neighbours = bt.query([relation[other_attributes].loc[r[0]]], k=self.k)
                    dist = dist[0].tolist()
                    radius = np.ceil(max(dist) * 10 ** 6) / 10 ** 6  # ceil the float max dist to 6th decimal
                    neighbours, dist = bt.query_radius(
                        [relation[other_attributes].loc[r[0]]], r=radius, return_distance=True,
                        sort_results=True)  # the list of neighbours is first (and only) element of the returned list
                    neighbours = neighbours[0].tolist()
                dist = dist[0].tolist()
                iteration['neighbors'] = neighbours
                iteration['dist'] = dist

                neighbourhood = relation.iloc[neighbours][attr_name].tolist()
                if attr_name in categorical_attributes:
                    marked_attribute = mark_categorical_value(neighbourhood, mark_bit)
                else:
                    marked_attribute = mark_continuous_value(neighbourhood, mark_bit, seed=seed)

#                if attr_name in categorical_attributes:
#                    iteration['frequencies'] = dict()
#                    for (k, val) in frequencies.items():
#                        decoded_k = label_encoders[attr_name].inverse_transform([k])
#                        iteration['frequencies'][decoded_k[0]] = val
#                else:
#                    iteration['frequencies'] = frequencies
                iteration['new_value'] = marked_attribute
                # print("Index " + str(r[0]) + ", attribute " + str(r[1].keys()[attr_idx]) + ", from " +
                #      str(attribute_val) + " to " + str(marked_attribute))
                fingerprinted_relation.at[r[0], r[1].keys()[attr_idx]] = marked_attribute
                iter_log.append(iteration)
                #   STOPPING DEMO
                # if iteration['id'] == 1:
                #    exit()

        # delabeling
        for cat in categorical_attributes:
            fingerprinted_relation[cat] = label_encoders[cat].inverse_transform(fingerprinted_relation[cat])

        print("Fingerprint inserted.")
        if secret_key is None:
            write_dataset(fingerprinted_relation, "categorical_neighbourhood", "blind/" + dataset_name,
                          [self.gamma, self.xi],
                          recipient_id)
        runtime = time.time() - start
        # if runtime < 1:
        #     print("Runtime: " + str(int(runtime) * 1000) + " ms.")
        # else:
        #     print("Runtime: " + str(round(runtime, 2)) + " sec.")
        if outfile is not None:
            fingerprinted_relation.to_csv(outfile, index=False)
        return fingerprinted_relation, fingerprint, iter_log

 #   @deprecated("This function is about to be removed. Use scheme.detection_iter_log instead.")
    def demo_detection(self, dataset, secret_key, primary_key=None, correlated_attributes=None, original_columns=None):
#        warnings.warn(
#            "This function is deprecated and will be removed in future versions. Use NCorrFP.demo.detection "
#            "instead",
#            DeprecationWarning,
#            stacklevel=2
#        )
        print("Start demo NCorr fingerprint detection algorithm ...")
        print("\tgamma: " + str(self.gamma) + "\n\tcorrelated attributes: " + str(correlated_attributes))

        relation_fp = read_data(dataset, correlated_attributes=correlated_attributes)
        # indices = list(relation_fp.dataframe.index)
        # number of numerical attributes minus primary key
        number_of_num_attributes = len(relation_fp.dataframe.select_dtypes(exclude='object').columns) - 1
        number_of_cat_attributes = len(relation_fp.dataframe.select_dtypes(include='object').columns)
        tot_attributes = number_of_num_attributes + number_of_cat_attributes
        categorical_attributes = relation_fp.dataframe.select_dtypes(include='object').columns

        attacked_columns = []
        if original_columns is not None:  # aligning with original schema (in case of vertical attacks)
            if "Id" in original_columns:
                original_columns.remove("Id")  # just in case
            for orig_col in original_columns:
                if orig_col not in relation_fp.columns:
                    # fill in
                    relation_fp.dataframe[orig_col] = 0
                    attacked_columns.append(orig_col)
            # rearrange in the original order
            relation_fp.dataframe = relation_fp.dataframe[["Id"] + original_columns]
            tot_attributes += len(attacked_columns)

        # encode the categorical values
        label_encoders = dict()
        for cat in categorical_attributes:
            label_enc = LabelEncoder()
            relation_fp.dataframe[cat] = label_enc.fit_transform(relation_fp.dataframe[cat])
            label_encoders[cat] = label_enc

        start = time.time()
        correlated_attributes = parse_correlated_attrs(correlated_attributes, relation_fp.dataframe)
        balltree = init_balltrees(correlated_attributes, relation_fp.dataframe.drop('Id', axis=1),
                                  self.dist_metric_discrete, self.dist_metric_continuous, categorical_attributes)

        count = [[0, 0] for x in range(self.fingerprint_bit_length)]
        iter_log = []
        for r in relation_fp.dataframe.iterrows():
            seed = (self.secret_key << self.__primary_key_len) + r[1].iloc[0]  # primary key must be the first column
            random.seed(seed)
            # this tuple was marked
            if random.choices([0, 1], [1 / self.gamma, 1 - 1 / self.gamma]) == [0]:
                iteration = {'seed': seed, 'row_index': r[1].iloc[0]}
                # this attribute was marked (skip the primary key)
                attr_idx = random.randint(0, _MAXINT) % tot_attributes + 1  # add 1 to skip the primary key
                attr_name = r[1].index[attr_idx]
                if attr_name in attacked_columns:  # if this columns was deleted by VA, don't collect the votes
                    continue
                iteration['attribute'] = attr_name
                attribute_val = r[1][attr_idx]
                iteration['attribute_val'] = attribute_val
                # fingerprint bit
                fingerprint_idx = random.randint(0, _MAXINT) % self.fingerprint_bit_length
                iteration['fingerprint_idx'] = fingerprint_idx
                # mask
                mask_bit = random.randint(0, _MAXINT) % 2
                iteration['mask_bit'] = mask_bit

                corr_group_index = next((i for i, sublist in enumerate(correlated_attributes) if attr_name in sublist),
                                        None)
                if corr_group_index is not None:  # if attr_name is in correlated attributes
                    other_attributes = correlated_attributes[corr_group_index].tolist().copy()
                    other_attributes.remove(attr_name)
                    bt = balltree[attr_name]
                else:
                    other_attributes = r[1].index.tolist().copy()
                    other_attributes.remove(attr_name)
                    other_attributes.remove('Id')
                    bt = balltree[attr_name]
                if self.distance_based:
                    neighbours, dist = bt.query_radius([relation_fp[other_attributes].loc[r[1].iloc[0]]], r=self.d,
                                                       return_distance=True, sort_results=True)
                else:
                    # find the neighborhood of cardinality k (non-deterministic)
                    dist, neighbours = bt.query([relation_fp.dataframe[other_attributes].loc[r[1].iloc[0]]], k=self.k)
                    dist = dist[0].tolist()
                    # solve nondeterminism: get all other elements of max distance in the neighbourhood
                    radius = np.ceil(max(dist) * 10 ** 6) / 10 ** 6  # ceil the float max dist to 6th decimal
                    neighbours, dist = bt.query_radius(
                        [relation_fp.dataframe[other_attributes].loc[r[1].iloc[0]]], r=radius, return_distance=True,
                        sort_results=True)
                    neighbours = neighbours[
                        0].tolist()  # the list of neighbours was first (and only) element of the returned list
                    dist = dist[0].tolist()

                iteration['neighbors'] = neighbours
                iteration['dist'] = dist

                # check the frequencies of the values
                neighbourhood = relation_fp.dataframe.iloc[neighbours][attr_name].tolist()
                mark_bit = get_mark_bit(is_categorical=(attr_name in categorical_attributes),
                                        attribute_val=attribute_val, neighbours=neighbourhood,
                                        relation_fp=relation_fp, attr_name=attr_name)

                fingerprint_bit = (mark_bit + mask_bit) % 2
                count[fingerprint_idx][fingerprint_bit] += 1

                iteration['count_state'] = copy.deepcopy(count)  # this returns the final counts for each step ??
                iteration['mark_bit'] = mark_bit
                iteration['fingerprint_bit'] = fingerprint_bit

                iter_log.append(iteration)

        # this fingerprint template will be upside-down from the real binary representation
        fingerprint_template = [2] * self.fingerprint_bit_length
        # recover fingerprint
        for i in range(self.fingerprint_bit_length):
            # certainty of a fingerprint value
            T = 0.50
            if count[i][0] + count[i][1] != 0:
                if count[i][0] / (count[i][0] + count[i][1]) > T:
                    fingerprint_template[i] = 0
                elif count[i][1] / (count[i][0] + count[i][1]) > T:
                    fingerprint_template[i] = 1

        print("Fingerprint detected: " + list_to_string(fingerprint_template))
        # print(count)

        recipient_no = self.exact_matching_scores(fingerprint_template, secret_key)
        #if recipient_no >= 0:
        #    print("Fingerprint belongs to Recipient " + str(recipient_no))
        #else:
        #    print("None suspected.")
        runtime = time.time() - start
        # if runtime < 1:
        #     print("Runtime: " + str(int(runtime) * 1000) + " ms.")
        # else:
        #     print("Runtime: " + str(round(runtime, 2)) + " sec.")
        return recipient_no, list_to_string(fingerprint_template), iter_log
