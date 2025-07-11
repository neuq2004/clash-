import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config_file = "config.json"
        self.default_config = {
            "paths": {
                "output_dir": "D:\\RTMP_Downloads",
                "ffmpeg_path": "ffmpeg",
                "yt_dlp_path": "yt-dlp",
                "log_dir": "logs"
            },
            "download": {
                "min_file_size_mb": 50,
                "download_timeout": 120,
                "startup_timeout": 60,
                "max_concurrent_downloads": 5,
                "auto_retry": True,
                "retry_count": 3
            },
            "notification": {
                "server_chan_key": "",
                "enable_desktop": True,
                "enable_sound": True,
                "sound_files": {
                    "success": "",
                    "warning": "",
                    "error": ""
                }
            },
            "ui": {
                "theme": "light",
                "font_family": "Microsoft YaHei UI",
                "font_size": 10,
                "window_size": [1200, 800],
                "language": "zh_CN"
            },
            "advanced": {
                "enable_auto_detect": False,
                "check_interval": 300,
                "enable_segment_recording": False,
                "segment_duration": 3600
            }
        }
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置和用户配置
                return self.merge_config(self.default_config, config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.default_config.copy()
        else:
            self.save_config(self.default_config)
            return self.default_config.copy()
    
    def save_config(self, config=None):
        """保存配置文件"""
        if config is None:
            config = self.config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def merge_config(self, default, user):
        """合并默认配置和用户配置"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key_path, default=None):
        """获取配置值，支持点号分隔的路径"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path, value):
        """设置配置值"""
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self.save_config()