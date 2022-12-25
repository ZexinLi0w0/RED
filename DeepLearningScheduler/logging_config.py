import logging, colorlog

def logging_basic_setting(name='main'):
    # create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # create formatter
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(white)s%(message)s',
        log_colors={
            'DEBUG': 'blue',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        reset=True
    )

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)
    # set logging format
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename='./log.info.txt')
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG, filename='./log.debug.txt')
    logging.basicConfig(format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s", level=logging.WARNING, filename='./log.warning.txt')
    logging.basicConfig(format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s", level=logging.ERROR, filename='./log.error.txt')
    logging.basicConfig(format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s", level=logging.CRITICAL, filename='./log.critical.txt')
    return logger

if __name__ == "__main__":
    logging_basic_setting('main')
    logger = logging.getLogger('main')
    logger.debug('Debug level will be like this')
    logger.info('Info level will be like this')
    logger.warning('Warning level will be like this')
    logger.error('Error level will be like this')
    logger.critical('Critical level will be like this')