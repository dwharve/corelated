import yaml
import os

class Config:
    def __init__(self,log,path='config.yml'):
        self.path = path
        self.log = log
        if not os.path.isfile(self.path):
            self.log.warn('No configuration found')
            try:
                with open(path,'w'):
                    pass
            except Exception as e:
                self.log.error('Unable to create configuration file at: '+self.path+'\n'+e)
                exit(1)
        self.lastModified = os.path.getmtime(self.path)

    def isNew(self):
        if not os.path.isfile(self.path):
            self.log.debug('Configuraiton file not found when checking for update')
            return False
        if os.path.getmtime(self.path) > self.lastModified:
            self.log.debug('Found newer configuration')
            return True
        else:
            return False

    def load(self):
        res = {}
        if os.path.isfile(self.path):
            try:
                f = open(self.path,'r')
                cont = f.read()
                f.close()
                if cont == '':
                    self.log.error('Configuration file is empty')
                    exit(1)
                res = yaml.load(cont)
                if res == None:
                    self.log.error('Unable to load configuration file')
                    exit(1)
                self.log.info('Found configuration')
                self.log.debug('Read '+str(len(res))+' configurations')
            except Exception as e:
                self.log.error('Unable to load configuraiton file\n'+str(e))
        self.lastModified = os.path.getmtime(self.path)
        return res

    def save(self,config):
        try:
            with open(self.path,'w') as f:
                f.write(yaml.safe_dump(config))
                self.log.debug('Saved confguration to '+self.path)
        except Exception as e:
            self.log.error('Unable to save configuration file\n'+e)
