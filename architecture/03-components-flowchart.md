graph LR
    classDef runner fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef pipe fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef llm fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef ocr fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    classDef ext fill:#eceff1,stroke:#263238,stroke-dasharray: 5 5;

    subgraph CLI_Runner [CLI Runner]
        user((Developer)) --> run[main.py]
        run --> settings[build_settings]
        run --> llm_chooser[select_model_and_update_config]
        run --> ocr_chooser[select_ocr_model_and_update_config]
        run --> llm_bootstrap[bootstrap_llm]
        run --> container[build_container]
        run --> prep[PrepPipeline.run_pipeline]
        run --> metadata[MetadataPipeline.run_pipeline]
        run --> ged[GEDPipeline.run_pipeline]
        run --> topic_fb[FBPipeline.run_pipeline]
        run --> concl_fb[ConclusionPipeline.run_pipeline]
        run --> body_fb[BodyPipeline.run_pipeline]
        run --> content_fb[ContentPipeline.run_pipeline]
        run --> summarize_fb[SummarizeFBPipeline.run_pipeline]
    end

    llm_chooser --> llm_model_specs[config.llm_model_spec]
    llm_chooser --> llm_persisted_key[.appdata/config/llm_model.json]
    ocr_chooser --> ocr_model_specs[config.ocr_model_spec]
    ocr_chooser --> ocr_persisted_key[.appdata/config/ocr_model.json]
    ocr_chooser --> model_store[.appdata/models]
    llm_bootstrap --> model_store

    subgraph Container_Wiring [Container Wiring]
        container --> llm_server[LlmServerProcess]
        container --> llm_client[OpenAICompatChatClient]
        container --> llm_service[LlmService]
        container --> llm_task_service[LlmTaskService]
        container --> input_discovery[InputDiscoveryService]
        container --> input_service[DocumentInputService]
        container --> output_service[DocxOutputService]
        container --> ged_service[GedService]
        container --> ocr_server[OcrServerProcess]
        container --> ocr_service[OcrService]
    end

    subgraph File_Artifacts [Pipeline File Artifacts]
        prep --> out_docx[(..._checked.docx)]
        metadata --> conc_para[(conc_para.docx)]
        topic_fb --> ts_docx[(ts.docx)]
        topic_fb --> fb_docx[(fb.docx)]
        concl_fb --> fb_docx
        body_fb --> fb_docx
        content_fb --> comp_para[(comp_para.docx)]
        content_fb --> fb_docx
        summarize_fb --> out_docx
    end

    subgraph LLM_Client_Layer [LLM Client Layer]
        llm_task_service --> task_chat_many[LlmService.chat_many]
        task_chat_many --> client_many[OpenAICompatChatClient.chat_many]
        client_many --> client_async[OpenAICompatChatClient.chat_async]
    end

    client_async -- "HTTP" --> llama_bin[[llama-server]]
    llm_server --> llama_bin
    llama_bin --> model_store
    ocr_server --> llama_bin

    class run,settings,llm_chooser,ocr_chooser,llm_bootstrap,container,prep,metadata,ged,topic_fb,concl_fb,body_fb,content_fb,summarize_fb runner;
    class llm_service,llm_task_service,task_chat_many,client_many,client_async,llm_server llm;
    class ocr_server,ocr_service ocr;
    class model_store,llm_model_specs,llm_persisted_key,ocr_model_specs,ocr_persisted_key,conc_para,ts_docx,fb_docx,comp_para,out_docx ext;
