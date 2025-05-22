**Roadmap Proposal**

**Phase 1: Core Functionality & Reliability**

1.  **Integrate Data into Frontend (`index.html`):**
    *   Modify the `fetchFactor(date)` JavaScript function in `index.html` to:
        *   Fetch data from the local `tabela_de_atualizacao_ec113.json` file.
        *   Implement logic to correctly parse user input dates and find the corresponding "Fator" from the JSON data for both "Update From" and "Update To" dates.
        *   Handle cases where data for a specific month/year might be missing.
    *   **Goal:** Make the "Vanilla JS Finance Tracker" fully functional using the periodically updated data.

2.  **Improve `gerar_tabelas.py` Robustness:**
    *   Enhance the Python script by:
        *   Adding `try-except` blocks for network requests and file operations.
        *   Implementing basic logging for successful runs or errors.
        *   Checking for empty data after PDF parsing.
    *   **Goal:** Make the data scraping process more resilient.

3.  **Expand `README.md` Documentation:**
    *   Update `README.md` to include:
        *   A clear description of the project's purpose.
        *   Explanation of how `gerar_tabelas.py` works.
        *   Instructions on how to use `index.html`.
        *   A brief mention of the automated daily update.
    *   **Goal:** Make the project understandable to new users or contributors.

**Phase 2: Automation & Developer Experience**

1.  **Enhance GitHub Actions Workflow:**
    *   Modify `.github/workflows/daily_script_run.yml` to:
        *   Add caching for pip dependencies.
        *   Update the commit message to be more informative (e.g., "Automated update of EC113 tables").
    *   **Goal:** Speed up the workflow and improve tracking of automated changes.

2.  **Add `requirements.txt`:**
    *   Create a `requirements.txt` file listing Python dependencies and their versions.
    *   **Goal:** Simplify local development setup.

3.  **Code Styling and Linting Setup (Optional but Recommended):**
    *   Introduce tools like Black and Flake8 for Python, and Prettier for HTML/JavaScript.
    *   Optionally, add a GitHub Action step for checking formatting/linting.
    *   **Goal:** Maintain consistent code quality and readability.

**Phase 3: Advanced Features & Future Development**

1.  **Advanced Frontend Features for `index.html`:**
    *   Improve the web interface by:
        *   Moving inline JavaScript to a separate `script.js` file.
        *   Adding UI feedback like loading indicators.
        *   Implementing input validation with clearer error messages.
    *   **Goal:** Improve user experience and frontend maintainability.

2.  **Deeper `gerar_tabelas.py` Enhancements:**
    *   Refine the data processing script by:
        *   Moving the PDF URL to a configuration variable or file.
        *   Implementing a mechanism to download/process the PDF only if it has been updated.
    *   **Goal:** Make the script more configurable and efficient.

3.  **Data Visualization:**
    *   Introduce charts in `index.html` (e.g., using Chart.js) to display the trend of "Fator" over time.
    *   **Goal:** Provide users with a visual understanding of the data.
