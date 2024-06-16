import os
import json
from dotenv import load_dotenv
from tqdm import tqdm
from functions import convert_pdfs_to_pngs, get_the_files_for_ocr, encode_image, validate_json, load_prompt, perform_ocr, clean_ocr_response

def load_environment_variables():
    load_dotenv()
    return {
        'api_key': os.getenv('OPENAI_API'),
        'pdf_path': os.getenv('PDF_DIRECTORY'),
        'png_path': os.getenv('OUTPUT_DIRECTORY'),
        'main_json_file': os.getenv('JSON_MAIN_FILE')
    }

def update_transactions(main_json_file, new_transactions):
    if os.path.exists(main_json_file):
        with open(main_json_file, 'r', encoding='utf-8') as file:
            all_transactions = json.load(file)
    else:
        all_transactions = {"transactions": []}

    all_transactions["transactions"].extend(new_transactions["transactions"])

    with open(main_json_file, 'w', encoding='utf-8') as file:
        json.dump(all_transactions, file, ensure_ascii=False, indent=4)

    print(f"Zaktualizowany plik zapisano jako {main_json_file}")

def rename_file(file_path, json_data):
    date_str = json_data['transactions'][0]['date']
    sklep = json_data['transactions'][0]['store']['name']
    kwota = json_data['transactions'][0]['total']
    new_file_name = f"DONE_{date_str}_{sklep}_{kwota}.png"
    new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
    os.rename(file_path, new_file_path)

def main():
    # Konfiguracja środowiska
    print("Ładowanie zmiennych środowiskowych...")
    env_vars = load_environment_variables()
    api_key = env_vars['api_key']
    pdf_path = env_vars['pdf_path']
    png_path = env_vars['png_path']
    main_json_file = env_vars['main_json_file']
    
    # Konwersja PDF do PNG
    print("Konwersja plików PDF do PNG...")
    convert_pdfs_to_pngs(pdf_path, png_path)
    
    # Wybieramy sobie pliki do OCR'owania
    print("Wybieranie plików do OCR...")
    files_to_analyze = get_the_files_for_ocr(png_path)
    print(f"Liczba plików do sprawdzenia: {len(files_to_analyze)}")
    
    # Załaduj prompt dla chatu
    print("Ładowanie promptu dla chatu...")
    prompt = load_prompt('prompt.txt')
    
    # Iteracja przez pliki z wskaźnikiem postępu
    for file in tqdm(files_to_analyze, desc="Przetwarzanie plików"):
        print(f"Przetwarzanie pliku: {file}")
        
        base64_image = encode_image(file)
        print(f"Wykonywanie OCR na pliku: {file}")

        json_data = perform_ocr(api_key, prompt, base64_image)
        print(f"Uzyskane dane: {json_data}")

        # Posprzątajmy trochę dane
        json_data = clean_ocr_response(json_data)
        
        # Wyświetl przetworzone dane (w celu debugowania)
        print(f"Przetworzone dane dla pliku {file}:")
        print(json.dumps(json_data, indent=4, ensure_ascii=False))
        
        # Walidacja danych
        print(f"Walidacja danych dla pliku: {file}")
        validate_json(json_data)
        
        # Aktualizacja pliku transakcji
        print(f"Aktualizacja pliku transakcji dla danych z pliku: {file}")
        update_transactions(main_json_file, json_data)
        
        # Zmiana nazwy pliku
        print(f"Zmiana nazwy pliku: {file}")
        rename_file(file, json_data)

if __name__ == "__main__":
    main()