# Workflow for find_parishes.py

This document outlines the process flow of the `find_parishes.py` script, which is responsible for finding parish directory URLs on diocesan websites using web scraping, GenAI, and search engine fallbacks.

The diagram below illustrates the step-by-step logic of the script.

```mermaid
graph TD
    A[Start] --> B{Parse CLI Args};
    B --> C[Validate Configuration];
    C --> D[Configure GenAI / Set Mock];
    D --> E[Initialize Supabase Client];
    E -- Success --> F{Determine Dioceses to Scan};
    E -- Failure --> G[Error: Supabase Init Failed];

    F -- No Dioceses --> H[Exit: No Dioceses to Scan];
    F -- Dioceses Found --> I[Setup Selenium WebDriver];
    I -- Success --> J[Loop Through Each Diocese];
    I -- Failure --> G[Error: WebDriver Setup Failed];

    J --> K{Process Diocese};
    K --> L[Fetch Diocese Website (Selenium)];
    L -- Success --> M[Find Candidate URLs on Page];
    L -- Failure --> N[Handle Page Load Error];

    M --> O{Candidate URLs Found?};
    O -- Yes --> P[Analyze Links with GenAI (Direct Page)];
    O -- No --> Q[Fallback to Search Engine];

    P --> R{GenAI Found Best Link?};
    R -- Yes --> S[Parish Dir URL Found];
    R -- No --> Q;

    Q --> T{Search Engine Found Results?};
    T -- Yes --> U[Analyze Search Snippets with GenAI];
    T -- No --> V[No Parish Dir URL Found];

    U --> W{GenAI Found Best Link from Snippet?};
    W -- Yes --> S;
    W -- No --> V;

    S --> X[Upsert Result to Supabase];
    V --> X;
    N --> X;

    X --> Y[Log Result & Status];
    Y --> J;

    J -- Loop Finished --> Z[Close WebDriver];
    Z --> AA[End];

    G --> AA;
    H --> AA;
    N --> AA;
```
