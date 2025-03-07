from ncorr.ncorr import NCorrFP

import argparse
import sys
import json
import os


def load_config(configuration_file):
    """
    Loads configuration parameters from a JSON file.

    Parameters:
        configuration_file (str): Path to the JSON configuration file.

    Returns:
        dict: Dictionary containing the configuration parameters.
    """
    config = {}
    if configuration_file and os.path.exists(configuration_file):
        try:
            with open(configuration_file, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading configuration file: {e}")
            sys.exit(1)
    else:
        print(f"Configuration file {configuration_file} not found. Using defaults. (Finding correlations might slow down the process -- define them in the config file instead.)")
    return config


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the fingerprint detection process.")

    # Required parameters
    parser.add_argument("data", help="Path to fingerprinted data")
    parser.add_argument("secret_key", help="Secret key", type=int)

    # Optional parameters
    parser.add_argument("--gamma", type=float, default=11.0, help="Gamma value (optional)")
    parser.add_argument("--fp_len", type=int, default=256, help="Fingerprint length (optional)")
    parser.add_argument("--config", default="speml/config.json", help="Configuration file (optional)")

    args = parser.parse_args()
    # Load additional parameters from configuration file
    config = load_config(args.config)
    extra_params = {k: config.get(k, None) for k in ['correlated_attributes', 'original_columns', 'k']}

    scheme = NCorrFP(gamma=args.gamma, fingerprint_bit_length=args.fp_len, fingerprint_code_type='tardos',
                     k=extra_params['k'])
    data = args.data

    suspect = scheme.detection(data, secret_key=args.secret_key,
                               correlated_attributes=extra_params['correlated_attributes'],
                               original_columns=extra_params['original_columns'])

    no1sus, no1sus_conf = max(suspect[2].items(), key=lambda item: item[1])
    print("User id {} with confidence {}. ".format(no1sus, no1sus_conf))
#    print("\n\tAll confidences: ", suspect[2])
