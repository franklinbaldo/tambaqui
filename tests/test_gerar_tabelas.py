import pandas as pd
from pandas.testing import assert_frame_equal
import pytest
import numpy as np # For NaN values

import os
import sys
import requests # For mocking requests.exceptions.RequestException

# Adjust the import path based on your project structure.
from .. import gerar_tabelas # Import the module to allow patching its members
from ..gerar_tabelas import (
    main, process_table, meses as app_meses,
    PDF_URL, LAST_MODIFIED_FILE, OUTPUT_JSON, OUTPUT_CSV # Import constants
)

# --- Helper Function to Create Mock Raw DataFrames (from previous step) ---
def create_raw_df(data_rows, year_columns):
    """
    Creates a DataFrame similar to the raw input expected by process_table
    (i.e., table.df from Camelot, where the first row is the header).
    """
    header_row = ['Mês/Ano'] + year_columns
    # Create DataFrame using the header for columns, then prepend the header as the first data row
    # This mimics Camelot's behavior where df.iloc[0] is the header.
    df_data = [header_row] + data_rows
    df = pd.DataFrame(df_data)
    # The first row is data that will become the header in process_table
    return df

# --- Test Cases ---

def test_process_table_basic():
    """Test basic processing with valid data."""
    raw_df = create_raw_df(
        data_rows=[
            ['JAN', '1.000,00', '1.100,00'],
            ['FEV', '1.010,00', ''] # Empty Fator for 2024-02, should be dropped
        ],
        year_columns=['2023', '2024']
    )
    # Expected DataFrame after processing
    expected_data = {
        'Ano-Mês': ['2023-01', '2023-02', '2024-01'],
        'Fator': [1000.00, 1010.00, 1100.00]
    }
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df, check_dtype=False) # Dtype can be tricky with NaN then drop

def test_process_table_fator_with_dots():
    """Test Fator conversion with multiple dots (thousands separators)."""
    raw_df = create_raw_df(
        data_rows=[['MAR', '1.234.567,89']],
        year_columns=['2023']
    )
    expected_data = {'Ano-Mês': ['2023-03'], 'Fator': [1234567.89]}
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês')

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df)

def test_process_table_non_numeric_fator():
    """Test that rows with non-numeric 'Fator' values are dropped."""
    raw_df = create_raw_df(
        data_rows=[
            ['ABR', '1.500,50', '-'],
            ['MAI', 'N/A', '1.600,60']
        ],
        year_columns=['2023', '2024']
    )
    expected_data = {
        'Ano-Mês': ['2023-04', '2024-05'],
        'Fator': [1500.50, 1600.60]
    }
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df, check_dtype=False)

def test_process_table_empty_input():
    """Test with an empty DataFrame as input."""
    empty_raw_df = pd.DataFrame() # Completely empty
    expected_df = pd.DataFrame(columns=['Ano-Mês', 'Fator']).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(empty_raw_df, app_meses)
    assert_frame_equal(result_df, expected_df, check_dtype=False)

    # Test with DataFrame that only contains a header row (which gets consumed)
    # and thus becomes empty for processing logic inside process_table
    header_only_df = create_raw_df(data_rows=[], year_columns=['2023'])
    # process_table will try to use .iloc[0] for columns, then .iloc[1:] for data.
    # If data_rows is empty, df.iloc[1:] will be empty.
    result_df_header_only = process_table(header_only_df, app_meses)
    assert_frame_equal(result_df_header_only, expected_df, check_dtype=False)


def test_process_table_malformed_header():
    """
    Test with a DataFrame where the first row (expected headers) is malformed
    or insufficient for the operations in process_table.
    """
    # Malformed: Not enough elements in the first row to be used as headers
    # This structure would cause an error when df.columns = df.iloc[0] is applied
    # if the number of elements in iloc[0] doesn't match number of existing columns.
    # However, create_raw_df ensures df.iloc[0] has same length as df.columns.
    # Let's test a df that is empty *after* header processing.
    df_data = [
        ['Mês/Ano', '2023'] # This becomes the header
        # No data rows
    ]
    malformed_df_for_logic = pd.DataFrame(df_data) # .iloc[0] will be header, .iloc[1:] will be empty

    expected_df = pd.DataFrame(columns=['Ano-Mês', 'Fator']).set_index('Ano-Mês').astype({'Fator': 'float64'})
    result_df = process_table(malformed_df_for_logic, app_meses)
    assert_frame_equal(result_df, expected_df, check_dtype=False)

    # Test with a completely empty dataframe, which process_table should handle
    empty_df = pd.DataFrame()
    result_empty_df = process_table(empty_df, app_meses)
    assert_frame_equal(result_empty_df, expected_df, check_dtype=False)

    # Test with a DataFrame that has no columns after trying to set header
    # This is a bit hard to simulate perfectly without replicating process_table's internal error handling logic,
    # but the refactored process_table has try-except for header setting.
    df_no_cols_after_header = pd.DataFrame([[]]) # A single row with no columns
    result_no_cols = process_table(df_no_cols_after_header, app_meses)
    assert_frame_equal(result_no_cols, expected_df, check_dtype=False)


def test_process_table_all_months():
    """Test that all months in the `meses` dictionary are correctly mapped."""
    all_meses_abbr = list(app_meses.keys())
    data_rows = [[abbr, '1.000,00'] for abbr in all_meses_abbr]

    raw_df = create_raw_df(data_rows, year_columns=['2023'])

    expected_ano_mes = [f"2023-{app_meses[abbr]}" for abbr in all_meses_abbr]
    expected_fator = [1000.00] * len(all_meses_abbr)

    expected_data = {'Ano-Mês': expected_ano_mes, 'Fator': expected_fator}
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(raw_df, app_meses)
    # Sort both DataFrames by index to ensure consistent comparison
    result_df = result_df.sort_index()
    expected_df = expected_df.sort_index()
    assert_frame_equal(result_df, expected_df, check_dtype=False)

def test_process_table_ano_with_spaces():
    """Test that years with spaces are correctly processed."""
    raw_df = create_raw_df(
        data_rows=[['JAN', '1.000,00']],
        year_columns=['2 023'] # Year with a space
    )
    expected_data = {'Ano-Mês': ['2023-01'], 'Fator': [1000.00]}
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês')

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df)

def test_process_table_fator_is_string_float():
    """Test Fator conversion when it's already a string representing a float (e.g., '1000.00')."""
    raw_df = create_raw_df(
        data_rows=[['JAN', '1000.00']], # Fator is already dot-separated float string
        year_columns=['2023']
    )
    expected_data = {'Ano-Mês': ['2023-01'], 'Fator': [1000.00]}
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês')

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df)

def test_process_table_mixed_fator_formats():
    """Test Fator conversion with mixed formats (some with comma, some with dot)."""
    raw_df = create_raw_df(
        data_rows=[
            ['JAN', '1.234,56'],
            ['FEV', '123.45']
        ],
        year_columns=['2023']
    )
    expected_data = {
        'Ano-Mês': ['2023-01', '2023-02'],
        'Fator': [1234.56, 123.45]
    }
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df)

def test_process_table_no_valid_data_rows():
    """Test scenario where all data rows have issues (e.g., non-numeric Fator)."""
    raw_df = create_raw_df(
        data_rows=[
            ['JAN', 'N/A'],
            ['FEV', '-']
        ],
        year_columns=['2023']
    )
    expected_df = pd.DataFrame(columns=['Ano-Mês', 'Fator']).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df, check_dtype=False)

def test_process_table_empty_string_in_fator():
    """Test Fator conversion when it's an empty string."""
    raw_df = create_raw_df(
        data_rows=[
            ['JAN', '1.234,56'],
            ['FEV', ''], # Empty string Fator
            ['MAR', '1.300,00']
        ],
        year_columns=['2023']
    )
    expected_data = {
        'Ano-Mês': ['2023-01', '2023-03'],
        'Fator': [1234.56, 1300.00]
    }
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df, check_dtype=False)

def test_process_table_multiple_years_and_months():
    """Test with multiple years and a fuller range of months."""
    raw_df = create_raw_df(
        data_rows=[
            ['JAN', '1.000,00', '2.000,00'],
            ['FEV', '1.010,00', '2.010,00'],
            ['MAR', '1.020,00', '2.020,00'],
            ['ABR', '1.030,00', ''], # Empty Fator for 2024-04
            ['MAI', '', '2.040,00'], # Empty Fator for 2023-05
            ['JUN', '1.050,00', '2.050,00'],
        ],
        year_columns=['2023', '2024']
    )
    expected_data = {
        'Ano-Mês': [
            '2023-01', '2023-02', '2023-03', '2023-06',
            '2024-01', '2024-02', '2024-03', '2024-05', '2024-06'
        ],
        'Fator': [
            1000.00, 1010.00, 1020.00, 1050.00,
            2000.00, 2010.00, 2020.00, 2040.00, 2050.00
        ]
    }
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(raw_df, app_meses)
    # Sort both DataFrames by index to ensure consistent comparison
    result_df = result_df.sort_index()
    expected_df = expected_df.sort_index()
    assert_frame_equal(result_df, expected_df, check_dtype=False)

def test_process_table_data_types():
    """Test the data types of the processed DataFrame."""
    raw_df = create_raw_df(
        data_rows=[['JAN', '1.000,00']],
        year_columns=['2023']
    )
    result_df = process_table(raw_df, app_meses)
    assert result_df.index.name == 'Ano-Mês'
    assert result_df['Fator'].dtype == 'float64'
    assert all(isinstance(idx, str) for idx in result_df.index)

def test_process_table_malformed_data_rows_not_enough_cols():
    """Test with data rows that don't have enough columns for all years."""
    # Here, 'FEV' row is missing a value for the '2024' column.
    # pd.melt should handle this by creating a row with NaN for that missing value,
    # which then gets dropped by .dropna().
    raw_df = create_raw_df(
        data_rows=[
            ['JAN', '1.000,00', '1.100,00'],
            ['FEV', '1.010,00'] # Missing data for 2024
        ],
        year_columns=['2023', '2024']
    )
    expected_data = {
        'Ano-Mês': ['2023-01', '2023-02', '2024-01'],
        'Fator': [1000.00, 1010.00, 1100.00]
    }
    expected_df = pd.DataFrame(expected_data).set_index('Ano-Mês').astype({'Fator': 'float64'})

    result_df = process_table(raw_df, app_meses)
    assert_frame_equal(result_df, expected_df, check_dtype=False)

# Note: The `process_table` function in `gerar_tabelas.py` has internal try-except blocks
# for header processing. If those fail, it returns an empty DataFrame.
# The tests for `test_process_table_empty_input` and `test_process_table_malformed_header`
# cover these scenarios by checking for an empty DataFrame output.
# More specific error raising tests would require mocking internal pandas calls,
# which is beyond typical unit testing for this function's scope unless specific
# exceptions are expected to be propagated.


# --- Mocks and Helpers for main() logic tests ---

class MockCamelotTable:
    def __init__(self, df_data_list_of_lists):
        # df_data_list_of_lists should be structured like:
        # [['Mês/Ano', '2023', '2024'], ['JAN', '1,0', '2,0']]
        # The first inner list is the header row for the DataFrame.
        self.df = pd.DataFrame(df_data_list_of_lists[1:], columns=df_data_list_of_lists[0])
        # To make it more realistic like camelot's output where .df.iloc[0] is used for columns
        # by process_table, we'll adjust it here.
        # The create_raw_df function already helps in creating a df that process_table can use.
        # For simplicity, let's assume the df passed here is what table.df would be.
        self.parsing_report = {'accuracy': 99, 'whitespace': 1}

# --- Test Cases for main() and orchestrated logic ---

@pytest.fixture(autouse=True)
def mock_sys_exit(mocker):
    """Automatically mock sys.exit for all tests in this module."""
    return mocker.patch('sys.exit')

def test_main_pdf_updated_and_files_regenerated(mocker, caplog, mock_sys_exit):
    """
    Test main logic when PDF is updated:
    - Stored timestamp is old.
    - New PDF is fetched, processed, and data saved.
    - New timestamp is stored.
    """
    mock_get_current_lm = mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="new_timestamp")
    mock_get_stored_lm = mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="old_timestamp")
    mock_os_path_exists_output = mocker.patch('os.path.exists', return_value=True) # Assume output files exist initially

    # Mock PDF fetching and processing
    # Use create_raw_df to create a DataFrame that process_table can handle
    sample_raw_df_data = create_raw_df([['JAN', '1.000,00']], ['2023'])
    mock_pdf_tables = [MockCamelotTable(sample_raw_df_data.values.tolist())] # MockCamelotTable expects list of lists

    mock_fetch_parse = mocker.patch('gerar_tabelas.fetch_and_parse_pdf', return_value=mock_pdf_tables)

    # Mock actual processing result
    processed_df_data = {'Ano-Mês': ['2023-01'], 'Fator': [1000.0]}
    mock_processed_df = pd.DataFrame(processed_df_data).set_index('Ano-Mês')
    mock_process_concat = mocker.patch('gerar_tabelas.process_and_concatenate_tables', return_value=mock_processed_df)

    mock_save_df = mocker.patch('gerar_tabelas.save_dataframes', return_value=True)
    mock_store_lm_file = mocker.patch('gerar_tabelas.store_last_modified_to_file')

    main()

    mock_get_current_lm.assert_called_once_with(PDF_URL)
    mock_get_stored_lm.assert_called_once_with(LAST_MODIFIED_FILE)
    mock_fetch_parse.assert_called_once_with(PDF_URL)
    mock_process_concat.assert_called_once_with(mock_pdf_tables)
    mock_save_df.assert_called_once_with(mock_processed_df, OUTPUT_JSON, OUTPUT_CSV)
    mock_store_lm_file.assert_called_once_with(LAST_MODIFIED_FILE, "new_timestamp")
    assert "PDF has been updated" in caplog.text
    assert "Script finished successfully." in caplog.text
    mock_sys_exit.assert_not_called()


def test_main_pdf_not_updated_files_exist(mocker, caplog, mock_sys_exit):
    """
    Test main logic when PDF is NOT updated and output files exist:
    - Stored timestamp matches server.
    - Processing is skipped.
    """
    mock_get_current_lm = mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="same_timestamp")
    mock_get_stored_lm = mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="same_timestamp")
    # Mock os.path.exists to return True for all checks (timestamp file and output files)
    mock_os_path_exists = mocker.patch('os.path.exists', return_value=True)

    mock_fetch_parse = mocker.patch('gerar_tabelas.fetch_and_parse_pdf')
    mock_process_concat = mocker.patch('gerar_tabelas.process_and_concatenate_tables')
    mock_save_df = mocker.patch('gerar_tabelas.save_dataframes')
    mock_store_lm_file = mocker.patch('gerar_tabelas.store_last_modified_to_file')

    main()

    mock_get_current_lm.assert_called_once_with(PDF_URL)
    mock_get_stored_lm.assert_called_once_with(LAST_MODIFIED_FILE)

    # Ensure these were NOT called
    mock_fetch_parse.assert_not_called()
    mock_process_concat.assert_not_called()
    mock_save_df.assert_not_called()
    mock_store_lm_file.assert_not_called()

    assert "PDF has not been updated since last check and output files exist. Skipping processing." in caplog.text
    mock_sys_exit.assert_called_once_with(0)


def test_main_output_files_missing_pdf_not_updated(mocker, caplog, mock_sys_exit):
    """
    Test main logic when output files are missing, even if PDF timestamp hasn't changed:
    - Data should be re-processed and saved.
    """
    mock_get_current_lm = mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="same_timestamp")
    mock_get_stored_lm = mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="same_timestamp")

    # Simulate timestamp file exists, but one of the output files (e.g., JSON) does not
    def os_path_exists_side_effect(path):
        if path == LAST_MODIFIED_FILE: return True
        if path == OUTPUT_JSON: return False # Simulate JSON missing
        if path == OUTPUT_CSV: return True
        return False # Default for any other path
    mock_os_path_exists = mocker.patch('os.path.exists', side_effect=os_path_exists_side_effect)

    sample_raw_df_data = create_raw_df([['JAN', '1.000,00']], ['2023'])
    mock_pdf_tables = [MockCamelotTable(sample_raw_df_data.values.tolist())]
    mock_fetch_parse = mocker.patch('gerar_tabelas.fetch_and_parse_pdf', return_value=mock_pdf_tables)

    processed_df_data = {'Ano-Mês': ['2023-01'], 'Fator': [1000.0]}
    mock_processed_df = pd.DataFrame(processed_df_data).set_index('Ano-Mês')
    mock_process_concat = mocker.patch('gerar_tabelas.process_and_concatenate_tables', return_value=mock_processed_df)

    mock_save_df = mocker.patch('gerar_tabelas.save_dataframes', return_value=True)
    mock_store_lm_file = mocker.patch('gerar_tabelas.store_last_modified_to_file')

    main()

    mock_fetch_parse.assert_called_once()
    mock_process_concat.assert_called_once()
    mock_save_df.assert_called_once()
    mock_store_lm_file.assert_called_once_with(LAST_MODIFIED_FILE, "same_timestamp")
    assert "output files are missing. Proceeding with download and processing." in caplog.text
    mock_sys_exit.assert_not_called() # Should finish successfully


def test_main_first_run_no_last_modified_file(mocker, caplog, mock_sys_exit):
    """
    Test main logic for a first run where LAST_MODIFIED_FILE does not exist:
    - PDF should be fetched, processed, and saved.
    - New timestamp stored.
    """
    mock_get_current_lm = mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="new_timestamp")
    # get_stored_last_modified will return None if file doesn't exist due to os.path.exists mock
    mock_get_stored_lm = mocker.patch('gerar_tabelas.get_stored_last_modified', return_value=None)
    # Mock os.path.exists to return False for LAST_MODIFIED_FILE, True for others if needed (though not strictly for this test)
    mocker.patch('os.path.exists', lambda path: False if path == LAST_MODIFIED_FILE else True)


    sample_raw_df_data = create_raw_df([['JAN', '1.000,00']], ['2023'])
    mock_pdf_tables = [MockCamelotTable(sample_raw_df_data.values.tolist())]
    mock_fetch_parse = mocker.patch('gerar_tabelas.fetch_and_parse_pdf', return_value=mock_pdf_tables)

    processed_df_data = {'Ano-Mês': ['2023-01'], 'Fator': [1000.0]}
    mock_processed_df = pd.DataFrame(processed_df_data).set_index('Ano-Mês')
    mock_process_concat = mocker.patch('gerar_tabelas.process_and_concatenate_tables', return_value=mock_processed_df)

    mock_save_df = mocker.patch('gerar_tabelas.save_dataframes', return_value=True)
    mock_store_lm_file = mocker.patch('gerar_tabelas.store_last_modified_to_file')

    main()

    mock_fetch_parse.assert_called_once()
    mock_process_concat.assert_called_once()
    mock_save_df.assert_called_once()
    mock_store_lm_file.assert_called_once_with(LAST_MODIFIED_FILE, "new_timestamp")
    assert "PDF has been updated, was not processed before" in caplog.text
    mock_sys_exit.assert_not_called()


def test_main_get_current_lm_fails(mocker, caplog, mock_sys_exit):
    """Test main logic when fetching server Last-Modified timestamp fails."""
    mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value=None)

    mock_fetch_parse = mocker.patch('gerar_tabelas.fetch_and_parse_pdf')
    # mock_sys_exit = mocker.patch('sys.exit') # Already mocked by fixture

    main()

    mock_fetch_parse.assert_not_called()
    assert "Could not determine server's Last-Modified time." in caplog.text
    mock_sys_exit.assert_called_once_with(1)


def test_main_fetch_and_parse_pdf_fails(mocker, caplog, mock_sys_exit):
    """Test main logic when fetch_and_parse_pdf returns None (simulating failure)."""
    mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="new_timestamp")
    mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="old_timestamp")
    mocker.patch('os.path.exists', return_value=True)

    mocker.patch('gerar_tabelas.fetch_and_parse_pdf', return_value=None) # Simulate failure

    mock_process_concat = mocker.patch('gerar_tabelas.process_and_concatenate_tables')
    # mock_sys_exit = mocker.patch('sys.exit')

    main()

    mock_process_concat.assert_not_called()
    assert "Exiting due to failure in fetching or parsing PDF." in caplog.text
    mock_sys_exit.assert_called_once_with(1)


def test_main_fetch_and_parse_pdf_raises_exception(mocker, caplog, mock_sys_exit):
    """Test main logic when fetch_and_parse_pdf raises an unexpected exception."""
    mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="new_timestamp")
    mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="old_timestamp")
    mocker.patch('os.path.exists', return_value=True)

    mocker.patch('gerar_tabelas.fetch_and_parse_pdf', side_effect=Exception("Camelot generic error"))

    mock_process_concat = mocker.patch('gerar_tabelas.process_and_concatenate_tables')
    # mock_sys_exit = mocker.patch('sys.exit')

    # fetch_and_parse_pdf itself has a try-except that prints and returns None.
    # So, the behavior will be the same as returning None.
    main()

    mock_process_concat.assert_not_called()
    assert "Error reading or parsing PDF: Exception - Camelot generic error" in caplog.text # Logged by fetch_and_parse_pdf
    assert "Exiting due to failure in fetching or parsing PDF." in caplog.text # Logged by main
    mock_sys_exit.assert_called_once_with(1)


def test_main_camelot_returns_empty_tables_list(mocker, caplog, mock_sys_exit):
    """Test main logic when fetch_and_parse_pdf returns an empty list (no tables found)."""
    mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="new_timestamp")
    mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="old_timestamp")
    mocker.patch('os.path.exists', return_value=True)

    # fetch_and_parse_pdf is mocked to return None if camelot.read_pdf returns empty list
    # based on its internal logic: `if not tables: return None`
    mocker.patch('gerar_tabelas.fetch_and_parse_pdf', return_value=None)

    mock_process_concat = mocker.patch('gerar_tabelas.process_and_concatenate_tables')
    # mock_sys_exit = mocker.patch('sys.exit')

    main()

    mock_process_concat.assert_not_called()
    assert "Exiting due to failure in fetching or parsing PDF." in caplog.text
    mock_sys_exit.assert_called_once_with(1)


def test_main_processing_fails_returns_empty_df(mocker, caplog, mock_sys_exit):
    """Test main logic when process_and_concatenate_tables returns an empty DataFrame."""
    mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="new_timestamp")
    mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="old_timestamp")
    mocker.patch('os.path.exists', return_value=True)

    sample_raw_df_data = create_raw_df([['JAN', '1.000,00']], ['2023'])
    mock_pdf_tables = [MockCamelotTable(sample_raw_df_data.values.tolist())]
    mocker.patch('gerar_tabelas.fetch_and_parse_pdf', return_value=mock_pdf_tables)

    mocker.patch('gerar_tabelas.process_and_concatenate_tables', return_value=pd.DataFrame()) # Empty DataFrame

    mock_save_df = mocker.patch('gerar_tabelas.save_dataframes')
    # mock_sys_exit = mocker.patch('sys.exit')

    main()

    mock_save_df.assert_not_called() # save_dataframes itself checks for empty df
    assert "Exiting because the final DataFrame is empty after processing." in caplog.text
    mock_sys_exit.assert_called_once_with(1)


def test_main_processing_raises_exception(mocker, caplog, mock_sys_exit):
    """Test main logic when process_and_concatenate_tables raises an exception."""
    mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="new_timestamp")
    mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="old_timestamp")
    mocker.patch('os.path.exists', return_value=True)

    sample_raw_df_data = create_raw_df([['JAN', '1.000,00']], ['2023'])
    mock_pdf_tables = [MockCamelotTable(sample_raw_df_data.values.tolist())]
    mocker.patch('gerar_tabelas.fetch_and_parse_pdf', return_value=mock_pdf_tables)

    mocker.patch('gerar_tabelas.process_and_concatenate_tables', side_effect=Exception("Processing boom!"))

    mock_save_df = mocker.patch('gerar_tabelas.save_dataframes')
    # mock_sys_exit = mocker.patch('sys.exit')

    # The exception in process_and_concatenate_tables is caught internally and returns empty df
    # So main should behave as if an empty df was returned.
    main()

    mock_save_df.assert_not_called()
    assert "Error concatenating processed tables: Exception - Processing boom!" in caplog.text # Log from process_and_concatenate_tables
    assert "Exiting because the final DataFrame is empty after processing." in caplog.text # Log from main
    mock_sys_exit.assert_called_once_with(1)


def test_main_saving_json_fails(mocker, caplog, mock_sys_exit):
    """Test main logic when save_dataframes fails (e.g., JSON saving error)."""
    mocker.patch('gerar_tabelas.get_current_last_modified_from_server', return_value="new_timestamp")
    mocker.patch('gerar_tabelas.get_stored_last_modified', return_value="old_timestamp")
    mocker.patch('os.path.exists', return_value=True)

    sample_raw_df_data = create_raw_df([['JAN', '1.000,00']], ['2023'])
    mock_pdf_tables = [MockCamelotTable(sample_raw_df_data.values.tolist())]
    mocker.patch('gerar_tabelas.fetch_and_parse_pdf', return_value=mock_pdf_tables)

    processed_df_data = {'Ano-Mês': ['2023-01'], 'Fator': [1000.0]}
    mock_processed_df = pd.DataFrame(processed_df_data).set_index('Ano-Mês')
    mocker.patch('gerar_tabelas.process_and_concatenate_tables', return_value=mock_processed_df)

    mocker.patch('gerar_tabelas.save_dataframes', return_value=False) # Simulate saving failure

    mock_store_lm_file = mocker.patch('gerar_tabelas.store_last_modified_to_file')
    # mock_sys_exit = mocker.patch('sys.exit')

    main()

    mock_store_lm_file.assert_not_called() # Timestamp should not be stored if saving failed
    assert "Script finished with errors during saving." in caplog.text
    mock_sys_exit.assert_called_once_with(1)

# Example of how you might test a specific helper if needed, e.g. get_stored_last_modified
def test_get_stored_last_modified_file_exists(mocker):
    mocker.patch('os.path.exists', return_value=True)
    mock_file_content = "timestamp_from_file"
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_file_content))

    result = gerar_tabelas.get_stored_last_modified("dummy_path")
    assert result == mock_file_content
    # builtins.open.assert_called_once_with("dummy_path", 'r') # open is a bit tricky to assert with mock_open

def test_get_stored_last_modified_file_not_exists(mocker):
    mocker.patch('os.path.exists', return_value=False)
    mock_open_func = mocker.patch('builtins.open', mocker.mock_open()) # Should not be called

    result = gerar_tabelas.get_stored_last_modified("dummy_path")
    assert result is None
    mock_open_func.assert_not_called()

def test_get_stored_last_modified_io_error(mocker, caplog):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', side_effect=IOError("File read error"))

    result = gerar_tabelas.get_stored_last_modified("dummy_path")
    assert result is None
    assert "Error reading stored Last-Modified timestamp" in caplog.text
    assert "IOError - File read error" in caplog.text
