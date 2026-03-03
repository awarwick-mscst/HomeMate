import os
import requests
from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return None

def query_ollama(prompt, context, model="llama3.2", ollama_url="http://10.0.0.55:11434"):
    """
    Send a prompt + context to local Ollama instance.
    Adjust ollama_url if your AI server is at a different IP.
    """
    full_prompt = f"""You are a helpful assistant. Answer the user's question based on the provided manual and appliance data.

Appliance Information:
{context}

User Question: {prompt}

Provide a clear, helpful answer. If the information is not in the manual, say so."""

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "keep_alive": "5m"
            },
            timeout=120
        )
        if response.status_code == 200:
            return response.json().get("response", "No response from model.")
        else:
            return f"Error: Ollama returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to Ollama. Is it running?"
    except Exception as e:
        return f"Error: {str(e)}"
