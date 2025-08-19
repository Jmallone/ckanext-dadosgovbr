# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

# Import all helper modules explicitly
try:
    from . import tools
    from . import wordpress
    from . import scheming
except ImportError:
    # If relative imports fail, try absolute imports
    try:
        import ckanext.dadosgovbr.helpers.tools
        import ckanext.dadosgovbr.helpers.wordpress
        import ckanext.dadosgovbr.helpers.scheming
    except ImportError:
        pass
