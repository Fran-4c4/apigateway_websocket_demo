

from dotenv import load_dotenv
from pathlib import Path
import os

def load_env(env_file_name,env_type="DEV",env_folder=".envs") -> None:
    """load environment data for app
    this is stored in user´s home directory as .env.env_file_name.DEV

    Args:
        env_file_name (str): the name of the environment file
        env_name (str, optional): _description_. Defaults to "DEV".
        env_folder (str, optional): _description_. Defaults to ".envs".
    """        
    # Get the user's home directory
    home_dir = Path(os.path.expanduser('~'))
    # Build the path to the environment file (e.g., .env.development or .env.production)
    fname=f'.env.{env_file_name}'
    if env_type:
        fname+="." + env_type
    env_file = home_dir / env_folder / fname

    # Load the environment file
    load_dotenv(dotenv_path=env_file)