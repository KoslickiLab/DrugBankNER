# Chunyu's utils for the TRAPI_NER project
## Import libraries
import sys
import logging
import xmltodict
import re

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