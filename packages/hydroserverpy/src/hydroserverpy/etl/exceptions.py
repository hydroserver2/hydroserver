class ETLError(Exception):
    """
    Base exception for all ETL-related errors.
    Can be used to signal known issues that occur during
    data extraction, transformation, or loading.
    """

    ...
