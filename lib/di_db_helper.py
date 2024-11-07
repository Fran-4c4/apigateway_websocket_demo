import os
from .db_helper_postgress import DBHelperPostgress


class DIDBHelper:
    """Static singleton pattern for database helper selection."""
    
    _instance = None  # Class-level variable to hold the singleton instance
    db_helper_classes = {
        "DBHelperPostgress": DBHelperPostgress,
    }

    def __init__(self):
        """Private initializer to prevent instantiation outside of get_instance."""
        if DIDBHelper._instance is not None:
            raise RuntimeError("Use get_instance() to get the singleton instance")
        
        # Automatically configure the instance based on environment variable
        class_name = os.getenv("db_handler", "DBHelperPostgress")
        if class_name not in DIDBHelper.db_helper_classes:
            raise ValueError(f"Unknown class: {class_name}")
        
        # Set the implementation based on the environment variable
        self.implementation = DIDBHelper.db_helper_classes[class_name]

    @classmethod
    def get_instance(cls):
        """Returns the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def resolve(self):
        """Creates and returns a new instance of the configured DB helper."""
        return self.implementation()  # Create a new instance of the configured class

# Usage
if __name__ == '__main__':
    from .load_env import load_env
    load_env(env_file_name="apigateway")

    # Get the singleton instance of DIDBHelper and resolve a new DB helper instance
    db = DIDBHelper.get_instance().resolve()
    print(db)

