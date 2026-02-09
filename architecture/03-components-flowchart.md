graph LR
    %% Styling
    classDef runner fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef pipe fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef llm fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef ext fill:#eceff1,stroke:#263238,stroke-dasharray: 5 5;

    %% Level 1: CLI Runner (Orchestrator)
    subgraph CLI_Runner [CLI Runner]
        user((Developer)) --> run[main]
        run --> settings[build_settings]
        run --> chooser[select_model_and_update_config]
        run --> bootstrap[bootstrap_llm]
        run --> container[build_container]
    end

    %% Level 2: Setup to Execution
    chooser --> model_specs[MODEL_SPECS]
    chooser --> persisted_key[Persisted model key]
    bootstrap --> model_store[Model Store (.appdata/models)]
    container --> server[Llama Server Process]
    container --> pipeline_core[Test Pipeline Core]

    %% Level 3: Pipeline Core and Sub-components
    subgraph Pipeline_Engine [Pipeline Engine]
        pipeline_core --> mode[with_mode(no_think)]
        pipeline_core --> parallel_task[run_parallel_test]
        parallel_task --> llm_svc[LlmService.chat_many]
    end

    %% Level 4: LLM Client Layer
    subgraph LLM_Client_Layer [LLM Client Layer]
        llm_svc --> req_build[ChatRequest fan-out]
        req_build --> client_async[OpenAICompatChatClient.chat_async]
    end

    %% Level 5: External Process & Terminal Output
    client_async -- "HTTP" --> llama_bin[[llama-server]]
    server -- "Start/stop/manage" --> llama_bin
    llama_bin -- "Loads" --> model_store
    pipeline_core --> output[Terminal result reporter]

    %% Assign Classes
    class run,settings,chooser,bootstrap,container runner;
    class pipeline_core,mode,parallel_task,llm_svc,req_build,output pipe;
    class client_async,server llm;
    class llama_bin,model_specs,persisted_key,model_store ext;
