import re
import sys
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.text_normalizer import clean_text

# Common English stopwords to ignore when they appear in completely lowercase form.
# This prevents clashing with capitalized gene names like WAS, FOR, OR, etc.
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadnt", "has", "hasnt", "have",
    "havent", "having", "he", "hed", "hell", "hes", "her", "here", "heres", "hers", "herself", "him",
    "himself", "his", "how", "hows", "i", "id", "ill", "im", "ive", "if", "in", "into", "is", "isnt",
    "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt", "so", "some",
    "such", "than", "that", "thats", "the", "their", "theirs", "them", "themselves", "then", "there",
    "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent",
    "what", "whats", "when", "whens", "where", "wheres", "which", "while", "who", "whos", "whom",
    "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve", "your",
    "yours", "yourself", "yourselves"
}

class BiomedicalNER:
    """
    Named Entity Recognition (NER) extractor for biomedical terms.
    Uses a hybrid approach:
    1. Regex-based detection for clinical acronyms and capitalized codes (e.g., TP53, MI, EGFR).
    2. High-performance dictionary matching (using a hash-set of normalized aliases
       from normalized_lookup.parquet).
    """
    def __init__(self):
        self.lookup_path = PROJECT_ROOT / "data" / "processed" / "normalized_lookup.parquet"
        self._aliases_set = None
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            import spacy
            import warnings
            # Suppress user/future warnings from older model configuration
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._nlp = spacy.load("en_core_sci_sm")
            print("[NER] Loaded SciSpacy model 'en_core_sci_sm'.")
        return self._nlp

    @property
    def aliases_set(self) -> set:
        if self._aliases_set is None:
            if not self.lookup_path.exists():
                print("[NER] Warning: normalized_lookup.parquet not found. Dictionary matching will be disabled.")
                self._aliases_set = set()
            else:
                # Load only the 'alias' column to save memory
                df = pd.read_parquet(self.lookup_path, columns=["alias"])
                self._aliases_set = set(df["alias"].dropna().unique())
                print(f"[NER] Loaded {len(self._aliases_set)} unique aliases for dictionary matching.")
        return self._aliases_set

    def extract_mentions(self, text: str) -> list[dict]:
        """
        Extracts biomedical mentions from free text.
        
        Returns:
            list[dict]: A list of dicts, each with keys:
                - 'mention': exact string in text
                - 'start_char': start offset
                - 'end_char': end offset
                - 'category': e.g., 'Acronym', 'DictionaryMatch'
        """
        if not text:
            return []

        extracted = []
        
        # 1. Extract Acronyms/Identifiers using Regex
        # Matches strings like: TP53, MI, EGFR, HER2, A1BG
        # Capitalized word optionally followed by digits/letters
        acronym_regex = re.compile(r'\b[A-Z]{2,8}(?:-\d+)?\b|\b[A-Z]+\d+[A-Z0-9]*\b')
        for match in acronym_regex.finditer(text):
            mention = match.group()
            extracted.append({
                "mention": mention,
                "start_char": match.start(),
                "end_char": match.end(),
                "category": "Acronym"
            })

        # 2. Extract using SciSpacy model
        try:
            doc = self.nlp(text)
            for ent in doc.ents:
                ent_text = ent.text.strip()
                if not ent_text:
                    continue
                # Skip common stopwords if the text in the source document is completely lowercase
                if ent_text.islower() and ent_text in STOPWORDS:
                    continue
                extracted.append({
                    "mention": ent_text,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                    "category": "SciSpacy"
                })
        except Exception as e:
            print(f"[NER] Warning: Failed to extract with SciSpacy: {e}")

        # 3. Extract N-grams that match the Dictionary
        # We check n-grams of length 1 to 5 words
        # To find start/end characters for n-grams, we tokenize and track start/end indices of each word.
        tokens = []
        token_regex = re.compile(r'\w+(?:-\w+)*')
        for match in token_regex.finditer(text):
            tokens.append({
                "word": match.group(),
                "start": match.start(),
                "end": match.end()
            })

        num_tokens = len(tokens)
        aliases = self.aliases_set
        
        if aliases:
            for n in range(1, 6): # n-grams of size 1 to 5
                for i in range(num_tokens - n + 1):
                    ngram_tokens = tokens[i : i + n]
                    ngram_text = text[ngram_tokens[0]["start"] : ngram_tokens[-1]["end"]]
                    
                    # Skip common stopwords if the text in the source document is completely lowercase
                    if ngram_text.islower() and ngram_text in STOPWORDS:
                        continue
                        
                    # Normalize the ngram text
                    norm_ngram = clean_text(ngram_text)
                    if norm_ngram in aliases:
                        # Check if this ngram is already captured or overlaps
                        extracted.append({
                            "mention": ngram_text,
                            "start_char": ngram_tokens[0]["start"],
                            "end_char": ngram_tokens[-1]["end"],
                            "category": "DictionaryMatch"
                        })

        # 3. Resolve Overlaps (Keep the longest match)
        # Sort extracted mentions by length (descending) so we process longer spans first
        extracted = sorted(extracted, key=lambda x: (x["end_char"] - x["start_char"]), reverse=True)
        
        final_mentions = []
        seen_chars = set()
        
        for mention in extracted:
            # Check if this mention overlaps with any already accepted mention
            overlap = False
            for idx in range(mention["start_char"], mention["end_char"]):
                if idx in seen_chars:
                    overlap = True
                    break
            
            if not overlap:
                # Accept it
                final_mentions.append(mention)
                # Mark characters as seen
                for idx in range(mention["start_char"], mention["end_char"]):
                    seen_chars.add(idx)

        # Sort the final mentions by start character to return in order of appearance
        final_mentions = sorted(final_mentions, key=lambda x: x["start_char"])
        return final_mentions
