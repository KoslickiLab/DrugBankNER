import argparse
import os
import re
from pathlib import Path

import NER
import json
import spacy
import pickle

from download_script import ensure_downloaded_and_verified
from utils import get_xml_data, delete_long_tokens, process_drug_bank_xmldict_data, remove_brackets
from CONSTANTS import MECHANISTIC_CATEGORIES, MOSTLY_TEXT_FIELDS

spacy.require_gpu()


def text_to_kg2_nodes(ners, text, categories=None):
    potential_mechanistic_matched_nodes = {}
    # split the text into sentences
    sentences = text.split('.')
    for sentence in sentences:
        # omit very long sequences and very short ones
        if len(sentence) > 1000 or len(sentence) < 15:
            continue
        # omit very long tokens/words
        sentence = delete_long_tokens(sentence)
        print(f"on sentence: {sentence}")
        for trapi_ner in ners:
            try:
                res = trapi_ner.get_kg2_match(sentence, remove_mark=True)
            except RuntimeError:
                continue
            for key, value in res.items():  # keys are plain text names, values are lists of tuples
                for v in value:  # v[0] is the KG2 identifier, v[1] is the node info in the form of a dict
                    if categories:
                        if v[1]['preferred_category'] in categories:
                            if v[0] not in potential_mechanistic_matched_nodes:
                                potential_mechanistic_matched_nodes[v[0]] = {'name': key,
                                                                             'category': v[1]['preferred_category']}
                            # replace name with longer name
                            elif v[0] in potential_mechanistic_matched_nodes and len(key) > len(
                                    potential_mechanistic_matched_nodes[v[0]]['name']):
                                potential_mechanistic_matched_nodes[v[0]]['name'] = key
                    else:
                        if v[0] not in potential_mechanistic_matched_nodes:
                            potential_mechanistic_matched_nodes[v[0]] = {'name': key,
                                                                         'category': v[1]['preferred_category']}
                        # replace name with longer name
                        elif v[0] in potential_mechanistic_matched_nodes and len(key) > len(
                                potential_mechanistic_matched_nodes[v[0]]['name']):
                            potential_mechanistic_matched_nodes[v[0]]['name'] = key
    return potential_mechanistic_matched_nodes


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


def main():
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

    # Chunyu's NER; different models have different strengths and weaknesses. Through trial and error, I decided on these
    # five, since each results in matches the other models don't get.
    ners = []
    trapi_ner = NER.TRAPI_NER(synonymizer_dir=out_dir_str, synonymizer_dbname=synonymizer_dbname,
                              linker_name=['umls', 'mesh'], spacy_model='en_core_sci_lg', threshold=0.70,
                              num_neighbors=15, max_entities_per_mention=1)
    ners.append(trapi_ner)
    trapi_ner = NER.TRAPI_NER(synonymizer_dir=out_dir_str, synonymizer_dbname=synonymizer_dbname,
                              linker_name=['umls', 'mesh'], spacy_model='en_core_sci_scibert', threshold=0.75,
                              num_neighbors=10, max_entities_per_mention=1)
    ners.append(trapi_ner)
    trapi_ner = NER.TRAPI_NER(synonymizer_dir=out_dir_str, synonymizer_dbname=synonymizer_dbname,
                              linker_name=['rxnorm'], spacy_model='en_core_sci_lg', threshold=0.70,
                              num_neighbors=15, max_entities_per_mention=1)
    ners.append(trapi_ner)
    trapi_ner = NER.TRAPI_NER(synonymizer_dir=out_dir_str, synonymizer_dbname=synonymizer_dbname,
                              linker_name=['go'], spacy_model='en_core_sci_lg', threshold=0.70,
                              num_neighbors=15, max_entities_per_mention=1)
    ners.append(trapi_ner)
    trapi_ner = NER.TRAPI_NER(synonymizer_dir=out_dir_str, synonymizer_dbname=synonymizer_dbname,
                              linker_name=['hpo'], spacy_model='en_core_sci_lg', threshold=0.70,
                              num_neighbors=15, max_entities_per_mention=1)
    ners.append(trapi_ner)

    # After running download_data.sh, the data will be in the data/ directory
    # convert the xml to dicts
    doc = get_xml_data(out_dir_str)
    kg2_drug_info = process_drug_bank_xmldict_data(doc, synonymizer_dbname)

    print("Number of drugs with info:", len(kg2_drug_info))

    # So now we have the KG2 identifiers for the drugs, as well as the category, name, and drugbank id
    # Now, I would like to NER the indications to add to an "indication" field in the kg2_drug_info dictionary.
    # While I am at it, also add the intermediate mechanistic nodes to the kg2_drug_info dictionary
    i = 0
    max_i = len(kg2_drug_info.keys())
    for kg2_drug in kg2_drug_info.keys():
        # if i % 100 == 0:
        print(f"Processing drug {i} of {max_i}")
        i += 1
        # NER and KG2 align the indications
        if kg2_drug_info[kg2_drug].get("indication"):
            kg2_drug_info[kg2_drug]["indication_NER_aligned"] = text_to_kg2_nodes(
                ners,
                remove_brackets(kg2_drug_info[kg2_drug]["indication"]), categories=['biolink:Disease',
                                                                                    'biolink:PhenotypicFeature',
                                                                                    'biolink:DiseaseOrPhenotypicFeature'])
        else:
            kg2_drug_info[kg2_drug]["indication_NER_aligned"] = {}
        # NER and KG2 align the mechanistic intermediate nodes from the text fields
        all_intermediate_text = ""
        for field in MOSTLY_TEXT_FIELDS:
            text = kg2_drug_info[kg2_drug].get(field)
            if text:
                all_intermediate_text += remove_brackets(text) + "\n "
        # then do the NER
        kg2_drug_info[kg2_drug]["mechanistic_intermediate_nodes"] = text_to_kg2_nodes(ners, all_intermediate_text,
                                                                                      categories=MECHANISTIC_CATEGORIES)

    # Now, let's write this to a JSON file
    with open(f'{out_dir_str}/kg2_drug_info.json', 'w') as f:
        json.dump(kg2_drug_info, f, indent=4)

    # also save as a pickle file for fast loading
    with open(f'{out_dir_str}/kg2_drug_info.pkl', 'wb') as f:
        pickle.dump(kg2_drug_info, f)


if __name__ == "__main__":
    main()
