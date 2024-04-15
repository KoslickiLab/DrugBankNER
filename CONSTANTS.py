DB_PREFIX = 'DRUGBANK:'
MECHANISTIC_CATEGORIES = {"biolink:BiologicalProcess", "biolink:BiologicalProcessOrActivity",
"biolink:Cell", "biolink:CellularComponent", "biolink:Drug",
"biolink:Disease", "biolink:DiseaseOrPhenotypicFeature",
"biolink:Gene", "biolink:GeneProduct", "biolink:GeneFamily",
"biolink:GeneGroupingMixin", "biolink:GeneOrGeneProduct",
"biolink:MolecularActivity", "biolink:NoncodingRNAProduct",
"biolink:PathologicalProcess", "biolink:PhenotypicFeature",
"biolink:Pathway", "biolink:PhenotypicFeature", "biolink:Protein",
"biolink:ProteinDomain", "biolink:ProteinFamily",
"biolink:PhysiologicalProcess", "biolink:RNAProduct",
"biolink:SmallMolecule", "biolink:Transcript"}

MOSTLY_TEXT_FIELDS = ['description', 'indication', 'pharmacodynamics', 'mechanism-of-action',
              'metabolism', 'protein-binding']

ALL_FIELDS = ['description', 'indication', 'pharmacodynamics', 'mechanism-of-action',
              'metabolism', 'protein-binding', 'pathways', 'reactions', 'targets',
              'enzymes', 'carriers', 'transporters']

DESIRED_XML_FIELDS = ['description', 'indication', 'pharmacodynamics', 'mechanism-of-action']

DATABASE_NAMES = ['DrugBank', 'CAS', 'KEGG Compound', 'KEGG Drug', 'PubChem Compound', 'PubChem Substance',
                  'ChEBI', 'PharmGKB', 'HET', 'UniProt', 'GenBank', 'DPD', 'NDC', 'SMPDB', 'PR']

DATABASE_PREFIXES = {
    'DrugBank': 'DRUGBANK',
    'CAS': 'CAS',
    'KEGG Compound': 'KEGG.COMPOUND',
    'KEGG Drug': 'KEGG.DRUG',
    'PubChem Compound': 'PUBCHEM.COMPOUND',
    'PubChem Substance': 'PUBCHEM.SUBSTANCE',
    'ChEBI': 'CHEBI',
    'PharmGKB': 'PHARMGKB',
    'HET': '',
    'UniProt': 'UNIPROTKB',
    'GenBank': 'GENBANK',
    'DPD': '',
    'NDC': 'NDC',
    'SMPDB': 'SMPDB',
    'PR': 'PR'
}

REGEX_PATTERNS = {
    'DrugBank': r'DB\d+',
    'CAS': r'\d{2,7}-\d{2}-\d',
    'KEGG Compound': r'C\d{5}',
    'KEGG Drug': r'D\d{5}',
    'PubChem Compound': r'\d{4,9}',
    'PubChem Substance': r'\d{4,9}',
    'ChEBI': r'\d+',
    'PharmGKB': r'PA\d+',
    'HET': r'\w{3}',
    'UniProt': r'[OPQ][0-9][A-Z0-9]{3}[0-9]',
    'GenBank': r'\w{2}\d{6}',
    'DPD': r'\d+',
    'NDC': r'\d{4}-\d{4}-\d{2}',
    'SMPDB': r'SMP\d+',
    'PR': r'P:\d+'
}

# Got the following from:
# sql_query = "SELECT DISTINCT SUBSTR(id, 1, INSTR(id, ':') - 1) AS prefix FROM nodes WHERE id LIKE '%:%';"
# synonymizer_CURIES = synonymizer._execute_sql_query(sql_query)
# prefixes = [x[0] for x in synonymizer_CURIES]

ALL_PREFIXES = ['AEO', 'ARO', 'ATC', 'AraPort', 'BAO', 'BFO', 'BSPO', 'BTO', 'CARO', 'CAS', 'CEPH', 'CGNC', 'CHEBI',
                'CHEMBL.COMPOUND', 'CHEMBL.MECHANISM', 'CHEMBL.TARGET', 'CHMO', 'CL', 'CLO', 'CP', 'CVDO', 'DDANAT',
                'DGIdb', 'DOID', 'DRUGBANK', 'DisGeNET', 'DrugCentral', 'EC', 'ECO', 'ECOCORE', 'ECTO', 'EDAM', 'EFO',
                'EHDAA2', 'EMAPA', 'ENSEMBL', 'ENVO', 'EO', 'EPO', 'ERO', 'EnsemblGenomes', 'ExO', 'FAO', 'FB', 'FBbt',
                'FBdv', 'FBgn', 'FIX', 'FLU', 'FMA', 'FOODON', 'GAZ', 'GENEPIO', 'GENO', 'GEO', 'GO', 'GOREL', 'GTOPDB',
                'HANCESTRO', 'HCPCS', 'HGNC', 'HMDB', 'HP', 'IAO', 'ICD10', 'ICD10PCS', 'ICD9', 'ICO', 'IDO',
                'INCHIKEY', 'JensenLab', 'KEGG.COMPOUND', 'KEGG.DISEASE', 'KEGG.DRUG', 'KEGG.ENZYME', 'KEGG.GLYCAN',
                'KEGG.REACTION', 'KEGG', 'KEGG_source', 'MA', 'MAXO', 'MEDDRA', 'MESH', 'MF', 'MFOMD', 'MGI', 'MI',
                'MMO', 'MOD', 'MONDO', 'MP', 'MPATH', 'NBO', 'NCBIGene', 'NCBITaxon', 'NCIT', 'NCRO', 'NDDF', 'OAE',
                'OBA', 'OBAN', 'OBI', 'OBO', 'OGG', 'OGMS', 'OIO', 'OMIABIS', 'OMIM.PS', 'OMIM', 'OMIT', 'OMP', 'OMRSE',
                'OPL', 'ORPHANET', 'PATO', 'PCO', 'PDQ', 'PECO', 'PO', 'PR', 'PSY', 'PUBCHEM.COMPOUND', 'PW',
                'PathWhiz.Bound', 'PathWhiz.Compound', 'PathWhiz.ElementCollection', 'PathWhiz.NucleicAcid',
                'PathWhiz.ProteinComplex', 'PathWhiz.Reaction', 'PathWhiz', 'PomBase', 'REACT', 'REPODB', 'RGD',
                'RHEA', 'RO', 'RTX', 'RXNORM', 'SEMMEDDB', 'SGD', 'SIO', 'SMPDB', 'SNOMED', 'SNOMEDCT', 'SO', 'STATO',
                'STY', 'SYMP', 'TCDB', 'TO', 'TRANS', 'TypOn', 'UBERON', 'UBERON_CORE', 'UBPROP', 'UMLS',
                'UNICHEM_source', 'UNII', 'UO', 'UPHENO', 'UniProtKB', 'VCARD', 'VT', 'WBbt', 'WBls', 'WormBase', 'XCO',
                'ZEA', 'ZFA', 'ZFIN', 'biolink', 'biolink_download_source', 'dbpedia', 'dc', 'dct', 'dictyBase',
                'dictybase.gene', 'doap', 'ecogene', 'foaf', 'identifiers_org_registry', 'linkml', 'medgen', 'miRBase',
                'owl', 'rdf', 'rdfs', 'skos', 'ttd.target', 'umls_source', 'wb']
