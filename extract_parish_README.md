# Workflow for extract_schedule.py

This document outlines the process flow of the `extract_schedule.py` script, which is responsible for scraping parish websites to find adoration and reconciliation schedules.

The diagram below is rendered by GitHub and shows the step-by-step logic of the script.

```mermaid
graph TD
    A[Start] --> B{Parse CLI Args};
    B --> C[Load .env & Connect to Supabase];
    C --> D{Get Parishes to Process};
    D -- Parishes Found --> E[Loop Through Each Parish];
    D -- No Parishes Found --> F[Exit];
    E --> G[scrape_parish_data];
    G --> H{Initialize Priority Queue & Visited Set};
    H --> I{Fetch sitemap.xml};
    I -- Sitemap Found --> J[Add Sitemap URLs to Queue];
    I -- Sitemap Not Found/Error --> K;
    J --> K;
    H --> K[Start Scraping Loop (Max 100 pages)];
    K -- URLs in Queue --> L{Pop Highest Priority URL};
    K -- Queue Empty or Limit Reached --> V;
    L --> M{Fetch & Parse Page};
    M -- Error --> K;
    M -- Success --> N{Page Text Contains Keywords?};
    N -- "reconciliation / confession" --> O[Add to Reconciliation Candidates];
    N -- "adoration" --> P[Add to Adoration Candidates];
    O --> Q;
    P --> Q;
    N --> Q{Find All Links on Page};
    Q --> R[For Each New Link];
    R --> S{Calculate Link Priority};
    S --> T[Add Link to Priority Queue];
    T --> R;
    R -- Done with Links --> U[Log Visited URL];
    U --> K;
    V[Save Discovered URLs to Supabase] --> W{Choose Best URL for Reconciliation};
    W --> X{Extract Reconciliation Schedule Info};
    X --> Y{Choose Best URL for Adoration};
    Y --> Z{Extract Adoration Schedule Info};
    Z --> AA[Return Scraped Result];
    AA --> E;
    E -- Loop Finished --> BB[save_facts_to_supabase];
    BB --> CC{Format Scraped Results into Facts};
    CC --> DD[Upsert Facts to ParishData Table];
    DD --> EE[End];
```
