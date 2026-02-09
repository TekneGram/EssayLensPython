graph TD
    classDef actor fill:#f5f5f5,stroke:#333,stroke-dasharray: 5 5;
    classDef internal fill:#d4ebf2,stroke:#0e5a71,stroke-width:2px;
    classDef external fill:#f9e4b7,stroke:#8a6d3b,stroke-width:2px;
    classDef storage fill:#dbfad6,stroke:#3b7a30,stroke-width:2px;

    User((Developer)) --> CLI[main.py]

    subgraph Setup [Startup and Model Setup]
        CLI --> Settings[build_settings]
        CLI --> ModelSelect[select_model_and_update_config]
        ModelSelect --> Persist[(.appdata/config/llm_model.json)]
        ModelSelect --> Catalog[(config.llm_model_spec)]
        CLI --> Bootstrap[bootstrap_llm]
        Bootstrap --> HF[Hugging Face Hub]
        Bootstrap --> Models[(.appdata/models)]
    end

    CLI --> Container[build_container]
    Container --> ServerProc[LlmServerProcess.start]
    Container --> LLMClient[OpenAICompatChatClient]
    Container --> LLMService[LlmService]

    CLI --> Pipeline[TestPipeline.run_test_again]
    Pipeline --> Tasks[build_feedback_tasks<br/>nlp.llm.tasks.test_parallel_2]
    Tasks --> DTOs[ChatRequest<br/>nlp.llm.llm_types]
    DTOs --> LLMService
    Pipeline --> Mode[with_mode no_think]
    Mode --> LLMService
    LLMService --> LLMClient
    LLMClient --> Llama[llama-server /v1/chat/completions]
    ServerProc --> Llama
    Llama --> Models
    CLI --> Terminal[(type_print output loop)]

    class User actor;
    class CLI,Settings,ModelSelect,Bootstrap,Container,Pipeline,Tasks,DTOs,LLMService,LLMClient,Mode,ServerProc internal;
    class HF,Llama external;
    class Persist,Catalog,Models,Terminal storage;
