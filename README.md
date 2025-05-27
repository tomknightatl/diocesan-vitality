# United States Conference of Catholic Bishops (USCCB) Data Project

## Overview

This project focuses on collecting, processing, and storing publicly available information about U.S. Catholic dioceses and parishes. Key data points include diocese names, addresses, websites, and links to parish directories. The project utilizes web scraping techniques and various data processing strategies implemented in Jupyter notebooks to build and maintain a local SQLite database (`data.db`). Some notebooks also explore experimental approaches for data extraction, such as using AI. The primary source for diocese information is the official USCCB website, supplemented by data from individual diocese sites for parish-level details.

## Project Structure

The project is organized around a few key components:

*   **Jupyter Notebooks (`.ipynb` files):** These are the core engines for data collection, processing, and interaction. Each notebook typically handles a specific task, such as scraping data from a particular source, transforming data, or querying the database. They are designed to be run in an environment like Google Colab.
*   **SQLite Database (`data.db`):** This single file acts as the central repository for all collected data. It contains various tables that store information about dioceses, parish directory URLs, and potentially detailed parish information. The notebooks read from and write to this database.
*   **Log Files (e.g., `scraping.log`):** Some scripts generate log files to track their progress and any issues encountered during processes like web scraping.
*   **License (`LICENSE`):** Contains the licensing information for the project.
*   **README (`README.md`):** This file, providing information about the project (meta!).

## Notebooks

The following Jupyter Notebooks are included in this project:

*   **`Build Dioceses Database.ipynb`**: Scrapes fundamental information about U.S. dioceses (name, address, website) from the official USCCB website (`usccb.org`) and populates the `Dioceses` table in `data.db`.
*   **`Find_Parish_Directory.ipynb`**: Iterates through the dioceses in `data.db` and attempts to find a URL for their parish directory/locator page by searching their respective websites. Stores results in the `DiocesesParishDirectory` table.
*   **`Build_Parishes_Database_From_Map.ipynb`**: (Assuming functionality based on name) Likely extracts parish information by interacting with map-based parish locators on diocese websites.
*   **`Build_Parishes_Database_From_Table.ipynb`**: (Assuming functionality based on name) Likely extracts parish information from tabular formats (e.g., HTML tables, PDFs) found on diocese websites.
*   **`Build_Parishes_Database_Using_AgenticAI.ipynb`**: Explores the use of AI (potentially Large Language Models) to assist in the extraction or processing of parish data.
*   **`Find_Adoration_and_Reconciliation_information_for_a_Parish.ipynb`**: (Assuming functionality based on name) Contains tools or scripts to query the database for specific parish details, such as Adoration and Reconciliation schedules, once that data is collected.
*   **`Clone_and_Update_GitHub_data.ipynb`**: A utility notebook likely focused on managing the `data.db` file within the Git repository, ensuring it's cloned, pulled, and changes are committed and pushed correctly.

*Note: The descriptions for notebooks not directly inspected are inferred from their names and may require verification for full accuracy.*

## Data

The primary output and central store of this project is `data.db`, an SQLite database file.

### Key Tables (examples):

*   **`Dioceses`**: Stores information about each diocese.
    *   `id`: Primary key.
    *   `Name`: Official name of the diocese.
    *   `Address`: Physical address of the chancery or main office.
    *   `Website`: Official website URL for the diocese.
*   **`DiocesesParishDirectory`**: Links dioceses to their parish directory URLs.
    *   `diocese_url`: The website URL of the diocese (acts as a foreign key).
    *   `parish_directory_url`: The URL pointing to the parish list/locator for that diocese.
    *   `found`: Status indicating if the parish directory URL was successfully found.
*   *(Other tables related to specific parish details might exist or be planned, depending on the progress of the data collection notebooks.)*

### Data Sources:

*   **USCCB Website (`usccb.org`):** The initial source for the list of dioceses and their primary contact information/websites.
*   **Individual Diocese Websites:** Scanned to find parish directory pages and, potentially, individual parish details.

The `data.db` file is included in this repository and is updated by the various notebooks as they collect and process information.

## Getting Started

This project primarily uses Python and Jupyter Notebooks, often run within the Google Colab environment.

### Prerequisites:

*   **Python 3.x**
*   **Jupyter Notebook or JupyterLab** (or access to Google Colab)
*   **Standard Python Libraries:**
    *   `requests`: For making HTTP requests to fetch web content.
    *   `BeautifulSoup4` (`bs4`): For parsing HTML and XML content.
    *   `pandas`: For data manipulation and analysis (though usage might be more for data structuring in some notebooks).
    *   `sqlite3`: For interacting with the SQLite database.
    *   `google-colab` (if running in Colab): For Colab-specific functionalities like `userdata`.

    These can generally be installed via pip:
    ```bash
    pip install requests beautifulsoup4 pandas
    ```
    (Note: `sqlite3` is part of the Python standard library. `google-colab` is specific to the Colab environment.)

### Setup and Running Notebooks:

1.  **Clone the Repository (Optional but Recommended):**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
    The notebooks themselves contain cells to clone or update the repository, especially when running in a fresh Colab environment.

2.  **GitHub Credentials for Data Pushing:**
    The notebooks that update `data.db` and push it back to GitHub (e.g., `Build Dioceses Database.ipynb`, `Find_Parish_Directory.ipynb`) use `google.colab.userdata` to fetch GitHub credentials (`GitHubUserforUSCCB`, `GitHubPATforUSCCB`). If you intend to run these notebooks and contribute data changes back to your own fork or the original repository (with appropriate permissions), you will need to:
    *   Fork the repository on GitHub.
    *   Configure these secrets in your Colab environment (or adapt the code if running locally) with your GitHub username and a Personal Access Token (PAT) that has repository write permissions.

3.  **Running Order:**
    *   It's generally recommended to run `Build Dioceses Database.ipynb` first to populate the initial list of dioceses.
    *   Subsequently, `Find_Parish_Directory.ipynb` can be run to find the parish directory URLs.
    *   Other notebooks can be run as needed, depending on the specific data you wish to collect or analyze.

4.  **Environment:**
    *   The notebooks are designed with Google Colab in mind, as indicated by `google.colab` imports and commands like `!git clone`. They can be adapted for local execution, but paths and credential management might need adjustments.

## Usage

### Running the Notebooks:

1.  **Open in Google Colab:** The simplest way to use these notebooks is to open them directly in Google Colab. Each notebook usually includes a badge/link for this purpose at the top.
2.  **Execute Cells:** Run the cells in the notebook sequentially. Pay attention to any output messages, especially for error handling or confirmation of steps.
3.  **Data Persistence:** The notebooks that modify the database (`data.db`) are designed to commit and push these changes to the GitHub repository. Ensure your environment is configured correctly (see "GitHub Credentials" under Getting Started) if you wish for these changes to be saved back to your fork or the repository.

### Accessing the Data:

*   **Directly via Notebooks:** The notebooks themselves often load data into pandas DataFrames for inspection or further processing.
*   **SQLite Browser:** The `data.db` file is a standard SQLite database. You can use any SQLite browser (e.g., DB Browser for SQLite) to open the file and explore its tables and data visually.
*   **Programmatically (Python):** You can access the data using Python's built-in `sqlite3` module in any Python script or environment:

    ```python
    import sqlite3
    import pandas as pd

    # Connect to the database
    conn = sqlite3.connect('data.db')

    # Example: Read the Dioceses table into a pandas DataFrame
    df_dioceses = pd.read_sql_query("SELECT * FROM Dioceses", conn)
    print(df_dioceses.head())

    # Example: Query for dioceses that have a parish directory URL
    df_with_parish_url = pd.read_sql_query("SELECT * FROM DiocesesParishDirectory WHERE parish_directory_url IS NOT NULL", conn)
    print(df_with_parish_url.head())

    # Close the connection
    conn.close()
    ```

## License

This project is licensed under the terms of the LICENSE file. Please see the `LICENSE` file in the root of the repository for more details.
