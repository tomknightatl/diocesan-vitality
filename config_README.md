# config.py

`config.py` is responsible for loading environment variables and defining application-wide configuration constants.

## Purpose

- **Environment Variable Loading**: It uses `dotenv` to load variables such as `SUPABASE_URL`, `SUPABASE_KEY`, `GENAI_API_KEY`, `SEARCH_API_KEY`, and `SEARCH_CX` from the `.env` file.
- **Default Constants**: Defines default values for pipeline parameters, such as `DEFAULT_MAX_DIOCESES`, `DEFAULT_MAX_PARISHES_PER_DIOCESE`, and `DEFAULT_NUM_PARISHES_FOR_SCHEDULE`.
- **Configuration Validation**: Includes a `validate_config()` function that checks if all necessary environment variables have been successfully loaded, providing warnings if any are missing.

This file ensures that the application has access to essential settings and API keys, and that the configuration is valid before execution.
