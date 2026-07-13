from bs4 import BeautifulSoup
from app.parsers.preprocessing import Preprocessor

html = """
<div>
  <h2>Pricing</h2>
  <a href="/buy" aria-label="Purchase Premium Plan">
    <svg>...</svg>
  </a>
  <button>
    <img src="cart.png" alt="Add to cart">
  </button>
</div>
"""

def prove_gap():
    print("--- 1. Testing Current Parsing Logic ---")
    preprocessor = Preprocessor()
    processed_html = preprocessor.process(html)
    
    soup = BeautifulSoup(processed_html, "html.parser")
    buttons = soup.find_all("button")
    links = soup.find_all("a")
    
    link_text = links[0].get_text(strip=True) if links else ""
    btn_text = buttons[0].get_text(strip=True) if buttons else ""
    
    print(f"Processed HTML: {processed_html}")
    print(f"Extracted Link Text: '{link_text}'")
    print(f"Extracted Button Text: '{btn_text}'")
    
    if "Purchase Premium Plan" not in link_text or "Add to cart" not in btn_text:
        print("FAIL: A11y text is completely ignored by get_text()!")
    else:
        print("PASS: A11y text is extracted.")

if __name__ == "__main__":
    prove_gap()
