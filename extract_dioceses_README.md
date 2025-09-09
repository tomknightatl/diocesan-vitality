# Workflow for extract_dioceses.py

This document outlines the process flow of the `extract_dioceses.py` script, which is responsible for extracting diocese information from the USCCB website.

The diagram below illustrates the step-by-step logic of the script.

```mermaid
graph TD
    A[Start] --> B{Parse CLI Args};
    B --> C[Validate Configuration];
    C --> D[Construct USCCB Dioceses URL];
    D --> E{Fetch Page Content (get_soup)};
    E -- Success --> F[Parse HTML];
    E -- Failure --> G[Error: Failed to Fetch Page];

    F --> H[Extract Dioceses Data];
    H --> I{Dioceses Extracted?};
    I -- Yes --> J[Apply Max Dioceses Limit];
    I -- No --> K[Warning: No Dioceses Extracted];

    J --> L[Initialize Supabase Client];
    L -- Success --> M[Upsert Data to Supabase 'Dioceses' Table];
    L -- Failure --> N[Error: Supabase Init Failed];

    M -- Success --> O[Log Success];
    M -- Failure --> P[Log Bulk Upsert Failure];

    G --> Q[End];
    K --> Q;
    N --> Q;
    O --> Q;
    P --> Q;
```
