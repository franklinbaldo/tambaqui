import pandas as pd
import camelot
import sys # For sys.exit()


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

url = 'https://www.tjsp.jus.br/Download/Tabelas/TabelaEmendaConstitucional113-2021.pdf'

try:
    print(f"Attempting to read PDF from URL: {url}")
    tables = camelot.read_pdf(url, pages='all', timeout=120) # Added timeout
    print("PDF read successfully.")
except Exception as e:
    print(f"Error reading or parsing PDF: {type(e).__name__} - {e}")
    sys.exit(1) # Exit the script if PDF reading fails

if not tables:
    print("Error: No tables found in the PDF.")
    sys.exit(1)

print(f"Found {len(tables)} tables in the PDF.")

try:
    processed_tables = [process_table(table) for table in tables]
    final_df = pd.concat(processed_tables)
except Exception as e:
    print(f"Error processing tables: {type(e).__name__} - {e}")
    sys.exit(1)

if final_df.empty:
    print("Error: Processed DataFrame is empty. No data to save.")
    sys.exit(1)

print("Tables processed successfully. Attempting to save data...")

try:
    final_df.to_json('tabela_de_atualizacao_ec113.json', indent=2) # Added indent for readability
    print("Successfully saved data to tabela_de_atualizacao_ec113.json")
except Exception as e:
    print(f"Error saving to JSON: {type(e).__name__} - {e}")
    sys.exit(1)

try:
    final_df.to_csv('tabela_de_atualizacao_ec113.csv')
    print("Successfully saved data to tabela_de_atualizacao_ec113.csv")
except Exception as e:
    print(f"Error saving to CSV: {type(e).__name__} - {e}")
    sys.exit(1)

print("Script finished successfully.")
