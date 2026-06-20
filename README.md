# Biomedical Entity Resolution Assistant

A Precision Medicine AI assistant for resolving **biomedical entities** (genes, diseases, and genomic variants) into **canonical standardized representations** using biomedical ontologies and trusted datasets.

---

# Overview

Biomedical datasets, literature, and clinical records often contain inconsistent naming conventions.

The same biomedical entity may appear under multiple aliases, abbreviations, shorthand notations, or historical names.

Examples:

| Input | Canonical Output | Type |
|------|------------------|------|
| HER1 | EGFR | Gene |
| ERBB1 | EGFR | Gene |
| p53 | TP53 | Gene |
| NSCLC | Non-Small Cell Lung Cancer | Disease |
| Ex19del | EGFR Exon 19 Deletion | Variant |

This project solves that problem by building an **Entity Resolution Assistant** that maps ambiguous biomedical terms into standardized canonical forms.

---

# Problem Statement

Biomedical AI systems struggle with:

- inconsistent terminology
- alias ambiguity
- abbreviation overload
- multiple ontology standards
- noisy human-entered data

Example:

Dataset A stores:

```text
HER1
```

Dataset B stores:

```text
EGFR
```

Dataset C stores:

```text
ERBB1
```

All refer to the same gene.

Without normalization:

- search quality decreases
- retrieval pipelines fail
- downstream AI assistants become unreliable
- clinical reasoning becomes inconsistent

This system acts as the **normalization layer** for the AI Precision Medicine Platform.

---

# Project Goal

The goal of this assistant is to answer one core question:

> **“What is this biomedical entity?”**

The assistant identifies and resolves:

- Gene aliases
- Disease aliases
- Variant aliases
- Standard biomedical identifiers

---

# Scope

## Included

### Gene Resolution
Examples:

- Is HER1 the same as EGFR?
- What is the canonical name for p53?
- Is ERBB1 an alias of EGFR?

Output:
- canonical gene symbol
- aliases
- identifier
- confidence score
- provenance

---

### Disease Resolution
Examples:

- What does NSCLC stand for?
- Resolve lung adenocarcinoma
- Is melanoma a disease entity?

Output:
- canonical disease name
- ontology ID
- synonyms
- confidence score

---

### Variant Resolution
Examples:

- What does Ex19del map to?
- Resolve G12C
- Resolve T790M

Output:
- canonical variant notation
- standardized representation
- variant identifiers
- confidence score

---

# Out of Scope

This project does **NOT** perform:

## Clinical Interpretation
Example:
- Is this mutation pathogenic?

## Therapeutic Recommendation
Example:
- Which drug targets EGFR?

## Prognostic Analysis
Example:
- Does this mutation worsen survival?

These belong to other projects in the AI Precision Medicine platform.

---

# Core Features

- Biomedical alias resolution
- Entity type detection
- Exact matching
- Fuzzy matching
- Confidence scoring
- Canonical entity mapping
- Provenance tracking
- REST API
- Evaluation pipeline
- Interactive UI

---

# System Architecture

```text
User Query
   ↓
Query Preprocessing
   ↓
Entity Detection
   ↓
Candidate Retrieval
   ↓
Matching Engine
   ↓
Confidence Scoring
   ↓
Canonical Resolution Response
```

---

## 1. Query Input

Example:

```text
Is HER1 the same as EGFR?
```

User input may be:

- raw biomedical text
- aliases
- abbreviations
- questions
- misspelled entities

---

## 2. Query Preprocessing

Normalize raw text.

Examples:

```text
HER-1 → HER1
her1 → HER1
HER 1 → HER1
```

Preprocessing includes:

- case normalization
- punctuation removal
- whitespace normalization
- token cleanup

---

## 3. Entity Detection

Determine whether input refers to:

- Gene
- Disease
- Variant

Examples:

| Input | Entity Type |
|------|-------------|
| EGFR | Gene |
| NSCLC | Disease |
| Ex19del | Variant |

---

## 4. Candidate Retrieval

Search internal knowledge base for possible matches.

Example:

Input:

```text
HER1
```

Candidates:

| Candidate | Type |
|-----------|------|
| EGFR | Gene |
| ERBB1 | Gene |

Methods:
- dictionary lookup
- index search
- vector search

---

## 5. Matching Engine

Compute similarity between query and candidates.

Matching methods:

### Exact Match
Highest confidence.

Example:

```text
EGFR == EGFR
```

---

### Alias Match
Known synonym mapping.

Example:

```text
HER1 → EGFR
```

---

### Fuzzy Match
Handles spelling variations.

Example:

```text
HER-1 ≈ HER1
```

---

### Semantic Match
Useful for longer disease names.

Example:

```text
non small cell lung cancer ≈ NSCLC
```

---

## 6. Confidence Scoring

Each prediction receives a confidence score.

Example:

```json
{
  "confidence": 0.98
}
```

Score interpretation:

| Score | Meaning |
|------|---------|
| 0.90–1.00 | Very High |
| 0.75–0.89 | High |
| 0.50–0.74 | Medium |
| <0.50 | Low |

---

## 7. Response Generation

Example output:

```json
{
  "query": "HER1",
  "canonical_name": "EGFR",
  "entity_type": "Gene",
  "identifier": "HGNC:3236",
  "confidence": 0.99,
  "source": "HGNC"
}
```

---

# Datasets

## 1. HGNC (Genes)

Official human gene naming authority.

Contains:
- approved gene symbols
- aliases
- previous names
- identifiers

Examples:

- EGFR
- TP53
- KRAS

Website:

https://www.genenames.org/

---

## 2. MONDO (Diseases)

Disease ontology database.

Contains:
- disease names
- synonyms
- ontology IDs
- relationships

Examples:
- NSCLC
- melanoma
- lung adenocarcinoma

Website:

https://mondo.monarchinitiative.org/

---

## 3. ClinVar (Variants)

Variant database.

Contains:
- genomic variants
- HGVS notation
- variant aliases
- submissions

Examples:
- Ex19del
- T790M
- G12C

Website:

https://www.ncbi.nlm.nih.gov/clinvar/

---

## 4. CIViC (Optional)

Clinical interpretation database.

Used mainly for validation and future integration.

Website:

https://civicdb.org/

---

# Tech Stack

| Layer | Tool |
|------|------|
| Language | Python |
| Backend API | FastAPI |
| UI | Streamlit |
| Matching | RapidFuzz |
| Vector DB | ChromaDB |
| NLP | spaCy |
| Data Processing | Pandas |
| Containerization | Docker |

---

# Repository Structure

```bash
biomedical-entity-resolution-assistant/
│
├── README.md
├── requirements.txt
├── Dockerfile
├── .env.example
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── ontology_mappings/
│
├── src/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── entity_detection/
│   ├── retrieval/
│   ├── matching/
│   ├── scoring/
│   ├── api/
│   └── utils/
│
├── tests/
├── docs/
├── notebooks/
└── ui/
```

---

# Installation

## Clone Repository

```bash
git clone <repo-url>
cd biomedical-entity-resolution-assistant
```

---

## Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Project

## Run API

```bash
uvicorn src.api.main:app --reload
```

API available at:

```text
http://localhost:8000
```

---

## Run UI

```bash
streamlit run ui/app.py
```

---

# API Example

## Request

```http
POST /resolve
```

Request body:

```json
{
  "query": "HER1"
}
```

---

## Response

```json
{
  "query": "HER1",
  "canonical_name": "EGFR",
  "entity_type": "Gene",
  "identifier": "HGNC:3236",
  "confidence": 0.99,
  "source": "HGNC"
}
```

---

# Evaluation Questions

## Gene Resolution

- Is HER1 the same as EGFR?
- What is the canonical name for p53?
- Is ERBB1 an alias of EGFR?

## Disease Resolution

- What does NSCLC stand for?
- Resolve lung adenocarcinoma
- Resolve melanoma

## Variant Resolution

- What does Ex19del map to?
- Resolve T790M
- Resolve G12C

---

# Evaluation Metrics

## Accuracy

Measures correct predictions.

Formula:

Accuracy = Correct Predictions / Total Predictions

---

## Precision

Measures correctness of predicted matches.

---

## Recall

Measures ability to recover true aliases.

---

## Latency

Measures response speed.

Target:

```text
< 2 seconds
```

---

# Development Roadmap

## Phase 1 — Core Resolver (MVP)
- repo setup
- dataset ingestion
- alias lookup
- exact matching

---

## Phase 2 — Enhanced Matching
- fuzzy search
- semantic similarity
- confidence scoring

---

## Phase 3 — Production Features
- API
- UI
- evaluation
- monitoring
- Docker deployment

---

# Future Improvements

- LLM-assisted disambiguation
- ontology graph traversal
- multi-entity extraction
- biomedical RAG integration
- knowledge graph support
- clinical workflow integration

---

# Role in AI Precision Medicine Platform

This project serves as a foundational service for:

- Variant Evidence Assistant
- Therapeutic Strategy Assistant
- Clinical Trial Matching Assistant
- Biomarker Assistant

It ensures all downstream systems operate on standardized biomedical entities.

---

# Author

**James**  
LLM Zoomcamp — AI Precision Medicine Platform

---

# License

MIT License
