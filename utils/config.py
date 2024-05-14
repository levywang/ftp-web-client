import json
from typing import List


class Config:
    # Singleton pattern for global configuration management, commented out for now to focus on function documentation and logic.
    config = None  # Class variable to store configuration data

    def __init__(self, config_file):
        """
        Initializes a Config instance and loads the configuration file.

        Args:
            config_file (str): The path to the configuration file.
        """
        self.config_file = config_file
        if self.config is None:
            with open(config_file, 'r', encoding="utf-8") as f:
                self.config = json.load(f)

    def get(self, *keys):
        """
        Retrieves a configuration value using the specified keys.

        Args:
            *keys: Variable-length arguments representing the configuration keys to retrieve, can be multi-level keys.

        Returns:
            Returns the configuration value or None if the specified key doesn't exist.
        """
        result = self.config
        for key in keys:
            result = result.get(key, None)
            if result is None:
                break
        return result
    
    def update(self, key_path: List[str], value, save=True):
        """
        Updates the configuration value at the specified key path and optionally saves the changes to the JSON file.

        Args:
            key_path (List[str]): A list of keys representing the path to the desired configuration value.
            value: The new value to set at the specified key path.
            save (bool, optional): If True, saves the updated configuration to the JSON file. Defaults to True.

        Raises:
            KeyError: If the key path does not exist in the configuration.
        """
        current_node = self.config
        # Traverse the key path to find the parent node of the last key
        for i, key in enumerate(key_path[:-1]):
            if key not in current_node:
                raise KeyError(f"Key path '{'/'.join(key_path[:i+1])}' does not exist in the configuration.")
            current_node = current_node[key]

        final_key = key_path[-1]
        # Check if the final key exists, if not, raise an exception
        if final_key not in current_node:
            raise KeyError(f"Final key '{final_key}' in key path '{'/'.join(key_path)}' does not exist in the configuration.")

        # Update the value
        current_node[final_key] = value

        # Save the configuration file based on the parameter
        if save:
            with open(self.config_file, 'w', encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)