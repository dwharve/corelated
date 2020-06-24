class Input:
    def __init__(self, log, conf=None):
        self.log = log
        self.sources = {}
        self.name = 'Input'
        if conf:
            if len(conf) > 0:
                for c in conf:
                    if 'name' in c:
                        self.sources[c['name']] = c

    def run(self):
        pass

    def get_sources(self):
        return self.sources.keys()

    def add_source(self, source):
        if 'name' not in source:
            self.log.error('Invalid configuration for '+self.name)
            return
        self.sources[source['name']] = source

    def add_output(self, source, output):
        if source in self.sources:
            if '_outputs' not in self.sources[source]:
                self.sources[source]['_outputs'] = []
            self.sources[source]['_outputs'].append(output)

    def get_outputs(self):
        res = {}
        for source in self.sources:
            if '_outputs' in self.sources[source]:
                res[source] = len(self.sources[source]['_outputs'])
        return res
