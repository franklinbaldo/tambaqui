import pandas as pd
import camelot
import sys # For sys.exit()
import requests
import os


meses = {
    'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04', 'MAI': '05', 'JUN': '06',
    'JUL': '07', 'AGO': '08', 'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
}
def process_table(table):
    df = table.df.copy()
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    df = pd.melt(df, id_vars=df.columns[0], var_name='Mês', value_name='Fator')
    df.columns = ['Mês', 'Ano', 'Fator']
    df["Ano"] = df["Ano"].str.replace(" ",'', regex=False)
    df['Fator'] = pd.to_numeric(df['Fator'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce')
    df = df.dropna().reset_index(drop=True)
    df['Mês'] = df['Mês'].map(meses)
    df['Ano-Mês'] = df['Ano'] + '-' + df['Mês']
    return df[["Ano-Mês","Fator"]].set_index('Ano-Mês')

# Configuration
PDF_URL = 'https://www.tjsp.jus.br/Download/Tabelas/TabelaEmendaConstitucional113-2021.pdf'
LAST_MODIFIED_FILE = 'last_modified_timestamp.txt'
OUTPUT_JSON = 'tabela_de_atualizacao_ec113.json'
OUTPUT_CSV = 'tabela_de_atualizacao_ec113.csv'

def get_current_last_modified():
    """Fetches the Last-Modified header from the PDF_URL."""
    try:
        print(f"Fetching Last-Modified header from {PDF_URL}")
        response = requests.head(PDF_URL, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.headers.get('Last-Modified')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Last-Modified header: {type(e).__name__} - {e}")
        return None

def get_stored_last_modified():
    """Reads the stored Last-Modified timestamp from the file."""
    if os.path.exists(LAST_MODIFIED_FILE):
        try:
            with open(LAST_MODIFIED_FILE, 'r') as f:
                return f.read().strip()
        except IOError as e:
            print(f"Error reading stored Last-Modified timestamp: {type(e).__name__} - {e}")
    return None

def store_last_modified(timestamp):
    """Saves the new Last-Modified timestamp to the file."""
    try:
        with open(LAST_MODIFIED_FILE, 'w') as f:
            f.write(timestamp)
        print(f"Stored new Last-Modified timestamp: {timestamp}")
    except IOError as e:
        print(f"Error storing Last-Modified timestamp: {type(e).__name__} - {e}")

# --- Main script logic ---
current_server_last_modified = get_current_last_modified()

if current_server_last_modified is None:
    print("Could not determine server's Last-Modified time. Exiting to prevent potential issues.")
    # Optionally, you could decide to proceed with download if this is critical
    # For now, we exit if we can't verify.
    sys.exit(1) 

stored_last_modified = get_stored_last_modified()

print(f"Server Last-Modified: {current_server_last_modified}")
print(f"Stored Last-Modified: {stored_last_modified}")

if current_server_last_modified == stored_last_modified and os.path.exists(OUTPUT_JSON) and os.path.exists(OUTPUT_CSV):
    print("PDF has not been updated since last check and output files exist. Skipping processing.")
    sys.exit(0)
else:
    print("PDF has been updated, was not processed before, or output files are missing. Proceeding with download and processing.")

try:
    print(f"Attempting to read PDF from URL: {PDF_URL}")
    tables = camelot.read_pdf(PDF_URL, pages='all', timeout=120) 
    print("PDF read successfully.")
except Exception as e:
    print(f"Error reading or parsing PDF: {type(e).__name__} - {e}")
    sys.exit(1)

if not tables:
    print("Error: No tables found in the PDF. This might be an issue with the PDF structure or the Camelot library.")
    sys.exit(1)

print(f"Found {len(tables)} tables in the PDF.")

try:
    processed_tables = [process_table(table) for table in tables]
    final_df = pd.concat(processed_tables)
except Exception as e:
    print(f"Error processing tables: {type(e).__name__} - {e}")
    sys.exit(1)

if final_df.empty:
    print("Error: Processed DataFrame is empty. No data to save. This could be due to issues in table processing logic.")
    sys.exit(1)

print("Tables processed successfully. Attempting to save data...")

try:
    final_df.to_json(OUTPUT_JSON, indent=2)
    print(f"Successfully saved data to {OUTPUT_JSON}")
except Exception as e:
    print(f"Error saving to JSON ({OUTPUT_JSON}): {type(e).__name__} - {e}")
    sys.exit(1)

try:
    final_df.to_csv(OUTPUT_CSV)
    print(f"Successfully saved data to {OUTPUT_CSV}")
except Exception as e:
    print(f"Error saving to CSV ({OUTPUT_CSV}): {type(e).__name__} - {e}")
    sys.exit(1)

# After successful processing and saving, store the new Last-Modified timestamp
store_last_modified(current_server_last_modified)
print("Script finished successfully.")
