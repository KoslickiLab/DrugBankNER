# Chunyu's utils for the TRAPI_NER project
## Import libraries
import sys
import logging
import xmltodict
import re
from CONSTANTS import DB_PREFIX
from node_synonymizer import NodeSynonymizer
from typing import Literal


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
    TODO: depreciate this
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
    TODO: depreciate this
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
    """
    TODO: depreciate this
    :param doc:
    :param fields:
    :return:
    """
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
    TODO: depreciate this
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
    return kg2_drug_info




def crawl_drugbank_bioentities(entry, field: Literal['transporters', 'enzymes', 'targets', 'carriers']):
    """
    This function crawls through the drugbank xml entry and extracts the names and ids of the bioentities in the
    specified field
    :param entry: dict
    :param field: str
    """
    field_singular = field[:-1]
    names = []
    ids = []
    if entry.get(field):
        entry_dict_or_list = entry[field][field_singular]
        if entry_dict_or_list:
            if isinstance(entry_dict_or_list, dict):
                names.append(entry_dict_or_list['name'])
                ids.append(entry_dict_or_list['id'])
                if 'polypeptide' in entry_dict_or_list:
                    if isinstance(entry_dict_or_list['polypeptide'], dict):
                        names.append(entry_dict_or_list['polypeptide']['name'])
                        names.append(entry_dict_or_list['polypeptide']['gene-name'])
                        ids.append(entry_dict_or_list['polypeptide']['@id'])
                    elif isinstance(entry_dict_or_list['polypeptide'], list):
                        for polypeptide in entry_dict_or_list['polypeptide']:
                            names.append(polypeptide['name'])
                            names.append(polypeptide['gene-name'])
                            ids.append(polypeptide['@id'])
            elif isinstance(entry_dict_or_list, list):
                for sub_entry in entry_dict_or_list:
                    names.append(sub_entry['name'])
                    ids.append(sub_entry['id'])
                    if 'polypeptide' in sub_entry:
                        if isinstance(sub_entry['polypeptide'], dict):
                            names.append(sub_entry['polypeptide']['name'])
                            names.append(sub_entry['polypeptide']['gene-name'])
                            ids.append(sub_entry['polypeptide']['@id'])
                        elif isinstance(sub_entry['polypeptide'], list):
                            for polypeptide in sub_entry['polypeptide']:
                                names.append(polypeptide['name'])
                                names.append(polypeptide['gene-name'])
                                ids.append(polypeptide['@id'])
    return names, ids


def crawl_drugbank_pathway(entry):
    pathway_dict_or_list = entry.get('pathways')
    pathway_ids = []
    pathway_enzymes = []
    if isinstance(pathway_dict_or_list, dict):
        if isinstance(pathway_dict_or_list.get('pathway'), dict):
            pathway_ids.append('SMPDB:' + pathway_dict_or_list.get('pathway').get('smpdb-id'))
            if pathway_dict_or_list.get('pathway').get('enzymes'):
                if pathway_dict_or_list.get('pathway').get('enzymes').get('uniprot-id'):
                    pathway_enzymes.extend(pathway_dict_or_list.get('pathway').get('enzymes').get('uniprot-id'))
        elif isinstance(pathway_dict_or_list.get('pathway'), list):
            for pathway in pathway_dict_or_list.get('pathway'):
                pathway_ids.append('SMPDB:' + pathway.get('smpdb-id'))
                if pathway.get('enzymes'):
                    if pathway.get('enzymes').get('uniprot-id'):
                        pathway_enzymes.extend(pathway.get('enzymes').get('uniprot-id'))
    elif isinstance(pathway_dict_or_list, list):
        for pathway in pathway_dict_or_list:
            if isinstance(pathway.get('pathway'), dict):
                pathway_ids.append('SMPDB:' + pathway.get('pathway').get('smpdb-id'))
                if pathway.get('pathway').get('enzymes'):
                    if pathway.get('pathway').get('enzymes').get('uniprot-id'):
                        pathway_enzymes.extend(pathway.get('pathway').get('enzymes').get('uniprot-id'))
            elif isinstance(pathway.get('pathway'), list):
                for p in pathway.get('pathway'):
                    pathway_ids.append('SMPDB:' + p.get('smpdb-id'))
                    if p.get('enzymes'):
                        if p.get('enzymes').get('uniprot-id'):
                            pathway_enzymes.extend(p.get('enzymes').get('uniprot-id'))
    # Tack on the UniProtKB: prefix
    pathway_enzymes = ['UniProtKB:' + x for x in pathway_enzymes]
    return pathway_ids, pathway_enzymes



def drug_bank_id_to_kg2_info(drug_bank_id):
    kg2_drug_info = {}
    query_CURIE = DB_PREFIX + drug_bank_id
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
            kg2_drug_info[identifier]["drug_bank_id"] = drug_bank_id
    return kg2_drug_info