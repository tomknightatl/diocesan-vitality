# Workflow for extract_parishes.py

This document outlines the process flow of the `extract_parishes.py` script, which is responsible for extracting parish data from U.S. Catholic dioceses.

The diagram below illustrates the step-by-step logic of the script.

```mermaid
graph TD
    A[Start] --> B{Parse CLI Args};
    B --> C[Ensure Chrome Installed];
    C -- Success --> D[Initialize Supabase Client];
    C -- Failure --> F[Error: Chrome Not Installed];
    D -- Success --> G{Determine Dioceses to Process};
    D -- Failure --> F[Error: Supabase Init Failed];

    G -- Specific Diocese ID --> H[Fetch Diocese by ID & Directory URL];
    G -- All Dioceses --> I[Fetch All Dioceses with Directory URLs];

    H --> J{Dioceses Found?};
    I --> J;
    J -- Yes --> K[Setup WebDriver];
    J -- No --> L[Exit: No Dioceses to Process];

    K -- Success --> M[Loop Through Each Diocese];
    K -- Failure --> F[Error: WebDriver Setup Failed];

    M --> N[Process Diocese with Detailed Extraction];
    N --> O{Parishes Found?};
    O -- Yes --> P[Save Parishes to Supabase];
    O -- No --> M;
    P --> M;

    M -- Loop Finished --> Q[Close WebDriver];
    Q --> R[End];

    F --> R;
    L --> R;
```
