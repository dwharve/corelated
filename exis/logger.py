class Logger:
    def __init__(self,verbosity=1):
        self.verbosity = verbosity

    def error(self,msg=""):
        if self.verbosity >= 1:
            self._log('ERROR',msg)

    def warn(self,msg=""):
        if self.verbosity >= 2:
            self._log('WARN',msg)

    def info(self,msg=""):
        if self.verbosity >= 3:
            self._log('INFO',msg)

    def debug(self,msg=""):
        if self.verbosity >= 4:
            self._log('DEBUG',msg)

    def _log(self,level="INFO",msg=""):
        print('[ '+level+' ] '+msg)
