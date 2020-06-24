from inputs import Input
import re
import elasticsearch
import elasticsearch.helpers
from datetime import datetime, timedelta
from copy import deepcopy


class Elasticsearch(Input):
    def __init__(self, log, conf=None):
        Input.__init__(self, log)
        self.es = {}
        if conf:
            for c in conf:
                self.add_source(c)

    def add_source(self, source):
        if 'name' not in source: raise Exception('Invalid configuration for Elasticsearch input')
        if source['name'] in self.sources: raise Exception('Attempted to add index '+source['name']+' twice')
        if 'host' not in source: raise Exception('Missing field host in '+source['name']+' index in Elasticsearch input')
        if 'duration' not in source: raise Exception('Missing field duration in '+source['name']+' index in Elasticsearch input')
        if 'delay' not in source: raise Exception('Missing field delay in '+source['name']+' index in Elasticsearch input')
        if 'doc_type' not in source: raise Exception('Missing field doc_type in '+source['name']+' index in Elasticsearch input')
        if 'source' not in source: raise Exception('Missing field source in '+source['name']+' index in Elasticsearch input')
        if 'pattern' not in source: raise Exception('Missing field pattern in '+source['name']+' index in Elasticsearch input')
        if 'indexedTimestamp' not in source: raise Exception('Missing field indexedTimestamp in '+source['name']+' index in Elasticsearch input')
        if 'timestamps' not in source: raise Exception('Missing field logTimestamp in '+source['name']+' index in Elasticsearch input')

        self.es[source['host']] = elasticsearch.Elasticsearch(source['host'])
        source['_newest'] = datetime.utcnow() - timedelta(seconds=source['duration'])
        source['_delay'] = timedelta(seconds=source['delay'])
        source['_outputs'] = []
        self.sources[source['name']] = source

    def run(self):
        for name in self.sources.keys():
            query = self.__get_query(name)
            try:
                res = self.es[self.sources[name]['host']].search(
                    index=query['index'],
                    doc_type=query['doc_type'],
                    body=query['query'],
                    size=10000,
                    scroll='1m',
                    sort=query['sort']
                )
            except Exception as e:
                self.log.error(str(e))
                return
            if res:
                self.log.debug('Received '+str(len(res['hits']['hits']))+'/'+str(res['hits']['total'])+' hits for '+name)
                if res['hits']['total'] > 0:
                    es_results = res['hits']['hits']
                    total = res['hits']['total']
                    while len(es_results) < total:
                        try:
                            res = self.es[self.sources[name]['host']].scroll(scroll_id=res['_scroll_id'], scroll='1m')
                            if 'hits' not in res:
                                break
                            if 'hits' not in res['hits']:
                                break
                            if len(res['hits']['hits']) < 1:
                                break
                            self.log.debug('Received '+str(len(es_results))+'/'+str(res['hits']['total'])+' hits for '+name)
                            es_results += res['hits']['hits']
                        except Exception as e:
                            self.log.error(str(e))
                    for record in es_results:
                        record.update(record['_source'])
                        del record['_score']
                        del record['_source']
                        self.__parse_timestamps(name, record)
                        if record[self.sources[name]['indexedTimestamp']] > self.sources[name]['_newest']:
                            self.sources[name]['_newest'] = record[self.sources[name]['indexedTimestamp']]
                    for p in self.sources[name]['_outputs']:
                        r = deepcopy(es_results)
                        p.add_records(name, r)

    def __parse_timestamps(self, name, record):
        for conf in self.sources[name]['timestamps']:
            if conf not in record:
                self.log.error('Unable to parse timestamp '+conf+', not found in received record in elasticsearch input')
                continue
            field = self.sources[name]['timestamps'][conf]
            if 'type' not in field or 'format' not in field:
                raise Exception('Invalid timestamp field '+conf+' in '+name+' in elasticsearch input')
            if 'replace' in field:
                if 'regex' not in field['replace'] or 'string' not in field['replace']:
                    raise Exception('Invalid replace in timestamp')
                record[conf] = re.sub(field['replace']['regex'], field['replace']['string'], str(record[conf]))
            if field['type'] == 'UNIX':
                record[conf] = datetime.utcfromtimestamp(float(record[conf]))
            elif field['type'] == 'string':
                record[conf] = datetime.strptime(record[conf], field['format'])
            else:
                raise Exception('Invalid timestamp type '+field['type'])

    def __get_query(self, name):
        q = {}
        if 'source' in self.sources[name]:
            q['_source'] = self.sources[name]['source']
        q['query'] = {}
        if 'query' in self.sources[name]:
            q['query'] = deepcopy(self.sources[name]['query'])
        range = {self.sources[name]['indexedTimestamp']: {'gt': self.sources[name]['_newest'], 'lt': datetime.utcnow() - self.sources[name]['_delay']}}
        if 'bool' in q['query']:
            if 'must' in q['query']['bool']:
                q['query']['bool']['must'].append({'range': range})
            else:
                q['query']['bool']['must'] = [{'range': range}]
        else:
            q['query']['range'] = range
        index_pattern = self.sources[name]['_newest'].strftime(self.sources[name]['pattern'])
        now_pattern = datetime.utcnow().strftime(self.sources[name]['pattern'])
        if index_pattern != now_pattern:
            index_pattern += ','+now_pattern
        doc_type = 'doc'
        if 'doc_type' in self.sources[name]:
            doc_type = self.sources[name]['doc_type']
        return {'index': index_pattern, 'doc_type': doc_type, 'query': q, 'sort': {self.sources[name]['indexedTimestamp']: 'asc'}}
