# Competitor Intelligence Pipeline Flow

Here is the updated, simplified pipeline flow after ripping out the redundant DOM parsing strategies.

```mermaid
graph TD
    subgraph Ingestion_Layer [1. Ingestion Layer]
        A[Redis Task Queue] -->|Pop URL Task| B{Is SPA?}
        B -->|No| C[httpx AsyncClient]
        B -->|Yes| D[Playwright Headless]
        C --> E[Raw HTML Document]
        D --> E
    end

    subgraph Parsing_Engine [2. Parsing Engine]
        E --> F[DOM Block Segmenter]
        F --> G[JsonLdStrategy]
        G --> H{Confidence OK?}
        
        H -->|No| I[LLM Fallback API]
        I --> J[Parsed Result]
        H -->|Yes| J
    end

    subgraph Post_Processing [3. Post-Processing]
        J --> K[Entity Resolver Deduplication]
        K --> L[Relationship Engine]
    end

    subgraph Persistence_Layer [4. Persistence Layer]
        L --> M[PostgreSQL AsyncPG]
        M --> N[Real-Time Dashboard UI]
    end

    classDef default fill:#1E293B,stroke:#64748B,stroke-width:2px,color:#F8FAFC;
    classDef highlight fill:#3B82F6,stroke:#2563EB,color:#F8FAFC;
    classDef ai fill:#8B5CF6,stroke:#7C3AED,color:#F8FAFC;
    
    class I ai;
    class G highlight;
```

### Key Changes Reflected:
- **No more Strategy Loop:** Instead of cascading through 22 different CSS/DOM scrapers, the parsing engine immediately checks for `JsonLdStrategy` (Schema.org).
- **Direct to AI:** If the structured data is missing or incomplete (Confidence < 0.8), it routes the raw document straight to the Llama 3 model (`LLMFallbackService`) for intelligent extraction.
- **Deduplication:** Occurs after parsing via `EntityResolver` before hitting the database.
