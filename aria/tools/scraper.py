import sys
import requests
from bs4 import BeautifulSoup

def scrape_url(url: str) -> str:
    """Scrapes a webpage URL and extracts its main text content.
    
    Uses standard requests and BeautifulSoup to strip scripts, styles, 
    and extract clean readable text.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style", "header", "footer", "nav"]):
            script_or_style.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing whitespace
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
        
        return cleaned_text
        
    except Exception as e:
        err_msg = f"Error scraping {url}: {e}"
        print(err_msg, file=sys.stderr)
        return err_msg

if __name__ == "__main__":
    print("Testing Scraper...")
    url = "https://example.com"
    content = scrape_url(url)
    print(f"Content from {url}:\n{content[:200]}")
