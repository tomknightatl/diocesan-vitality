# parish_extraction_core.py

`parish_extraction_core.py` contains core functionalities and helper utilities used across various parish data extraction and management processes.

## Classes and Functions

### `class PatternDetector`

- **Purpose**: A utility class designed for detecting specific patterns within text using regular expressions. It can be initialized with a list of patterns and provides methods to check for their presence.

### `analyze_parish_finder_quality(url: str) -> dict`

- **Purpose**: Analyzes the quality or suitability of a given URL as a parish finder or directory. This function would typically assess the URL's content or structure to determine its relevance for locating parish information.
- **Args**:
    - `url`: The URL of the potential parish finder page.
- **Returns**: A dictionary containing analysis results, which might include a score, confidence level, or specific findings.

### `enhanced_safe_upsert_to_supabase(parishes_data: list, diocese_name: str, diocese_url: str, parish_directory_url: str, supabase_client) -> None`

- **Purpose**: Provides a robust and safe mechanism for upserting (inserting or updating) parish data into the Supabase database.
- **Features**:
    - Handles potential conflicts during upsert operations.
    - Logs detailed information about the upsert process, including successes and failures.
    - Ensures data integrity and provides feedback on the database operation.
- **Args**:
    - `parishes_data`: A list of dictionaries, where each dictionary represents a parish's data.
    - `diocese_name`: The name of the diocese associated with the parishes.
    - `diocese_url`: The main URL of the diocese.
    - `parish_directory_url`: The URL from which the parish data was extracted.
    - `supabase_client`: An initialized Supabase client instance.
