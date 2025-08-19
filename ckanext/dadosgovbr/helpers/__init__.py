# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

# Import all helper modules and functions
# We need try/except because these modules depend on CKAN
try:
    from . import tools
    from . import wordpress  
    from . import scheming

    # Import all functions directly for easy access
    from .tools import (
        most_recent_datasets, trim_string, trim_letter, resource_count,
        get_featured_group, get_organization_extra, get_package,
        cache_create, cache_load, group_id_or_name_exists,
        eouv_is_avaliable, helper_get_contador_eouv
    )

    from .wordpress import posts, format_timestamp
    from .scheming import get_schema_name, get_schema_title
    
except ImportError:
    # This happens when CKAN is not available (e.g., during development)
    # The modules will still be importable when running in CKAN environment
    pass
