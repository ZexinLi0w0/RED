import logging, colorlog

def logging_basic_setting():
    # create logger
    logger = logging.getLogger()
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
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename='./log.txt')
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    logging.basicConfig(format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s", level=logging.WARNING)
    logging.basicConfig(format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s", level=logging.ERROR)
    logging.basicConfig(format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s", level=logging.CRITICAL)

if __name__ == "__main__":
    logging_basic_setting()
    logging.debug('Debug level will be like this')
    logging.info('Info level will be like this')
    logging.warning('Warning level will be like this')
    logging.error('Error level will be like this')
    logging.critical('Critical level will be like this')