"""Configuration loading with dataclasses and YAML defaults."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BrowserConfig:
    channel: str = "msedge"
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 800
    locale: str = "zh-CN"


@dataclass
class SearchConfig:
    pc_count: int = 30
    mobile_count: int = 20
    min_delay: float = 3.0
    max_delay: float = 8.0
    search_base_url: str = "https://www.bing.com/search"
    query_language: str = "mix"


@dataclass
class ActivitiesConfig:
    enabled: bool = True
    poll_choice: str = "random"
    quiz_search_delay: float = 2.5
    max_quiz_retries: int = 2
    more_activities_timeout: int = 30


@dataclass
class BehaviorConfig:
    max_retries: int = 3
    retry_delay: float = 5.0
    save_state_on_exit: bool = True
    state_file: str = "auth_state.json"
    log_level: str = "INFO"


@dataclass
class Config:
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    activities: ActivitiesConfig = field(default_factory=ActivitiesConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)


def _dict_to_dataclass(data: dict, cls: type) -> Any:
    """Recursively convert a dict to a dataclass instance."""
    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs = {}
    for key, value in data.items():
        if key not in field_types:
            continue
        if isinstance(value, dict) and hasattr(field_types[key], "__dataclass_fields__"):
            kwargs[key] = _dict_to_dataclass(value, field_types[key])
        else:
            kwargs[key] = value
    return cls(**kwargs)


def load_config(path: Path = Path("config.yaml")) -> Config:
    """Load configuration from YAML file, applying defaults for missing keys."""
    if not path.exists():
        return Config()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _dict_to_dataclass(raw, Config)
