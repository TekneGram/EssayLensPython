graph TD
    classDef config fill:#f9f,stroke:#333,stroke-width:2px;
    classDef core fill:#bbf,stroke:#333,stroke-width:2px;
    classDef nlp fill:#dfd,stroke:#333,stroke-width:1px;
    classDef io fill:#ffd,stroke:#333,stroke-width:1px;

    subgraph Initialization
        main[main.py] --> settings[app.settings.build_settings]
        settings --> cfg_mods[config.*]
        main --> select[app.select_model.select_model_and_update_config]
        select --> model_spec[config.llm_model_spec]
        main --> bootstrap[app.bootstrap_llm.bootstrap_llm]
    end

    bootstrap --> container[app.container.build_container]
    container --> server_proc[nlp.llm.llm_server_process.LlmServerProcess]
    container --> llm_client[nlp.llm.llm_client.OpenAICompatChatClient]
    container --> llm_svc[services.llm_service.LlmService]

    subgraph Pipeline_Execution [Current Main Path]
        main --> pipeline[app.pipeline.TestPipeline]
        pipeline --> run_again[run_test_again]
        run_again --> mode[llm.with_mode no_think]
        run_again --> task_builder[nlp.llm.tasks.test_parallel_2.build_feedback_tasks]
        task_builder --> dto_req[nlp.llm.llm_types.ChatRequest]
        dto_req --> llm_svc
        llm_svc --> svc_many[LlmService.chat_many]
    end

    subgraph LLM_Runtime [LLM Runtime]
        svc_many --> client_many[OpenAICompatChatClient.chat_many]
        client_many --> client_async[OpenAICompatChatClient.chat_async]
        client_async --> llama_server[(llama-server endpoint)]
        server_proc --> llama_server
    end

    subgraph Output [Output]
        main --> print_loop[type_print task outputs]
        select --> sel_store[(.appdata/config/llm_model.json)]
        bootstrap --> model_store[(.appdata/models)]
    end

    pipeline -. typed by .-> app_shape[interfaces.config.app_config]

    class settings,select,bootstrap,cfg_mods,model_spec,app_shape config;
    class main,container,pipeline,run_again,mode,llm_svc,svc_many core;
    class llm_client,server_proc,task_builder,dto_req,client_many,client_async,llama_server nlp;
    class sel_store,model_store,print_loop io;
