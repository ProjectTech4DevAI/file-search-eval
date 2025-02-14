import os
import logging

#
#
#
logging.basicConfig(
    format='[ %(asctime)s %(levelname)s %(filename)s ] %(message)s',
    datefmt='%H:%M:%S',
    level=os.getenv('PYTHONLOGLEVEL', 'WARNING').upper(),
)
logging.captureWarnings(True)
Logger = logging.getLogger(__name__)
