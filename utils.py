# Chunyu's utils for the TRAPI_NER project
## Import libraries
import sys
import logging
import xmltodict
import re
from CONSTANTS import DB_PREFIX
from node_synonymizer import NodeSynonymizer


# Directly use the node synonymizer
synonymizer = NodeSynonymizer("./data", "node_synonymizer_v1.0_KG2.8.4.sqlite")


def get_logger(level: str = logging.INFO):
    """
    Setup a logger object
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s  [%(levelname)s]  %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def get_xml_data():
    with open('./data/full_database.xml', 'r', encoding='utf-8') as fd:
        doc = xmltodict.parse(fd.read())
    return doc


def extract_text(value):
    """
    Traverses a nested dictionary/list-of*-lists and extracts all the text values
    :param value:
    :return: big-ol-string
    """
    if isinstance(value, list):
        res = ' '.join(extract_text(v) for v in value)
    elif isinstance(value, dict):
        res = ' '.join(extract_text(v) for k, v in value.items() if not k.startswith('@'))
    else:
        res = str(value)
    if res != 'None':
        return res
    else:
        return ''


def process_drug(drug, fields):
    """
    Processes a drug from the drugbank xml file, extracting text from the fields we are interested in
    :param drug: xmltodict drug object
    :param fields: list of strings
    :return: dictionary
    """
    #fields = ['description', 'indication', 'pharmacodynamics', 'mechanism-of-action',
    #          'metabolism', 'protein-binding', 'pathways', 'reactions', 'targets',
    #          'enzymes', 'carriers', 'transporters']  # From what I can see, these are the most relevant to us
    #fields = ['description', 'indication', 'pharmacodynamics', 'mechanism-of-action',
    #          'metabolism', 'protein-binding', 'reactions',
    #          'enzymes', 'carriers', 'transporters']
    drug_data = {}
    for field in fields:
        value = drug.get(field, '')
        text = extract_text(value)
        # remove anything within brackets from the text (these are all references in the drugbank data)
        text = re.sub(r'\[.*?\]', '', text)
        drug_data[field] = text
    return drug_data


def process_drugbank_data(doc, fields):
    drugs = doc['drugbank']['drug']
    drug_dict = {}
    for drug in drugs:
        # This handles the case where there are multiple drugbank-ids and chooses the primary one
        drug_ids = drug['drugbank-id']
        try:
            primary_id = [d['#text'] for d in drug_ids if isinstance(d, dict) and d.get('@primary', '') == 'true'][0]
        except IndexError:
            primary_id = drug_ids['#text'] if isinstance(drug_ids, dict) and drug_ids.get('@primary', '') == 'true' else ''
        if primary_id:
            drug_info = process_drug(drug, fields)
            # check if some field is not empty
            if any(drug_info.values()):
                drug_dict[primary_id] = drug_info
    return drug_dict


def delete_long_tokens(text, max_length=100):
    """
    This function deletes tokens that are longer than 100 characters
    :param text: str
    :return: str
    """
    tokens = text.split(" ")
    return ' '.join([token for token in tokens if len(token) < max_length])


def get_preferred_name(curie):
    results = synonymizer.get_canonical_curies(curies=curie)
    return results[curie]['preferred_name']


def drug_dict_to_kg2_drug_info(drug_dict):
    """
    Take the output of process_drug_bank_data and create a dictionary keyed by KG2 notes, with values being the
    different fields from DrugBank with their associated text
    :param drug_dict:
    :return:
    """
    kg2_drug_info = {}
    # convert all the drugbank IDs to KG2 IDs
    i = 0
    max_i = len(drug_dict.keys())
    for drug in drug_dict.keys():
        if i % 100 == 0:
            print(f"Processing drug {i} of {max_i}")
        i += 1
        query_CURIE = DB_PREFIX + drug
        norm_results = synonymizer.get_canonical_curies(query_CURIE)
        if norm_results[query_CURIE]:
            identifier = norm_results[query_CURIE]['preferred_curie']
            name = norm_results[query_CURIE]['preferred_name']
            category = norm_results[query_CURIE]['preferred_category']
            if identifier:
                kg2_drug_info[identifier] = {}
                kg2_drug_info[identifier]['KG2_ID'] = identifier
                if name:
                    kg2_drug_info[identifier]['name'] = get_preferred_name(identifier)
                if category:
                    kg2_drug_info[identifier]['category'] = category
                kg2_drug_info[identifier]["drug_bank_id"] = drug