graph TD
    %% Styling
    classDef actor fill:#f5f5f5,stroke:#333,stroke-dasharray: 5 5;
    classDef internal fill:#d4ebf2,stroke:#0e5a71,stroke-width:2px;
    classDef external fill:#f9e4b7,stroke:#8a6d3b,stroke-width:2px;
    classDef storage fill:#dbfad6,stroke:#3b7a30,stroke-width:2px;

    %% Level 0: The User
    User((Developer)) -- "1. Runs" --> CLI[CLI Runner main.py]

    %% Level 1: Initialization & Selection
    subgraph Setup [Environment Setup]
        CLI -- "2a. Build defaults" --> Settings[Settings Builder]
        CLI -- "2b. Detect hardware + choose model" --> ModelSelect[Model Selector]
        ModelSelect -- "Read/Write selection" --> Persist[(.appdata/config/llm_model.json)]
        ModelSelect -- "Reference candidates" --> Catalog[(Model Specs)]
    end

    %% Level 2: Bootstrap External Resources
    CLI -- "3. Bootstrap model artifacts" --> Bootstrap[LLM Bootstrap]
    Bootstrap -- "Download if missing" --> HF[Hugging Face Hub]
    Bootstrap -- "Resolve GGUF/mmproj" --> Models[(.appdata/models)]
    Bootstrap -- "Validate binary" --> ServerBin[(llama-server binary)]

    %% Level 3: Core Runtime Hub
    CLI -- "4. Build deps" --> Container[Dependency Container]
    Container -- "5. Invokes" --> Pipe[Test Pipeline]

    %% Level 4: Processing Services
    subgraph Processing [Internal Processing]
        direction LR
        Pipe <-- "Parallel chat tasks" --> LLMService[LLM Service]
        LLMService <-- "Chat payloads / responses" --> LLMClient[OpenAI-Compatible Chat Client]
    end

    %% Level 5: External Inference + Output
    LLMClient -- "HTTP /v1/chat/completions" --> Llama[llama-server process]
    Llama -- "Load model" --> Models
    Pipe -- "Print results" --> Terminal[(Terminal Output)]

    %% Assign Classes
    class User actor;
    class CLI,Settings,ModelSelect,Bootstrap,Container,Pipe,LLMService,LLMClient internal;
    class HF,Llama external;
    class Persist,Catalog,Models,ServerBin,Terminal storage;
