import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("CFupdater")
handler = logging.FileHandler("CFupdater.log")
handler.setLevel(logging.WARNING)
handler.setFormatter(logging.Formatter("%(asctime)s-%(name)s-%(levelname)s: %(message)s"))
log.addHandler(handler)


log.info("test")
