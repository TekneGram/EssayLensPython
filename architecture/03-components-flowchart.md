graph LR
    classDef runner fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef pipe fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef llm fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef ext fill:#eceff1,stroke:#263238,stroke-dasharray: 5 5;

    subgraph CLI_Runner [CLI Runner]
        user((Developer)) --> run[main.py]
        run --> settings[build_settings]
        run --> chooser[select_model_and_update_config]
        run --> bootstrap[bootstrap_llm]
        run --> container[build_container]
        run --> pipeline[TestPipeline.run_test_again]
    end

    chooser --> model_specs[config.llm_model_spec]
    chooser --> persisted_key[.appdata/config/llm_model.json]
    bootstrap --> model_store[.appdata/models]

    subgraph Container_Wiring [Container Wiring]
        container --> server[LlmServerProcess.start]
        container --> llm_client[OpenAICompatChatClient]
        container --> llm_service[LlmService]
    end

    subgraph Pipeline_Engine [Pipeline Engine]
        pipeline --> mode[llm.with_mode no_think]
        pipeline --> task_builder[build_feedback_tasks]
        task_builder --> req_build[ChatRequest list]
        req_build --> llm_service
    end

    subgraph LLM_Client_Layer [LLM Client Layer]
        llm_service --> chat_many[LlmService.chat_many]
        chat_many --> client_many[OpenAICompatChatClient.chat_many]
        client_many --> client_async[OpenAICompatChatClient.chat_async]
    end

    client_async -- "HTTP" --> llama_bin[[llama-server]]
    server --> llama_bin
    llama_bin --> model_store
    run --> output[type_print output loop]

    class run,settings,chooser,bootstrap,container runner;
    class pipeline,mode,task_builder,req_build,llm_service,chat_many,output pipe;
    class llm_client,client_many,client_async,server llm;
    class llama_bin,model_specs,persisted_key,model_store ext;
