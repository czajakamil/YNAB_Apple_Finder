import os
import subprocess
import requests
import json
from datetime import datetime
from pdf2image import convert_from_path # type: ignore
import base64
import re

def get_unique_filename(directory, filename):
    """
    Generuje unikalną nazwę pliku w danym katalogu.
    Dodaje numerowany sufiks do nazwy pliku, jeśli plik o podanej nazwie już istnieje.

    Args:
        directory (str): Ścieżka do katalogu, w którym ma być zapisany plik.
        filename (str): Początkowa nazwa pliku.

    Returns:
        str: Unikalna nazwa pliku.
    """
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename

    while os.path.exists(os.path.join(directory, unique_filename)):
        unique_filename = f"{base}_{counter}{ext}"
        counter += 1

    return unique_filename

def get_creation_date(path_to_file):
    """
    Pobiera datę utworzenia pliku za pomocą komendy 'mdls' w systemie macOS.

    Args:
        path_to_file (str): Ścieżka do pliku.

    Returns:
        datetime or None: Obiekt datetime reprezentujący datę utworzenia pliku,
                          lub None, jeśli nie uda się pobrać daty.
    """
    try:
        result = subprocess.run(['mdls', '-name', 'kMDItemFSCreationDate', '-raw', path_to_file], capture_output=True, text=True)
        creation_date_str = result.stdout.strip()
        # Przekonwertuj datę utworzenia na obiekt datetime
        creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")
        return creation_date
    except Exception as e:
        print(f"Nie udało się uzyskać daty utworzenia: {e}")
        return None

def convert_pdfs_to_pngs(pdf_directory, output_directory):
    """
    Konwertuje wszystkie pliki PDF w zadanym katalogu na obrazy PNG i zapisuje je
    w katalogu wyjściowym. Pliki PDF, które zostały poprawnie przetworzone,
    są następnie przemianowywane z prefiksem 'Converted' i datą utworzenia.

    Args:
        pdf_directory (str): Ścieżka do katalogu zawierającego pliki PDF.
        output_directory (str): Ścieżka do katalogu, gdzie mają być zapisane obrazy PNG.
    """
    # If path doesn't exist, create directory.
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Get list of all the PDF files that do not start with 'Converted'
    pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith('.pdf') and not f.startswith('Converted')]

    if not pdf_files:
        print("Brak PDF'ów do konwersji")
        return
    
    files_to_rename = []

    # Convert the PDFs
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_directory, pdf_file)
        try:
            images = convert_from_path(pdf_path)
            for i, image in enumerate(images):
                output_file_path = os.path.join(output_directory, f"{os.path.splitext(pdf_file)[0]}_page_{i+1}.png")
                image.save(output_file_path, 'PNG')
                print(f"Zapisano {output_file_path}")
            files_to_rename.append(pdf_path)
        except Exception as e:
            print(f"Nie udało się przekonwertować {pdf_file}: {e}")

    for pdf_path in files_to_rename:
        try:
            creation_date = get_creation_date(pdf_path)
            if creation_date:
                date_str = creation_date.strftime("%Y_%m_%d")
                new_pdf_name = f"Converted_{date_str}.pdf"
                new_pdf_name = get_unique_filename(pdf_directory, new_pdf_name)
                new_pdf_path = os.path.join(pdf_directory, new_pdf_name)
                os.rename(pdf_path, new_pdf_path)
                print(f"Zmieniono nazwę z {pdf_path} na {new_pdf_path}")
        except Exception as e:
            print(f"Nie udało się zmienić nazwy {pdf_path}: {e}")

def get_the_files_for_ocr(directory):
    """
    Pobiera wszystkie pliki PNG z zadanego katalogu, które nie zaczynają się od 'DONE'.

    Args:
        directory (str): Ścieżka do katalogu.

    Returns:
        list: Lista ścieżek do plików PNG.
    """
    # Pobiera wszystkie pliki w katalogu
    files = os.listdir(directory)
    # Filtruje pliki, które nie zaczynają się od 'DONE' i mają rozszerzenie .png
    filtered_files = [os.path.join(directory, file) for file in files if not file.startswith('DONE') and (file.endswith('.png') or file.endswith('.PNG'))]
    return filtered_files

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')
  

def validate_json(data):
    errors = []

    # Validate basic structure
    if not isinstance(data, dict):
        errors.append("JSON powinien być obiektem.")
        return errors

    if "transactions" not in data:
        errors.append("Brak klucza 'transactions'.")
        return errors

    transactions = data["transactions"]
    if not isinstance(transactions, list):
        errors.append("'transactions' powinien być listą.")
        return errors

    # Loop through each transaction to validate
    for transaction in transactions:
        # Validate required fields
        required_fields = ["id", "receipt_number", "timestamp", "date", "store", "total", "taxes_total", "currency", "items", "comments", "category", "transaction_comment"]
        for field in required_fields:
            if field not in transaction:
                errors.append(f"Brak klucza '{field}' w transakcji.")
                continue
        
        # Validate types
        if not isinstance(transaction["id"], str):
            errors.append("Pole 'id' powinno być stringiem.")
        
        # Validate timestamp
        try:
            datetime.strptime(transaction["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append("Pole 'timestamp' ma nieprawidłowy format.")
        
        # Validate date
        try:
            datetime.strptime(transaction["date"], "%Y-%m-%d")
        except ValueError:
            errors.append("Pole 'date' ma nieprawidłowy format.")
        
        # Validate store information
        store = transaction["store"]
        if not isinstance(store, dict):
            errors.append("Pole 'store' powinno być obiektem.")
        else:
            if "name" not in store or not isinstance(store["name"], str):
                errors.append("Pole 'store.name' powinno być stringiem.")
            if "address" not in store or not isinstance(store["address"], str):
                errors.append("Pole 'store.address' powinno być stringiem.")
            if "NIP" not in store or not re.match(r"^\d{10}$", store["NIP"]):
                errors.append("Pole 'store.NIP' powinno mieć 10 cyfr.")
        
        # Validate total
        if not isinstance(transaction["total"], (int, float)) or transaction["total"] < 0:
            errors.append("Pole 'total' powinno być dodatnią liczbą.")
        
        # Validate currency
        if not isinstance(transaction["currency"], str) or len(transaction["currency"]) != 3:
            errors.append("Pole 'currency' powinno być trzyliterowym stringiem.")

        # Validate items
        items = transaction["items"]
        if not isinstance(items, list):
            errors.append("Pole 'items' powinno być listą.")
        else:
            total_price_sum = 0
            for item in items:
                if "name" not in item or not isinstance(item["name"], str):
                    errors.append("Pole 'items[].name' powinno być stringiem.")
                if "unit_price" not in item or not isinstance(item["unit_price"], dict):
                    errors.append("Pole 'items[].unit_price' powinno być obiektem.")
                if "quantity" not in item or not isinstance(item["quantity"], (int, float)):
                    errors.append("Pole 'items[].quantity' powinno być liczbą.")
                if "total_price" not in item or not isinstance(item["total_price"], dict):
                    errors.append("Pole 'items[].total_price' powinno być obiektem.")
                
                # Validate total_price.after_discount
                total_price_sum += item["total_price"]["after_discount"]

                # Validate unit_of_measurement
                if "unit_of_measurement" not in item or item["unit_of_measurement"] not in ["szt", "kg", "l", "m"]:
                    errors.append("Pole 'items[].unit_of_measurement' powinno być jedną z wartości: 'szt', 'kg', 'l', 'm'.")
            
            # Check if sum of total_price.after_discount matches total
            if round(total_price_sum, 2) != round(transaction["total"], 2):
                errors.append("Suma 'total_price.after_discount' nie zgadza się z 'total'.")

        # Validate taxes
        taxes = transaction.get("taxes", [])
        if not isinstance(taxes, list):
            errors.append("Pole 'taxes' powinno być listą.")
        else:
            taxes_total_sum = 0
            for tax in taxes:
                if "type" not in tax or not isinstance(tax["type"], str):
                    errors.append("Pole 'taxes[].type' powinno być stringiem.")
                if "rate" not in tax or not isinstance(tax["rate"], (int, float)):
                    errors.append("Pole 'taxes[].rate' powinno być liczbą.")
                if "amount" not in tax or not isinstance(tax["amount"], (int, float)):
                    errors.append("Pole 'taxes[].amount' powinno być liczbą.")
                
                # Sum the taxes amounts
                taxes_total_sum += tax["amount"]
            
            # Check if sum of taxes amounts matches taxes_total
            if round(taxes_total_sum, 2) != round(transaction.get("taxes_total", 0), 2):
                errors.append("Suma 'taxes[].amount' nie zgadza się z 'taxes_total'.")

    if not errors:
        return True
    return errors


def load_prompt(file_path):
    """Load prompt from a file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    

def perform_ocr(api_key, prompt, base64_image):
    """Perform OCR on a base64 image."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{prompt}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 4096
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()

def clean_ocr_response(response):
    response = response['choices'][0]['message']['content']
    cleaned_content = response.strip('```json\n').strip('\n```')
    return json.loads(cleaned_content)