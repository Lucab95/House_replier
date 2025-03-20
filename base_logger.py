import logging

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('cron-log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)