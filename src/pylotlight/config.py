import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    
    # Hook configurations
    HOOKS: Dict[str, Dict[str, Any]] = {
        'airflow': {
            'enabled': os.getenv('AIRFLOW_ENABLED', 'true').lower() == 'true',
            'polling_interval': int(os.getenv('AIRFLOW_POLLING_INTERVAL', 300)),
            'base_url': os.getenv('AIRFLOW_BASE_URL', 'http://localhost:8080/api/v1'),
            'api_user': os.getenv('AIRFLOW_API_USER','airflow'),
            'api_password': os.getenv('AIRFLOW_API_PASSWORD','airflow'),
        },
        # Add other hooks here as needed
    }

    @classmethod
    def get_hook_config(cls, hook_name: str) -> Dict[str, Any]:
        return cls.HOOKS.get(hook_name, {})

# Example usage:
# config = Config()
# airflow_config = config.get_hook_config('airflow')