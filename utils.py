# Chunyu's utils for the TRAPI_NER project
## Import libraries
import sys
import logging
import xmltodict
import re
from CONSTANTS import DB_PREFIX
from node_synonymizer import NodeSynonymizer
from typing import Literal


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


def get_xml_data(out_dir_str):
    with open(f'{out_dir_str}/full database.xml', 'r', encoding='utf-8') as fd:
        doc = xmltodict.parse(fd.read())
    return doc


def delete_long_tokens(text, max_length=100):
    """
    This function deletes tokens that are longer than 100 characters
    :param text: str
    :return: str
    """
    tokens = text.split(" ")
    return ' '.join([token for token in tokens if len(token) < max_length])


def get_preferred_name(curie, out_dir_str, synonymizer_dbname):
    synonymizer = NodeSynonymizer(out_dir_str, synonymizer_dbname)
    results = synonymizer.get_canonical_curies(curies=curie)
    return results[curie]['preferred_name']


def remove_brackets(text):
    """
    This function removes brackets and their contents from the text
    :param text: str
    :return: str
    """
    return re.sub(r'\[.*?\]', '', text)


def process_drug_bank_xmldict_data(doc, out_dir_str, synonymizer_dbname):
    """
    This function processes the drugbank xml data and extracts the relevant information
    :param doc: doc = get_xml_data()
    :param out_dir_str: string
    :param synonymizer_dbname: string
    :return: dict
    """
    extracted_data = dict()
    for entry in doc['drugbank']['drug']:
        drug_dict = process_drugbank_doc_entry(entry, out_dir_str, synonymizer_dbname)
        if drug_dict:
            extracted_data.update(drug_dict)
    return extracted_data


def process_drugbank_doc_entry(entry, out_dir_str, synonymizer_dbname):
    """
    This function processes a drugbank entry and extracts the relevant information
    :param entry: dict
    :param out_dir_str: string
    :param synonymizer_dbname: string
    :return: dict
    """
    drugbank_drug_id = None
    if isinstance(entry.get('drugbank-id'), dict):
        drugbank_drug_id = entry.get('drugbank-id').get('#text')
    elif isinstance(entry.get('drugbank-id'), list):
        drugbank_drug_id = entry.get('drugbank-id')[0]['#text']
    if drugbank_drug_id:
        kg2_drug_info = drug_bank_id_to_kg2_info(drugbank_drug_id, out_dir_str, synonymizer_dbname)
    else:
        return None
    if kg2_drug_info:
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
            # deduplicate all the *_names and *_ids lists
            transporters_names = list(set(transporters_names))
            transporters_ids = list(set(transporters_ids))
            enzymes_names = list(set(enzymes_names))
            enzymes_ids = list(set(enzymes_ids))
            targets_names = list(set(targets_names))
            targets_ids = list(set(targets_ids))
            carriers_names = list(set(carriers_names))
            carriers_ids = list(set(carriers_ids))
            pathway_ids = list(set(pathway_ids))
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
    else:
        return None


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


def drug_bank_id_to_kg2_info(drug_bank_id, out_dir_str, synonymizer_dbname):
    kg2_drug_info = {}
    query_CURIE = DB_PREFIX + drug_bank_id
    synonymizer = NodeSynonymizer(out_dir_str, synonymizer_dbname)
    norm_results = synonymizer.get_canonical_curies(query_CURIE)
    if norm_results[query_CURIE]:
        identifier = norm_results[query_CURIE]['preferred_curie']
        name = norm_results[query_CURIE]['preferred_name']
        category = norm_results[query_CURIE]['preferred_category']
        if identifier:
            kg2_drug_info[identifier] = {}
            kg2_drug_info[identifier]['KG2_ID'] = identifier
            if name:
                kg2_drug_info[identifier]['name'] = get_preferred_name(identifier, out_dir_str, synonymizer_dbname)
            if category:
                kg2_drug_info[identifier]['category'] = category
            kg2_drug_info[identifier]["drug_bank_id"] = drug_bank_id
    return kg2_drug_info
