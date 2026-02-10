# DrugBankNER

ETL pipeline for processing DrugBank data and aligning entities and identifiers with RTX-KG2 concepts.
The resulting output is intended for use as training or evaluation data in downstream knowledge graph tasks.

---

## Prep Work

### 1. Download DrugBank XML

1. Create an account at https://go.drugbank.com
2. Run:
   ```bash
   ./download_data.sh
   ```
   This will place the DrugBank XML file in the `data/` directory.

---

### 2. Obtain the RTX / ARAX Node Synonymizer

You will need a compatible node synonymizer SQLite database for the KG version you are using.

- **Recommended**: Ask a team member for a local copy of the node synonymizer database  
  (this is useful if you do not have access to the RTX database server).

- **Alternative**: Request access to the RTX database server (`arax-databases.rtx.ai`).  
  If access is granted, the scripts will automatically download the appropriate node synonymizer database when it is not found locally.

> ⚠️ The node synonymizer version must match the KG version passed via `--kg-version`.  
> The scripts first check for a local database and only attempt a download if it is not already available.

---

### 3. Environment Setup

Create and activate a conda environment:

```bash
conda create --name drugbank_ner python=3.11.10
conda activate drugbank_ner
```

Install required packages:

```bash
pip install xmltodict==0.14.2
pip install pandas==2.2.3
pip install spacy==3.8.2
pip install scispacy==0.5.5
```

#### Optional: GPU support

Check your CUDA version:

```bash
nvidia-smi
```

Then install the matching CuPy package:

```bash
pip install cupy-cuda<your_cuda_version>x
```

---

### 4. Install ScispaCy Models

```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_lg-0.5.3.tar.gz
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_scibert-0.5.3.tar.gz
```

---

## Running the Tool

> **Important**  
> As of the latest refactor, all scripts require the `--kg-version` argument.  
> This ensures that downloaded databases and alignment logic are consistent with the intended knowledge graph version.

---

### 1. Perform Named Entity Recognition

Run `perform_NER.py` to perform named entity recognition and concept alignment on DrugBank text fields.

```bash
python perform_NER.py --kg-version 2.10.2
```

#### Optional arguments

```text
--db-host        Database file host (default: arax-databases.rtx.ai)
--db-username    Database file username (default: rtxconfig)
--db-port        Database file port (default: 22)
--ssh-key        Path to SSH private key (optional; uses SSH agent if omitted)
--ssh-password   SSH password (optional; prefer key or agent; can also set SSH_PASSWORD env var)
--out-dir        Output directory for downloaded database files (default: ./data)
```

Example:

```bash
python perform_NER.py \
  --kg-version 2.10.2 \
  --out-dir ./data \
  --ssh-key ~/.ssh/id_rsa
```

---

### 2. Extract and Align Identifiers

Run `look_for_identifiers.py` to extract, synonymize, and align DrugBank identifiers with RTX-KG2.

```bash
python look_for_identifiers.py --kg-version 2.10.2
```

This script supports the same optional connection and output arguments as `perform_NER.py`.

---

## Output

After successfully running both scripts, the final aligned output will be written to:

```text
./data/DrugBank_aligned_with_KG2.json
```

---

## Notes

- The `--kg-version` argument must follow the format `X.Y.Z` (e.g. `2.10.2`)
- Ensure all downloaded database artifacts correspond to the specified KG version
- SSH key–based authentication is strongly recommended over password-based access
