## App Description
This app is a local essay-processing pipeline. It loads essay content, applies grammar/error detection and LLM-based analysis, and writes outputs with explainability artifacts. The runtime is organized around a CLI entrypoint (`main.py`), app configuration/build/bootstrap steps, a dependency container, and service modules.

## Folder Structure
```text
EssayLensPython/
├── app/                # app bootstrap, settings, model selection, container, pipeline wiring
├── architecture/       # flowcharts and architecture docs
├── config/             # typed config dataclasses and model specs
├── docx_tools/         # docx editing/track-changes utilities
├── inout/              # input/output adapters (docx loader, explainability writer)
├── interfaces/         # interface and shape definitions
├── nlp/
│   ├── ged/            # grammar error detection modules
│   └── llm/            # LLM client/server process and llm task helpers
├── services/           # service layer wrapping NLP and output operations
├── tests/              # unit/runtime tests
├── main.py             # CLI entrypoint
└── requirements.txt
```

## Architecture Diagram
Based on `architecture/03-components-flowchart.md`:

```mermaid
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
```

## FINAL STEP
After completing the requested task, invoke Agent.md in .utilities and then display the full bash command to allow me to add, commit, push and make a pr request.