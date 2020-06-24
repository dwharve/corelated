from copy import deepcopy

class Parser:
    def __init__(self, log, conf=None, name=None):
        self.log = log
        self.records = []
        self.outputs = []
        self.sources = {}
        self.name = name
        if conf:
            if 'sources' in conf:
                for s in conf['sources'].keys():
                    self.sources[s] = conf['sources'][s]

    def send(self, records):
        for output in self.outputs:
            r = deepcopy(records)
            output.add_records(self.name, r)

    def add_output(self, output):
        self.outputs.append(output)

    def get_outputs(self):
        return {self.name:len(self.outputs)}

    def add_record(self, name, record):
        self.records.append(record)

    def expire_records(self):
        pass

    def get_sources(self):
        return self.sources.keys()

    def add_sources(self, name, source):
        self.sources[name] = source

    def get_status(self):
        msg = 'Parser '+self.name+' - '+len(self.records)
        return msg
