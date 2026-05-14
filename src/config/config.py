import yaml
import os
import re
from types import SimpleNamespace


def _expand_env_vars(value):
    """Recursively expand environment variables in strings like ${VAR_NAME}."""
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}'
        def replace_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        return re.sub(pattern, replace_var, value)
    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    return value


def _convert_types(value):
    """Convert string values to appropriate types (int, bool, etc.)."""
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        elif value.lower() in ('false', '0', 'no', 'off', ''):
            return False
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
    elif isinstance(value, dict):
        return {k: _convert_types(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_convert_types(item) for item in value]
    return value


def _dict_to_namespace(data):
    """Recursively convert nested dictionaries to SimpleNamespace objects."""
    if isinstance(data, dict):
        namespace = SimpleNamespace()
        for key, value in data.items():
            # Convert key to valid Python identifier
            python_key = key.replace('-', '_').replace(' ', '_')
            setattr(namespace, python_key, _dict_to_namespace(value))
        return namespace
    return data


def _load_config():
    """Load YAML config and create namespace objects."""
    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')

    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"Config file '{config_file}' not found.")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return {}

    # Expand environment variables and convert types
    config_data = _expand_env_vars(config_data)
    config_data = _convert_types(config_data)

    # Convert each section to SimpleNamespace
    sections = {}
    for section_name, section_data in config_data.items():
        sections[section_name] = _dict_to_namespace(section_data)

    return sections


def generate_stub_file():
    """Generate a .pyi stub file for IDE support."""
    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
    stub_file = os.path.join(os.path.dirname(__file__), '__init__.pyi')

    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f) or {}
    except:
        return

    def _generate_class_definition(name: str, data: dict, indent: int = 0) -> str:
        """Generate class definition for a config section."""
        spaces = "    " * indent
        lines = [f"{spaces}class {name.title()}:"]

        for key, value in data.items():
            # Convert key to valid Python identifier
            python_key = key.replace('-', '_').replace(' ', '_')

            if isinstance(value, dict):
                # Nested section
                lines.append(_generate_class_definition(python_key, value, indent + 1))
                lines.append(f"{spaces}    {python_key}: {python_key.title()}")
            else:
                # Simple attribute
                if isinstance(value, str):
                    lines.append(f"{spaces}    {python_key}: str")
                elif isinstance(value, int):
                    lines.append(f"{spaces}    {python_key}: int")
                elif isinstance(value, bool):
                    lines.append(f"{spaces}    {python_key}: bool")
                elif isinstance(value, float):
                    lines.append(f"{spaces}    {python_key}: float")
                else:
                    lines.append(f"{spaces}    {python_key}: Any")

        return "\n".join(lines)

    # Generate stub content
    stub_content = ["from typing import Any\n"]

    for section_name, section_data in config_data.items():
        if isinstance(section_data, dict):
            stub_content.append(_generate_class_definition(section_name, section_data))
            stub_content.append(f"{section_name}: {section_name.title()}")
        else:
            if isinstance(section_data, str):
                stub_content.append(f"{section_name}: str")
            elif isinstance(section_data, int):
                stub_content.append(f"{section_name}: int")
            elif isinstance(section_data, bool):
                stub_content.append(f"{section_name}: bool")
            else:
                stub_content.append(f"{section_name}: Any")

    stub_content.append("\ndef reload_config() -> None: ...")

    try:
        with open(stub_file, 'w') as f:
            f.write("\n\n".join(stub_content))
        print(f"Generated stub file: {stub_file}")
    except Exception as e:
        print(f"Could not generate stub file: {e}")


# Load config sections
config_sections = _load_config()

# Dynamically create variables and generate stub file for IDE support
if config_sections:
    generate_stub_file()

# Create module-level variables for each section
for section_name, section_obj in config_sections.items():
    globals()[section_name] = section_obj


def reload_config():
    """Reload configuration from YAML file."""
    global config_sections

    config_sections = _load_config()

    # Regenerate stub file
    if config_sections:
        generate_stub_file()

    # Update module globals
    for section_name, section_obj in config_sections.items():
        globals()[section_name] = section_obj

    print("Config reloaded!")