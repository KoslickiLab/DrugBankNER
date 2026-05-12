# # I'll go through the various fields of the xml file, looking for identifiers in the text. I'll then use the
# # synonymizer to get the preferred CURIE for each identifier and save the results to a json & pkl file.
# import argparse
# import os
# from pathlib import Path
#
# import xmltodict
# import json
# import pickle
#
# from node_synonymizer import NodeSynonymizer
# import re
#
# from CONSTANTS import DATABASE_PREFIXES, REGEX_PATTERNS, IDENTIFIER_FIELDS
# from CachedNodeSynonymizer import CachedNodeSynonymizer
#
#
# def find_curies_with_prefix(text):
#     """
#     This function finds all the curies in the text using the regex patterns in REGEX_PATTERNS and returns a list of
#     dictionaries with the curie, preferred name, and the category of the curie
#     :param text: str
#     :return: list of dictionaries
#     """
#     res = []
#     for key, pattern in REGEX_PATTERNS.items():
#         found = re.compile(pattern).findall(text)
#         for f in found:
#             curie = DATABASE_PREFIXES[key] + ":" + text  # the regex can get partial matches, so I'll add the prefix
#             # to the full input (not the matched portion)
#             syn_result = synonymizer.get_canonical_curies(curie)
#             if syn_result[curie]:
#                 preferred_name = syn_result[curie]['preferred_name']
#                 category = syn_result[curie]['preferred_category']
#                 preferred_curie = syn_result[curie]['preferred_curie']
#                 res.append({'preferred_curie': preferred_curie, 'preferred_name': preferred_name, 'preferred_category': category})
#     return res
#
# if __name__ == "__main__":
#
#     base_syn = NodeSynonymizer()
#     synonymizer = CachedNodeSynonymizer(base_syn)
#
#     # doc = get_xml_data()
#     # kg2_drug_info = process_drug_bank_xmldict_data(doc, out_dir_str, synonymizer_dbname)
#     # Just read in the pkl file: ./data/kg2_drug_info.pkl
#     with open(f'data/kg2_drug_info.pkl', 'rb') as f:
#         kg2_drug_info = pickle.load(f)
#
#     # Go through each drug, use the names to find KG2 nodes, and then use the identifiers to find the preferred curies
#     # add each to the mechanistic_intermediate_nodes field
#     i = 0
#     for drug in kg2_drug_info.keys():
#         print(f"Processing drug {i} of {len(kg2_drug_info.keys())}")
#         i += 1
#         for field in IDENTIFIER_FIELDS:
#             # Align the names to KG2
#             names = []
#             if kg2_drug_info[drug].get(field):
#                 names = kg2_drug_info[drug].get(field).get('names')
#             if names:
#                 res = synonymizer.get_canonical_curies(names=names)
#                 for key, value in res.items():
#                     if value:
#                         preferred_name = value['preferred_name']
#                         preferred_curie = value['preferred_curie']
#                         preferred_category = value['preferred_category']
#                         if preferred_curie not in kg2_drug_info[drug]['mechanistic_intermediate_nodes']:
#                             kg2_drug_info[drug]['mechanistic_intermediate_nodes'].update(
#                                 {preferred_curie: {'name': preferred_name,
#                                                    'category': preferred_category}})
#             # Align the IDs to KG2
#             ids = []
#             if kg2_drug_info[drug].get(field):
#                 ids = kg2_drug_info[drug].get(field).get('ids')
#                 if ids:
#                     for id in ids:
#                         if ":" not in id:  # That means I'm dealing with a suffix
#                             results = find_curies_with_prefix(id)
#                             for res in results:
#                                 preferred_name = res['preferred_name']
#                                 preferred_curie = res['preferred_curie']
#                                 preferred_category = res['preferred_category']
#                                 if preferred_curie not in kg2_drug_info[drug]['mechanistic_intermediate_nodes']:
#                                     kg2_drug_info[drug]['mechanistic_intermediate_nodes'].update(
#                                         {preferred_curie: {'name': preferred_name,
#                                                            'category': preferred_category}})
#
#     # Now, let's write this to a JSON file
#     with open(f'data/DrugBank_aligned_with_KG2.json', 'w') as f:
#         json.dump(kg2_drug_info, f, indent=2)
#     # Also dump to a pickle file
#     with open(f'data/DrugBank_aligned_with_KG2.pkl', 'wb') as f:
#         pickle.dump(kg2_drug_info, f)
#
#     synonymizer.save_cache()


import argparse
import os
from pathlib import Path
import xmltodict
import json
import pickle
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from node_synonymizer import NodeSynonymizer
from CONSTANTS import DATABASE_PREFIXES, REGEX_PATTERNS, IDENTIFIER_FIELDS
from CachedNodeSynonymizer import CachedNodeSynonymizer


def find_curies_with_prefix(text, syn_instance):
    """
    This function finds all the curies in the text using the regex patterns in REGEX_PATTERNS and returns a list of
    dictionaries with the curie, preferred name, and the category of the curie
    :param text: str
    :param syn_instance: CachedNodeSynonymizer object
    :return: list of dictionaries
    """
    res = []
    for key, pattern in REGEX_PATTERNS.items():
        found = re.compile(pattern).findall(text)
        for f in found:
            curie = DATABASE_PREFIXES[key] + ":" + text  # adding the prefix to the full input
            syn_result = syn_instance.get_canonical_curies(curie)

            if syn_result and syn_result.get(curie):
                preferred_name = syn_result[curie]['preferred_name']
                category = syn_result[curie]['preferred_category']
                preferred_curie = syn_result[curie]['preferred_curie']
                res.append({
                    'preferred_curie': preferred_curie,
                    'preferred_name': preferred_name,
                    'preferred_category': category
                })
    return res


def process_drug(drug_id, drug_data, syn_instance):
    """
    Worker function to process a single drug's fields and query the synonymizer.
    Returns the drug_id and a dictionary of new mechanistic nodes to append.
    """
    new_nodes = {}

    for field in IDENTIFIER_FIELDS:
        field_data = drug_data.get(field)
        if not field_data:
            continue

        # Align the names to KG2
        names = field_data.get('names')
        if names:
            res = syn_instance.get_canonical_curies(names=names)
            for key, value in res.items():
                if value:
                    new_nodes[value['preferred_curie']] = {
                        'name': value['preferred_name'],
                        'category': value['preferred_category']
                    }

        # Align the IDs to KG2
        ids = field_data.get('ids')
        if ids:
            for id_val in ids:
                if ":" not in id_val:  # That means I'm dealing with a suffix
                    results = find_curies_with_prefix(id_val, syn_instance)
                    for res_item in results:
                        new_nodes[res_item['preferred_curie']] = {
                            'name': res_item['preferred_name'],
                            'category': res_item['preferred_category']
                        }

    return drug_id, new_nodes


if __name__ == "__main__":

    base_syn = NodeSynonymizer()
    synonymizer = CachedNodeSynonymizer(base_syn)

    with open('data/kg2_drug_info.pkl', 'rb') as f:
        kg2_drug_info = pickle.load(f)

    total_drugs = len(kg2_drug_info)
    print(f"Starting processing of {total_drugs} drugs in parallel...")

    # Set up multithreading
    # Adjust max_workers based on your machine's capabilities or the database's connection limits
    MAX_WORKERS = 10

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks to the thread pool
        futures = {
            executor.submit(process_drug, drug, data, synonymizer): drug
            for drug, data in kg2_drug_info.items()
        }

        # Process results as they complete
        completed_count = 0
        for future in as_completed(futures):
            drug_id, new_mechanistic_nodes = future.result()

            # Ensure the key exists before updating
            if 'mechanistic_intermediate_nodes' not in kg2_drug_info[drug_id]:
                kg2_drug_info[drug_id]['mechanistic_intermediate_nodes'] = {}

            # Safely update the dictionary in the main thread
            kg2_drug_info[drug_id]['mechanistic_intermediate_nodes'].update(new_mechanistic_nodes)

            # Progress tracker
            completed_count += 1
            if completed_count % 50 == 0:
                print(f"Processed {completed_count} of {total_drugs} drugs")

    # Now, let's write this to a JSON file
    with open('data/DrugBank_aligned_with_KG2.json', 'w') as f:
        json.dump(kg2_drug_info, f, indent=2)

    # Also dump to a pickle file
    with open('data/DrugBank_aligned_with_KG2.pkl', 'wb') as f:
        pickle.dump(kg2_drug_info, f)

    synonymizer.save_cache()
    print("Processing complete! Data and cache saved.")