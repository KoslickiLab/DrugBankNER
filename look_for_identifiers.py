# I'll go through the various fields of the xml file, looking for identifiers in the text. I'll then use the
# synonymizer to get the preferred CURIE for each identifier and save the results to a json & pkl file.
import xmltodict
import json
import pickle
import pandas as pd
from node_synonymizer import NodeSynonymizer
