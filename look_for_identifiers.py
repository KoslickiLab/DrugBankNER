# I'll go through the various fields of the xml file, looking for identifiers in the text. I'll then use the
# synonymizer to get the preferred CURIE for each identifier and save the results to a json & pkl file.
import xmltodict
import json
import pickle
import pandas as pd
from node_synonymizer import NodeSynonymizer
import re
from utils import extract_text, process_drug, get_xml_data, process_drugbank_data, drug_dict_to_kg2_drug_info, \
    crawl_drugbank_bioentities, crawl_drugbank_pathway, drug_bank_id_to_kg2_info
from CONSTANTS import MECHANISTIC_CATEGORIES, DB_PREFIX, MOSTLY_TEXT_FIELDS, ALL_FIELDS, DATABASE_PREFIXES, \
    DATABASE_NAMES, REGEX_PATTERNS
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
            curie = DATABASE_PREFIXES[key] + ":" + f
            syn_result = synonymizer.get_canonical_curies(curie)
            if syn_result[curie]:
                preferred_name = syn_result[curie]['preferred_name']
                category = syn_result[curie]['preferred_category']
                preferred_curie = syn_result[curie]['preferred_curie']
                res.append({'curie': preferred_curie, 'preferred_name': preferred_name, 'preferred_category': category})
    return res

synonymizer = NodeSynonymizer()

doc = get_xml_data()
entry = doc['drugbank']['drug'][0]

def process_drugbank_doc_entry(entry):
    """
    This function processes a drugbank entry and extracts the relevant information
    :param entry: dict
    :return: dict
    """
    drugbank_drug_id = entry.get('drugbank-id')[0]['#text']
    kg2_drug_info = drug_bank_id_to_kg2_info(drugbank_drug_id)
    kg2_id = list(kg2_drug_info.keys())[0]
    if kg2_id:
        description_text = entry.get('description')
        indication_text = entry.get('indication')
        pharmacodynamics_text = entry.get('pharmacodynamics')
        mechanism_of_action_text = entry.get('mechanism-of-action')
        metabolism_text = entry.get('metabolism')
        transporters_names, transporters_ids = crawl_drugbank_bioentities(entry, 'transporters')
        enzymes_names, enzymes_ids = crawl_drugbank_bioentities(entry, 'enzymes')
        targets_names, targets_ids = crawl_drugbank_bioentities(entry, 'targets')
        carriers_names, carriers_ids = crawl_drugbank_bioentities(entry, 'carriers')
        pathway_ids, pathway_enzymes = crawl_drugbank_pathway(entry)
        kg2_drug_info[kg2_id]['description'] = description_text
        kg2_drug_info[kg2_id]['indication'] = indication_text
        kg2_drug_info[kg2_id]['pharmacodynamics'] = pharmacodynamics_text
        kg2_drug_info[kg2_id]['mechanism_of_action'] = mechanism_of_action_text
        kg2_drug_info[kg2_id]['metabolism'] = metabolism_text
        kg2_drug_info[kg2_id]['transporters'] = {'names': transporters_names, 'ids': transporters_ids}
        kg2_drug_info[kg2_id]['enzymes'] = {'names': enzymes_names, 'ids': enzymes_ids}
        kg2_drug_info[kg2_id]['targets'] = {'names': targets_names, 'ids': targets_ids}
        kg2_drug_info[kg2_id]['carriers'] = {'names': carriers_names, 'ids': carriers_ids}
        kg2_drug_info[kg2_id]['pathways'] = {'ids': pathway_ids, 'enzymes': {'ids': pathway_enzymes}}
        return kg2_drug_info
    else:
        return None

print(json.dumps(process_drugbank_doc_entry(entry), indent=4))
