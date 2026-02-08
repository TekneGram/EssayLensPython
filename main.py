from utils.terminal_ui import Color, type_print, stage

from app.settings import build_settings

def main():
    # Handle environment variables for production vs dev later
    type_print("Building settings", color=Color.BLUE)
    app_cfg = build_settings()
    print(app_cfg)

if __name__ == "__main__":
    main()