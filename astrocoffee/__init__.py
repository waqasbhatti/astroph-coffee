from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

# the basic logging styles common to all modules
log_sub = '{'
log_fmt = '[{levelname:1.1} {asctime} {module}:{funcName}:{lineno}] {message}'
log_date_fmt = '%Y-%m-%d %H:%M:%S%z'
