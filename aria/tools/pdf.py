import sys
import fitz  # PyMuPDF

def read_pdf(file_path: str) -> str:
    """Reads and extracts text from a PDF file using PyMuPDF.
    
    Returns the extracted text as a single string.
    """
    try:
        doc = fitz.open(file_path)
        text_pages = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_pages.append(page.get_text())
        return "\n\n--- Page Break ---\n\n".join(text_pages)
    except Exception as e:
        err_msg = f"Error reading PDF {file_path}: {e}"
        print(err_msg, file=sys.stderr)
        return err_msg

if __name__ == "__main__":
    # Test stub
    print("PDF Reader tool loaded.")
