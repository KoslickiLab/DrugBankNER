import argparse
import os
import re
from pathlib import Path

import NER
import json
import spacy
import pickle

from download_script import ensure_downloaded_and_verified
from parser import get_parser
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


def main():
    args = get_parser().parse_args()

    kg_version = args.kg_version
    synonymizer_dbname = f'node_synonymizer_v1.0_KG{kg_version}.sqlite'
    out_dir_str = args.out_dir
    out_dir = Path(out_dir_str)
    remote_path_synonymizer_db = f"~/KG{kg_version}/{synonymizer_dbname}"
    local_path_synonymizer_db = out_dir / synonymizer_dbname

    ensure_downloaded_and_verified(
        host=args.db_host,
        username=args.db_username,
        port=args.db_port,
        remote_path=remote_path_synonymizer_db,
        local_path=local_path_synonymizer_db,
        key_path=args.ssh_key,
        password=args.ssh_password or os.getenv("SSH_PASSWORD"),
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
