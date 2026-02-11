graph TD
    classDef actor fill:#f5f5f5,stroke:#333,stroke-dasharray: 5 5;
    classDef internal fill:#d4ebf2,stroke:#0e5a71,stroke-width:2px;
    classDef external fill:#f9e4b7,stroke:#8a6d3b,stroke-width:2px;
    classDef storage fill:#dbfad6,stroke:#3b7a30,stroke-width:2px;

    User((Developer)) --> CLI[main.py]

    subgraph Setup [Startup and Model Setup]
        CLI --> Settings[build_settings]
        CLI --> ModelSelect[select_model_and_update_config]
        CLI --> OcrSelect[select_ocr_model_and_update_config]
        ModelSelect --> PersistLLM[(.appdata/config/llm_model.json)]
        OcrSelect --> PersistOCR[(.appdata/config/ocr_model.json)]
        ModelSelect --> LlmCatalog[(config.llm_model_spec)]
        OcrSelect --> OcrCatalog[(config.ocr_model_spec)]
        CLI --> Bootstrap[bootstrap_llm]
        Bootstrap --> HF[Hugging Face Hub]
        Bootstrap --> Models[(.appdata/models)]
    end

    CLI --> Container[build_container]

    subgraph Container [Container Services]
        Container --> LLMServer[LlmServerProcess]
        Container --> OCRServer[OcrServerProcess]
        Container --> LLMClient[OpenAICompatChatClient]
        Container --> OCRClient[OcrClient]
        Container --> LLMService[LlmService]
        Container --> LLMTasks[LlmTaskService]
        Container --> OCRService[OcrService]
        Container --> Discovery[InputDiscoveryService]
        Container --> InputSvc[DocumentInputService]
        Container --> OutputSvc[DocxOutputService]
        Container --> GedSvc[GedService]
    end

    subgraph Runtime [Main Runtime Pipelines]
        CLI --> Prep[PrepPipeline]
        CLI --> Metadata[MetadataPipeline]
        CLI --> GED[GEDPipeline]
        CLI --> TopicFB[FBPipeline]
        CLI --> ConclFB[ConclusionPipeline]
        CLI --> BodyFB[BodyPipeline]
        CLI --> ContentFB[ContentPipeline]
        CLI --> SummarizeFB[SummarizeFBPipeline]

        Prep --> Checked[(..._checked.docx)]
        Metadata --> Conc[(conc_para.docx)]
        TopicFB --> TS[(ts.docx)]
        TopicFB --> FB[(fb.docx)]
        ConclFB --> FB
        BodyFB --> FB
        ContentFB --> Comp[(comp_para.docx)]
        ContentFB --> FB
        SummarizeFB --> Checked
    end

    LLMTasks --> LLMService
    LLMService --> LLMClient
    LLMClient --> Llama[llama-server /v1/chat/completions]
    LLMServer --> Llama
    OCRServer --> Llama
    Llama --> Models

    class User actor;
    class CLI,Settings,ModelSelect,OcrSelect,Bootstrap,Container,Prep,Metadata,GED,TopicFB,ConclFB,BodyFB,ContentFB,SummarizeFB,LLMServer,OCRServer,LLMClient,OCRClient,LLMService,LLMTasks,OCRService,Discovery,InputSvc,OutputSvc,GedSvc internal;
    class HF,Llama external;
    class PersistLLM,PersistOCR,LlmCatalog,OcrCatalog,Models,Checked,Conc,TS,FB,Comp storage;
