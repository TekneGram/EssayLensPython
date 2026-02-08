from utils.terminal_ui import Color, type_print, stage

from app.settings import build_settings
from app.select_model import select_model_and_update_config
from app.bootstrap_llm import bootstrap_llm

def main():
    # Handle environment variables for production vs dev later
    type_print("Building settings", color=Color.BLUE)
    app_cfg = build_settings()

    type_print("Selecting the best model for your system", color=Color.BLUE)
    app_cfg = select_model_and_update_config(app_cfg)

    type_print("Bootstrapping a large language model", color=Color.BLUE)
    app_cfg = bootstrap_llm(app_cfg)

    print(app_cfg)

if __name__ == "__main__":
    main()