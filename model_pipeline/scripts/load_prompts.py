import yaml

def load_prompts(filename):
    """Load prompt templates from a YAML file."""
    with open(filename, "r") as file:
        return yaml.safe_load(file)
