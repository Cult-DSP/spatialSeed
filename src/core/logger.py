import logging
import sys

def setup_logging(level=logging.INFO):
    """
    Sets up structured logging for the SpatialSeed project.
    """
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger("spatialSeed")
    if not root_logger.handlers:
        root_logger.setLevel(level)
        root_logger.addHandler(handler)
        
    return root_logger
