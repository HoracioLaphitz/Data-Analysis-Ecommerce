class DataQualityError(Exception):
    """Raised when the ELT data-quality gate finds violating rows."""
