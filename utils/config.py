import json
from pathlib import Path
from typing import Dict, Any

def load_company_config(company_name: str = "libanjus") -> Dict[str, Any]:
    """Load company-specific configuration."""
    config_path = Path(f"config/companies/{company_name}.json")
    if not config_path.exists():
        return {
            "name": company_name,
            "display_name": "LibanJus",
            "description": "Lebanese food products company",
            "icon": ":material/nutrition:",
            "color": "#2E8B57",
            "background_image_light": "data/libanjus/images/libanjus_bg_light.png",
            "background_image_dark": "data/libanjus/images/libanjus_bg_dark.png",
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)