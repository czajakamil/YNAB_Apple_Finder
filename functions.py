import os
import subprocess
from datetime import datetime
from pdf2image import convert_from_path
import base64

def get_unique_filename(directory, filename):
    """
    Generuje unikalną nazwę pliku w danym katalogu przez dodanie
    numerowanego sufiksu do nazwy pliku, jeśli plik o podanej nazwie już istnieje.

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


def get_the_files_with_paths(directory):
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
    filtered_files = [os.path.join(directory, file) for file in files if not file.startswith('DONE') and file.endswith('.png')]
    return filtered_files

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')