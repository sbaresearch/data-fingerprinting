from ncorr.ncorr import NCorrFP

import argparse
import json
import sys
import pandas as pd
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
        print(f"Configuration file {configuration_file} not found. Using defaults.")
    return config


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the fingerprint embedding process.")

    # Required parameters
    parser.add_argument("data", help="Path to data")
    parser.add_argument("secret_key", help="Secret key", type=int)
    parser.add_argument("user_id", help="Recipient ID", type=int)

    # Optional parameters
    parser.add_argument("--gamma", type=float, default=11.0, help="Gamma value (optional)")
    parser.add_argument("--fp_len", type=int, default=256, help="Fingerprint length (optional)")
    parser.add_argument("--out", default="fingerprinted_output.csv", help="Output file (optional)")
    parser.add_argument("--config", default="speml/config.json", help="Configuration file (optional)")
    parser.add_argument("--log", default="log.json", help="Log file (optional)")

    args = parser.parse_args()
    # Load additional parameters from configuration file
    config = load_config(args.config)
    extra_params = {i: config.get(i, None) for i in ['correlated_attributes', 'k']}

    scheme = NCorrFP(gamma=args.gamma, fingerprint_bit_length=args.fp_len, fingerprint_code_type='tardos',
                     k=extra_params["k"])
    data = args.data
    dataframe = pd.read_csv(data)
    fingerprinted_data = scheme.insertion(data, secret_key=args.secret_key, recipient_id=args.user_id,
                                          outfile=args.out, correlated_attributes=extra_params['correlated_attributes'])
    print("Result in {}".format(args.out))
    log = {"data": args.data, "gamma": args.gamma, "fp_len": args.fp_len, "user_id": args.user_id,
           "k": extra_params["k"], "original_columns": list(dataframe.columns), "**secret**": args.secret_key}
    with open(args.log, "w") as json_file:
        json.dump(log, json_file, indent=6)
    print("Embedding log in {} - save this file to ensure successful detection using the same parameters "
          "(Mind the secret).".format(args.log))
