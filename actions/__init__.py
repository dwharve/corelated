class Action:
    def __init__(self, log, conf=None):
        self.log = log
        self.records = []
        self.sources = {}
        self.name = 'Action'
        if conf:
            if len(conf) > 0:
                for c in conf:
                    if 'name' in c:
                        self.sources[c['name']] = c

    def add_record(self, name, record):
        self.records.append(record)

    def run(self):
        pass

    def get_sources(self):
        return self.sources.keys()

    def add_source(self, conf):
        if 'name' not in conf:
            self.log.error('Invalid configuration for '+self.name)
            return
        self.sources[conf['name']] = conf
