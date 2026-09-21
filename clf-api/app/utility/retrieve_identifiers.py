import yaml

def get_identifiers_from_yaml(file_path):
    with open(file_path, 'r') as file:
        identifiers = yaml.safe_load(file)

    if not isinstance(identifiers, list):
        raise ValueError("YAML file must contain a list of identifiers.")

    return identifiers
