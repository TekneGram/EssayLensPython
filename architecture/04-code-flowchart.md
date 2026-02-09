graph TD
    %% Styling
    classDef config fill:#f9f,stroke:#333,stroke-width:2px;
    classDef core fill:#bbf,stroke:#333,stroke-width:2px;
    classDef nlp fill:#dfd,stroke:#333,stroke-width:1px;
    classDef io fill:#ffd,stroke:#333,stroke-width:1px;

    %% Level 1: Initialization
    subgraph Initialization
        main[main.py] -- "AppConfig" --> settings[app.settings]
        settings -- "Config objects" --> cfg_mods[config.*]
        main -- "Update config from choice" --> select[app.select_model]
        select -- "Model metadata" --> model_spec[config.llm_model_spec]
        main -- "Resolve artifacts" --> bootstrap[app.bootstrap_llm]
    end

    %% Level 2: Dependency Wiring
    bootstrap -- "Resolved model + server paths" --> container[app.container]
    container -- "Injected instances" --> pipeline[app.pipeline]

    %% Level 3: Pipeline & Task Execution
    subgraph Pipeline_Execution [Pipeline and Tasks]
        pipeline -- "run_test(app_cfg)" --> llm_svc[services.llm_service]
        llm_svc -- "run_parallel_kv_cache_test" --> task_runner[nlp.llm.tasks.test_parallel]
        task_runner -- "ChatRequest[]" --> llm_svc
    end

    %% Level 4: LLM Client and Server Process
    subgraph LLM_Runtime [LLM Runtime]
        llm_svc -- "chat_many / chat_async" --> llm_client[nlp.llm.llm_client]
        container -- "start/stop lifecycle" --> server_proc[nlp.llm.llm_server_process]
        llm_client -- "HTTP JSON" --> llama_server[(llama-server endpoint)]
        server_proc -- "subprocess + health checks" --> llama_server
    end

    %% Level 5: Persistence and Output
    subgraph Persistence_Output [Persistence and Output]
        select -- "Persist selected model key" --> sel_store[(.appdata/config/llm_model.json)]
        bootstrap -- "Download GGUF/mmproj" --> model_store[(.appdata/models)]
        pipeline -- "print ChatResponse/results" --> terminal[utils.terminal_ui]
    end

    %% Interfaces
    pipeline -. "Typed by" .-> app_shape[interfaces.config.app_config]

    %% Assign Classes
    class settings,select,bootstrap,cfg_mods,model_spec,app_shape config;
    class main,container,pipeline,llm_svc core;
    class llm_client,server_proc,task_runner,llama_server nlp;
    class sel_store,model_store,terminal io;
