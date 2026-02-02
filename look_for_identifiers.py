# I'll go through the various fields of the xml file, looking for identifiers in the text. I'll then use the
# synonymizer to get the preferred CURIE for each identifier and save the results to a json & pkl file.
import argparse
import os
from pathlib import Path

import xmltodict
import json
import pickle

from download_script import ensure_downloaded_and_verified
from node_synonymizer import NodeSynonymizer
import re

from CONSTANTS import DATABASE_PREFIXES, REGEX_PATTERNS, IDENTIFIER_FIELDS


def find_curies_with_prefix(text):
    """
    This function finds all the curies in the text using the regex patterns in REGEX_PATTERNS and returns a list of
    dictionaries with the curie, preferred name, and the category of the curie
    :param text: str
    :return: list of dictionaries
    """
    res = []
    for key, pattern in REGEX_PATTERNS.items():
        found = re.compile(pattern).findall(text)
        for f in found:
            curie = DATABASE_PREFIXES[key] + ":" + text  # the regex can get partial matches, so I'll add the prefix
            # to the full input (not the matched portion)
            syn_result = synonymizer.get_canonical_curies(curie)
            if syn_result[curie]:
                preferred_name = syn_result[curie]['preferred_name']
                category = syn_result[curie]['preferred_category']
                preferred_curie = syn_result[curie]['preferred_curie']
                res.append({'preferred_curie': preferred_curie, 'preferred_name': preferred_name, 'preferred_category': category})
    return res


def kg_version_validator(value: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise argparse.ArgumentTypeError("KG version must look like X.Y.Z (e.g. 2.10.2)")
    return value


def parse_args():
    parser = argparse.ArgumentParser(
        description="Builds curie_ngd sqlite database for a given KG version."
    )

    parser.add_argument(
        "--kg-version",
        type=kg_version_validator,
        required=True,
        metavar="VERSION",
        help="Knowledge graph version (e.g. 2.10.2)",
    )

    parser.add_argument(
        "--plover-url",
        type=str,
        required=True,
        help="PloverDB URL",
    )

    parser.add_argument(
        "--db-host",
        default="arax-databases.rtx.ai",
        type=str,
        help="Database file host (default: arax-databases.rtx.ai)",
    )

    parser.add_argument(
        "--db-username",
        default="rtxconfig",
        type=str,
        help="Database file username (default: rtxconfig)",
    )

    parser.add_argument(
        "--db-port",
        default=22,
        type=int,
        help="Database file port (default: 22)",
    )

    parser.add_argument(
        "--ssh-key",
        default=None,
        help="Path to SSH private key (optional). If omitted, uses SSH agent/default keys.",
    )

    parser.add_argument(
        "--ssh-password",
        default=None,
        help="SSH password (optional; prefer key/agent). You can also set SSH_PASSWORD env var.",
    )

    parser.add_argument(
        "--redis-host",
        default="localhost",
        type=str,
        help="Redis host (default: localhost)",
    )

    parser.add_argument(
        "--redis-port",
        default=6379,
        type=int,
        help="Redis port (default: 6379)",
    )

    parser.add_argument(
        "--redis-db",
        default=0,
        type=int,
        help="Redis database index (default: 0)",
    )

    parser.add_argument(
        "--num-pubmed-articles",
        default=3.5e7,
        type=float,
        help="Number of PubMed citations and abstracts (default: 3.5e7)",
    )

    parser.add_argument(
        "--avg-mesh-terms-per-article",
        default=20,
        type=int,
        help="Average number of MeSH terms per article (default: 20)",
    )

    # Optional: choose output dir for downloads
    parser.add_argument(
        "--out-dir",
        default="./data",
        type=str,
        help="Where to store downloaded DB files (default: current directory)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    kg_version = args.kg_version
    db_host = args.db_host
    db_username = args.db_username
    db_port = args.db_port
    ssh_key = args.ssh_key
    ssh_password = args.ssh_password or os.getenv("SSH_PASSWORD")
    synonymizer_dbname = f'node_synonymizer_v1.0_KG{kg_version}.sqlite'

    out_dir_str = args.out_dir
    out_dir = Path(out_dir_str)
    remote_path_synonymizer_db = f"~/KG{kg_version}/{synonymizer_dbname}"

    local_path_synonymizer_db = out_dir / synonymizer_dbname

    ensure_downloaded_and_verified(
        host=db_host,
        username=db_username,
        port=db_port,
        remote_path=remote_path_synonymizer_db,
        local_path=local_path_synonymizer_db,
        key_path=ssh_key,
        password=ssh_password,
    )

    synonymizer = NodeSynonymizer("./data", synonymizer_dbname)

    # doc = get_xml_data()
    # kg2_drug_info = process_drug_bank_xmldict_data(doc)
    # Just read in the pkl file: ./data/kg2_drug_info.pkl
    with open(f'{out_dir_str}/kg2_drug_info.pkl', 'rb') as f:
        kg2_drug_info = pickle.load(f)

    # Go through each drug, use the names to find KG2 nodes, and then use the identifiers to find the preferred curies
    # add each to the mechanistic_intermediate_nodes field
    i = 0
    for drug in kg2_drug_info.keys():
        print(f"Processing drug {i} of {len(kg2_drug_info.keys())}")
        i += 1
        for field in IDENTIFIER_FIELDS:
            # Align the names to KG2
            names = []
            if kg2_drug_info[drug].get(field):
                names = kg2_drug_info[drug].get(field).get('names')
            if names:
                res = synonymizer.get_canonical_curies(names=names)
                for key, value in res.items():
                    if value:
                        preferred_name = value['preferred_name']
                        preferred_curie = value['preferred_curie']
                        preferred_category = value['preferred_category']
                        if preferred_curie not in kg2_drug_info[drug]['mechanistic_intermediate_nodes']:
                            kg2_drug_info[drug]['mechanistic_intermediate_nodes'].update(
                                {preferred_curie: {'name': preferred_name,
                                                   'category': preferred_category}})
            # Align the IDs to KG2
            ids = []
            if kg2_drug_info[drug].get(field):
                ids = kg2_drug_info[drug].get(field).get('ids')
                if ids:
                    for id in ids:
                        if ":" not in id:  # That means I'm dealing with a suffix
                            results = find_curies_with_prefix(id)
                            for res in results:
                                preferred_name = res['preferred_name']
                                preferred_curie = res['preferred_curie']
                                preferred_category = res['preferred_category']
                                if preferred_curie not in kg2_drug_info[drug]['mechanistic_intermediate_nodes']:
                                    kg2_drug_info[drug]['mechanistic_intermediate_nodes'].update(
                                        {preferred_curie: {'name': preferred_name,
                                                           'category': preferred_category}})

    # Now, let's write this to a JSON file
    with open(f'{out_dir_str}/DrugBank_aligned_with_KG2.json', 'w') as f:
        json.dump(kg2_drug_info, f, indent=2)
    # Also dump to a pickle file
    with open(f'{out_dir_str}/DrugBank_aligned_with_KG2.pkl', 'wb') as f:
        pickle.dump(kg2_drug_info, f)
