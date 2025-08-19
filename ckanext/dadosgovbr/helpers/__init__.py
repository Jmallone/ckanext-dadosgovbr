# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

# Import all helper modules and functions
# We need to ensure these are imported and available
import sys
import os

# Get the current directory
current_dir = os.path.dirname(__file__)

# Import modules explicitly
try:
    # Import the modules first
    import ckanext.dadosgovbr.helpers.tools
    import ckanext.dadosgovbr.helpers.scheming
    
    # Make them available as attributes
    tools = ckanext.dadosgovbr.helpers.tools
    scheming = ckanext.dadosgovbr.helpers.scheming
    
    # Also import functions directly for convenience
    from ckanext.dadosgovbr.helpers.tools import (
        most_recent_datasets, trim_string, trim_letter, resource_count,
        get_featured_group, get_organization_extra, get_package,
        cache_create, cache_load, group_id_or_name_exists,
        eouv_is_avaliable, helper_get_contador_eouv
    )

    from ckanext.dadosgovbr.helpers.scheming import get_schema_name, get_schema_title
    
except ImportError as e:
    # If absolute imports fail, try relative imports
    try:
        from . import tools
        from . import scheming

        # Import all functions directly for easy access
        from .tools import (
            most_recent_datasets, trim_string, trim_letter, resource_count,
            get_featured_group, get_organization_extra, get_package,
            cache_create, cache_load, group_id_or_name_exists,
            eouv_is_avaliable, helper_get_contador_eouv
        )

        from .scheming import get_schema_name, get_schema_title
        
    except ImportError as e2:
        # This happens when CKAN is not available (e.g., during development)
        # The modules will still be importable when running in CKAN environment
        print(f"Warning: Could not import helpers modules: {e2}")
        pass
