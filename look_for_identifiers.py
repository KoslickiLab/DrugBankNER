# I'll go through the various fields of the xml file, looking for identifiers in the text. I'll then use the
# synonymizer to get the preferred CURIE for each identifier and save the results to a json & pkl file.
import xmltodict
import json
import pickle
import pandas as pd
from node_synonymizer import NodeSynonymizer
import re
from utils import get_xml_data, process_drug_bank_xmldict_data
from CONSTANTS import MECHANISTIC_CATEGORIES, DB_PREFIX, MOSTLY_TEXT_FIELDS, ALL_FIELDS, DATABASE_PREFIXES, \
    DATABASE_NAMES, REGEX_PATTERNS, IDENTIFIER_FIELDS
from typing import Literal, Union, List, Dict, Any


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

synonymizer = NodeSynonymizer()

# doc = get_xml_data()
# kg2_drug_info = process_drug_bank_xmldict_data(doc)
# Just read in the pkl file: ./data/kg2_drug_info.pkl
with open('./data/kg2_drug_info.pkl', 'rb') as f:
    kg2_drug_info = pickle.load(f)

# Go through each drug, use the names to find KG2 nodes, and then use the identifiers to find the preferred curies
# add each to the mechanistic_intermediate_nodes field
for drug in kg2_drug_info.keys():
    for field in IDENTIFIER_FIELDS:
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
                        kg2_drug_info[drug]['mechanistic_intermediate_nodes'].update({preferred_curie: {'name': preferred_name,
                                                                                                         'category': preferred_category}})
                        print(f"Added: {preferred_name}")
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
                                kg2_drug_info[drug]['mechanistic_intermediate_nodes'].update({preferred_curie: {'name': preferred_name,
                                                                                                                 'category': preferred_category}})
                                print(f"Added: {preferred_name}")

print(len(kg2_drug_info[drug]['mechanistic_intermediate_nodes']))
# Let's check to see what all the identifiers could look like. I am getting a bunch of off-target matches since the
# suffix can match with multiple prefixes, leading to things like "Q8TCC7" mapping to SLC22A8 (correct) and (+)-8-Hydroxycalamenene