import logging

# Configure SQLAlchemy engine logger
logger = logging.getLogger('sqlalchemy.engine')
logger.setLevel(logging.INFO)  # Set to DEBUG for detailed logs
file_handler = logging.FileHandler('sqlalchemy_queries.log', mode='w')
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)