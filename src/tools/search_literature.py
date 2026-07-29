import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

def search_literature(query: str, limit: int = 3) -> list[dict]:
    """
    Tool: search_literature
    Queries scientific literature (NCBI PubMed database) for recent publications related to the query term.
    
    Args:
        query (str): The search phrase or medical concept.
        limit (int): Maximum number of publication records to return.
        
    Returns:
        list[dict]: List of matching article details.
    """
    if not query:
        return []

    # 1. Try to query NCBI Entrez public API
    try:
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmode=json&retmax={limit}"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            search_data = json.loads(response.read().decode())
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            
        if id_list:
            ids_str = ",".join(id_list)
            summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"
            req_sum = urllib.request.Request(summary_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_sum, timeout=4) as response_sum:
                summary_data = json.loads(response_sum.read().decode())
                results = summary_data.get("result", {})
                
            articles = []
            for pmid in id_list:
                article_info = results.get(pmid, {})
                title = article_info.get("title", "No Title Available")
                authors = ", ".join([a.get("name", "") for a in article_info.get("authors", [])])
                source = article_info.get("source", "PubMed Journal")
                pubdate = article_info.get("pubdate", "Unknown Date")
                
                articles.append({
                    "pmid": pmid,
                    "title": title,
                    "authors": authors,
                    "source": source,
                    "pubdate": pubdate,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })
            return articles
    except Exception as e:
        print(f"[Literature Tool] Error querying NCBI Entrez: {e}")
        
    return []

if __name__ == "__main__":
    print("Testing search_literature tool...")
    print(json.dumps(search_literature("Diabetes"), indent=2))
