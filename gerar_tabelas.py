import pandas as pd
import camelot
import sys # For sys.exit()
import requests
import os


meses = {
    'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04', 'MAI': '05', 'JUN': '06',
    'JUL': '07', 'AGO': '08', 'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
}

# This function is now refactored to accept a DataFrame and meses_dict
def process_table(table_df, meses_dict):
    """
    Processes a single DataFrame (derived from a PDF table) to extract and format
    financial correction factors.
    """
    df = table_df.copy()
    # The first row of the DataFrame is expected to be the header
    if df.empty or len(df.columns) == 0:
        # Handle cases with empty or malformed input DataFrame
        print("Warning: process_table received an empty or malformed DataFrame.")
        return pd.DataFrame(columns=['Ano-Mês', 'Fator']).set_index('Ano-Mês')

    try:
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
    except Exception as e:
        print(f"Warning: Error setting headers in process_table, possibly malformed input. Error: {e}")
        return pd.DataFrame(columns=['Ano-Mês', 'Fator']).set_index('Ano-Mês')
        
    
    # Ensure the first column (expected to be month indicators) is named for melting
    if len(df.columns) > 0:
        month_indicator_col = df.columns[0]
    else:
        print("Warning: DataFrame has no columns after header processing in process_table.")
        return pd.DataFrame(columns=['Ano-Mês', 'Fator']).set_index('Ano-Mês')

    df = pd.melt(df, id_vars=[month_indicator_col], var_name='Ano', value_name='Fator') # Renamed var_name to 'Ano' for clarity
    df.columns = ['Mês', 'Ano', 'Fator'] # Ensure correct column names after melt
    
    df["Ano"] = df["Ano"].astype(str).str.replace(" ", '', regex=False) # Convert Ano to string before replace
    df['Fator'] = pd.to_numeric(df['Fator'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce')
    df = df.dropna().reset_index(drop=True)
    df['Mês'] = df['Mês'].map(meses_dict)
    df['Ano-Mês'] = df['Ano'] + '-' + df['Mês']
    return df[["Ano-Mês","Fator"]].set_index('Ano-Mês')

# --- Configuration Constants ---
PDF_URL = 'https://www.tjsp.jus.br/Download/Tabelas/TabelaEmendaConstitucional113-2021.pdf'
LAST_MODIFIED_FILE = 'last_modified_timestamp.txt'
OUTPUT_JSON = 'tabela_de_atualizacao_ec113.json'
OUTPUT_CSV = 'tabela_de_atualizacao_ec113.csv'

# --- Helper Functions for External Interactions ---
def get_current_last_modified_from_server(url):
    """Fetches the Last-Modified header from the given URL."""
    try:
        print(f"Fetching Last-Modified header from {url}")
        response = requests.head(url, timeout=30)
        response.raise_for_status()
        return response.headers.get('Last-Modified')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Last-Modified header: {type(e).__name__} - {e}")
        return None

def get_stored_last_modified(filepath):
    """Reads the stored Last-Modified timestamp from the file."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return f.read().strip()
        except IOError as e:
            print(f"Error reading stored Last-Modified timestamp from {filepath}: {type(e).__name__} - {e}")
    return None

def store_last_modified_to_file(filepath, timestamp):
    """Saves the new Last-Modified timestamp to the file."""
    try:
        with open(filepath, 'w') as f:
            f.write(timestamp)
        print(f"Stored new Last-Modified timestamp to {filepath}: {timestamp}")
    except IOError as e:
        print(f"Error storing Last-Modified timestamp to {filepath}: {type(e).__name__} - {e}")

def fetch_and_parse_pdf(url, timeout=120):
    """Fetches PDF from URL and parses it using Camelot."""
    print(f"Attempting to read PDF from URL: {url}")
    try:
        tables = camelot.read_pdf(url, pages='all', timeout=timeout)
        print("PDF read successfully.")
        if not tables:
            print("Error: No tables found in the PDF. This might be an issue with the PDF structure or the Camelot library.")
            return None # Or raise an exception
        print(f"Found {len(tables)} tables in the PDF.")
        return tables
    except Exception as e: # Broad exception for camelot issues
        print(f"Error reading or parsing PDF: {type(e).__name__} - {e}")
        return None # Or raise an exception

# --- Helper Functions for Data Processing ---
def process_and_concatenate_tables(tables_list):
    """Processes list of Camelot tables and concatenates them."""
    if not tables_list:
        return pd.DataFrame() # Return empty DataFrame if no tables
    
    processed_dfs = []
    for i, table_obj in enumerate(tables_list):
        print(f"Processing table {i+1}/{len(tables_list)}")
        try:
            # Pass the DataFrame from the table object and the global meses dict
            df = process_table(table_obj.df, meses) 
            if not df.empty: # Only append if processing didn't result in an empty df (e.g. from errors)
                processed_dfs.append(df)
        except Exception as e:
            print(f"Error processing table object's DataFrame {i+1}: {type(e).__name__} - {e}")
            # Optionally, decide if one bad table should stop all processing
            # For now, we skip bad tables.
    
    if not processed_dfs:
        print("No tables were successfully processed.")
        return pd.DataFrame()

    try:
        final_df = pd.concat(processed_dfs)
        if final_df.empty:
            print("Error: Processed DataFrame is empty after concatenation. No data to save.")
        return final_df
    except Exception as e:
        print(f"Error concatenating processed tables: {type(e).__name__} - {e}")
        return pd.DataFrame()

# --- Helper Function for Saving Data ---
def save_dataframes(df, json_path, csv_path):
    """Saves DataFrame to JSON and CSV files."""
    if df.empty:
        print("DataFrame is empty, skipping save operations.")
        return False # Indicate failure or that nothing was saved
    
    print("Attempting to save data...")
    try:
        df.to_json(json_path, indent=2)
        print(f"Successfully saved data to {json_path}")
    except Exception as e:
        print(f"Error saving to JSON ({json_path}): {type(e).__name__} - {e}")
        return False # Indicate failure

    try:
        df.to_csv(csv_path)
        print(f"Successfully saved data to {csv_path}")
    except Exception as e:
        print(f"Error saving to CSV ({csv_path}): {type(e).__name__} - {e}")
        return False # Indicate failure
    return True # Indicate success

# --- Main Orchestration Function ---
def main():
    """Main function to orchestrate PDF fetching, processing, and saving."""
    current_server_lm = get_current_last_modified_from_server(PDF_URL)

    if current_server_lm is None:
        print("Could not determine server's Last-Modified time. Exiting to prevent potential issues.")
        sys.exit(1)

    stored_lm = get_stored_last_modified(LAST_MODIFIED_FILE)

    print(f"Server Last-Modified: {current_server_lm}")
    print(f"Stored Last-Modified: {stored_lm}")

    if current_server_lm == stored_lm and os.path.exists(OUTPUT_JSON) and os.path.exists(OUTPUT_CSV):
        print("PDF has not been updated since last check and output files exist. Skipping processing.")
        sys.exit(0)
    else:
        print("PDF has been updated, was not processed before, or output files are missing. Proceeding with download and processing.")

    pdf_tables = fetch_and_parse_pdf(PDF_URL)
    if pdf_tables is None:
        print("Exiting due to failure in fetching or parsing PDF.")
        sys.exit(1)

    final_dataframe = process_and_concatenate_tables(pdf_tables)
    if final_dataframe.empty:
        print("Exiting because the final DataFrame is empty after processing.")
        sys.exit(1)
    
    save_successful = save_dataframes(final_dataframe, OUTPUT_JSON, OUTPUT_CSV)
    
    if save_successful:
        store_last_modified_to_file(LAST_MODIFIED_FILE, current_server_lm)
        print("Script finished successfully.")
    else:
        print("Script finished with errors during saving.")
        sys.exit(1)

if __name__ == "__main__":
    main()
