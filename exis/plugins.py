import imp
import os

class Plugins:
    def __init__(self,logger,path='./plugins'):
        self.log = logger
        self.path = path
        self.files = {}
        try:
            for f in os.listdir(self.path):
                if f == '__init__.py': continue
                if f[-3:] == '.py':
                    m = imp.find_module(os.path.join(self.path,f[:-3]))
                    module = imp.load_module(f[:-3],m[0],m[1],m[2])
                    if f[:-3] not in module.__dict__:
                        self.log.error('Class '+f[:-3]+' not in '+f)
                        continue
                    self.files[f[:-3]] = module.__dict__[f[:-3]]
                    self.log.info('Loaded plugin '+f[:-3])
        except Exception as e:
            self.log.error("Unable to load plugin: "+f[:-3]+"\n"+str(e))
            exit(1)
    def get(self,key=None):
        if key == None and len(self.files) > 0:
            return self.files
        elif key in self.files:
            return self.files[key]
        else:
            return None
