from actions import Action
import elasticsearch
import elasticsearch.helpers
from copy import deepcopy


class Elasticsearch(Action):
    def __init__(self, log, conf=None):
        Action.__init__(self, log, conf)
        self.log = log
        self.records = []
        self.sources = {}
        self.debug_records_sent = []
        if conf:
            for c in conf:
                self.add_source(c)

    def add_records(self, name, records):
        for record in records:
            for source in self.sources[name]:
                if source['source'] not in record:
                    self.log.error('Unknown source in record in Elasticsearch action')

                r = deepcopy(record[source['source']])
                fields = source['fields']
                if '_id' not in r or '_type' not in r or '_index' not in r:
                    self.log.error('Record missing required fields in '+source['source']+' in Elasticsearch action')
                    print(r)
                    return

                fields_to_keep = ['_id', '_type', '_index']
                doc_fields = []
                for field in fields:
                    doc_fields.append(field[source['source']])
                tbd = []
                for k in r:
                    if k not in fields_to_keep and k not in doc_fields:
                        tbd.append(k)
                for k in tbd:
                    del r[k]

                r['doc'] = {}
                for field in fields:
                    if source['source'] not in field:
                        raise Exception('Invalid fields in Elasticsearch action')
                    for k in field:
                        if k == source['source']:
                            continue
                        if field[k] not in record[k]:
                            continue
                        if '.' not in field[source['source']]:
                            r['doc'][field[source['source']]] = record[k][field[k]]
                        else:
                            obs = field[source['source']].split('.')
                            parents = obs[:-1]
                            if len(obs) < 1:
                                continue
                            parent = r['doc']
                            for f in parents:
                                if f not in parent:
                                    parent[f] = {}
                                parent = parent[f]
                            parent[obs[-1]] = record[k][field[k]]

                r['_op_type'] = source['type']
                source['_records'].append(r)

    def run(self):
        for name in self.sources:
            for source in self.sources[name]:
                try:
                    elasticsearch.helpers.bulk(source['_es'], source['_records'])
                    source['_records'] = []
                except Exception as e:
                    self.log.error(str(e))

    def add_source(self, conf):
        for field in ['name', 'type', 'source', 'host', 'fields']:
            if field not in conf: raise Exception(field+' not defined in Elasticsearch action')
        conf['_es'] = elasticsearch.Elasticsearch(conf['host'])
        conf['_records'] = []
        if conf['name'] not in self.sources:
            self.sources[conf['name']] = []
        self.sources[conf['name']].append(conf)
