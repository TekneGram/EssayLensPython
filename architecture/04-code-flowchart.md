graph TD
    classDef config fill:#f9f,stroke:#333,stroke-width:2px;
    classDef core fill:#bbf,stroke:#333,stroke-width:2px;
    classDef nlp fill:#dfd,stroke:#333,stroke-width:1px;
    classDef io fill:#ffd,stroke:#333,stroke-width:1px;

    subgraph Initialization
        main[main.py] --> settings[app.settings.build_settings]
        settings --> cfg_mods[config.*]
        main --> llm_select[app.select_model.select_model_and_update_config]
        llm_select --> llm_spec[config.llm_model_spec]
        main --> ocr_select[app.select_ocr_model.select_ocr_model_and_update_config]
        ocr_select --> ocr_spec[config.ocr_model_spec]
        main --> bootstrap[app.bootstrap_llm.bootstrap_llm]
        main --> container[app.container.build_container]
    end

    container --> server_proc[nlp.llm.llm_server_process.LlmServerProcess]
    container --> llm_client[nlp.llm.llm_client.OpenAICompatChatClient]
    container --> llm_svc[services.llm_service.LlmService]
    container --> task_svc[services.llm_task_service.LlmTaskService]
    container --> input_svc[services.document_input_service.DocumentInputService]
    container --> output_svc[services.docx_output_service.DocxOutputService]

    subgraph Main_Pipeline_Order [main.py execution order]
        main --> prep[app.pipeline_prep.PrepPipeline]
        prep --> discover[InputDiscoveryService.discover]
        prep --> prep_write[write_plain_copy -> out_path]

        main --> metadata[app.pipeline_metadata.MetadataPipeline]
        metadata --> meta_tasks[extract_metadata_parallel]
        metadata --> write_meta[append metadata to out_path]
        metadata --> write_conc[write_plain_copy conc_para.docx]

        main --> ged[app.pipeline_ged.GEDPipeline]
        ged --> ged_detect[GedService.score]
        ged --> ged_fix[correct_grammar_parallel]
        ged --> ged_write[append_corrected_paragraph -> out_path]

        main --> topic_fb[app.pipeline_fb.FBPipeline]
        topic_fb --> ts_construct[construct_topic_sentence_parallel]
        topic_fb --> ts_write[write ts.docx]
        topic_fb --> ts_analyze[analyze_topic_sentence_parallel]
        topic_fb --> fb_write[write fb.docx]

        main --> concl_fb[app.pipeline_conclusion.ConclusionPipeline]
        concl_fb --> concl_analyze[analyze_conclusion_sentence_parallel]
        concl_fb --> concl_append[append_paragraphs -> fb.docx]

        main --> body_fb[app.pipeline_body.BodyPipeline]
        body_fb --> hedging_pass[analyze_hedging_parallel (all paragraphs, batched)]
        body_fb --> cause_pass[analyze_cause_effect_parallel (all paragraphs, batched)]
        body_fb --> cc_pass[analyze_compare_contrast_parallel (all paragraphs, batched)]
        body_fb --> body_append[append_paragraphs -> fb.docx]

        main --> content_fb[app.pipeline_content.ContentPipeline]
        content_fb --> content_pass[analyze_content_parallel (all paragraphs, batched)]
        content_fb --> comp_write[write comp_para.docx]
        content_fb --> filter_pass[filter_content_parallel from comp_para.docx]
        content_fb --> content_append[append_paragraphs -> fb.docx]

        main --> summarize_fb[app.pipeline_summarize_fb.SummarizeFBPipeline]
        summarize_fb --> summarize_pass[summarize_personalize_parallel from fb.docx]
        summarize_fb --> final_append[append_paragraphs -> out_path (Final Feedback)]
    end

    subgraph LLM_Runtime [LLM Runtime]
        task_svc --> svc_many[LlmService.chat_many]
        svc_many --> client_many[OpenAICompatChatClient.chat_many]
        client_many --> client_async[OpenAICompatChatClient.chat_async]
        client_async --> llama_server[(llama-server endpoint)]
        server_proc --> llama_server
    end

    subgraph Artifacts [Key Intermediate Files]
        out_doc[(..._checked.docx)]
        conc_doc[(conc_para.docx)]
        ts_doc[(ts.docx)]
        fb_doc[(fb.docx)]
        comp_doc[(comp_para.docx)]
    end

    prep_write --> out_doc
    write_conc --> conc_doc
    ts_write --> ts_doc
    fb_write --> fb_doc
    concl_append --> fb_doc
    body_append --> fb_doc
    comp_write --> comp_doc
    content_append --> fb_doc
    final_append --> out_doc

    class settings,llm_select,ocr_select,bootstrap,cfg_mods,llm_spec,ocr_spec config;
    class main,container,prep,metadata,ged,topic_fb,concl_fb,body_fb,content_fb,summarize_fb,task_svc,llm_svc,svc_many core;
    class llm_client,server_proc,client_many,client_async,llama_server,meta_tasks,ged_fix,ts_construct,ts_analyze,concl_analyze,hedging_pass,cause_pass,cc_pass,content_pass,filter_pass,summarize_pass nlp;
    class input_svc,output_svc,out_doc,conc_doc,ts_doc,fb_doc,comp_doc,prep_write,write_meta,write_conc,ged_write,ts_write,fb_write,concl_append,body_append,comp_write,content_append,final_append io;
