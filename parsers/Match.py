from parsers import Parser
from datetime import datetime, timedelta
from multiprocessing import Process, Queue
from hashlib import md5


class MatchCache:
    @staticmethod
    def run(name, fields, timestamp, tolerance, duration, method, chunk_id, chunk_len, rx_queue, tx_queue):
        cache = MatchCache(name, fields, timestamp, tolerance, duration, method, chunk_id, chunk_len)
        rx_queue = rx_queue
        tx_queue = tx_queue
        rx = rx_queue.get()
        while rx != None:
            if len(rx) < 1:
                rx = rx_queue.get()
                continue
            if rx[0] == 'match' and len(rx) == 5:
                try:
                    tx_queue.put(cache.get_matches(rx[1], rx[2], rx[3], rx[4]))
                except Exception as e:
                    tx_queue.put({'tbd': [], 'matches': []})
                    print(str(e)+'\nException caught by runner in match')
            elif rx[0] == 'add' and len(rx) == 2:
                try:
                    cache.add(rx[1])
                except Exception as e:
                    print(str(e)+'\nException caught by runner in match')
            elif rx[0] == 'expire' and len(rx) == 1:
                try:
                    tx_queue.put(cache.expire())
                except Exception as e:
                    tx_queue.put([])
                    print(str(e)+'\nException caught by runner in match')
            elif rx[0] == 'status' and len(rx) == 1:
                try:
                    tx_queue.put(cache.get_status())
                except Exception as e:
                    tx_queue.put('')
                    print(str(e) + '\nException caught by runner in match')
            rx = rx_queue.get()

    def __init__(self, name, fields, timestamp, tolerance, duration, method, chunk_id, chunk_len):
        self.name = name
        self.fields = fields
        self.timestamp = timestamp
        self.tolerance = timedelta(seconds=tolerance)
        self.duration = timedelta(seconds=duration)
        self.method = method
        self.chunk_id = chunk_id
        self.chunk_len = chunk_len
        self.records = {}

    def add(self, records):
        for record in records:
            if self.timestamp not in record:
                continue
            keys = self.__get_keys(self.fields, record)
            if not keys:
                continue
            if not self.__is_mine(keys):
                continue
            r = self.__get_records_by_keys(keys)
            if not r:
                r = [record]
                for key in keys:
                    self.records[key] = r
            else:
                for i in range(0, len(r)):
                    if MatchCache.__is_copy(record, r[i]):
                        continue
                    if r[i][self.timestamp] < record[self.timestamp]:
                        if i == len(r) - 1:
                            r.append(record)
                            break
                    else:
                        r.insert(i, record)
                        break

    def get_matches(self, input_name, ts_field, key_fields, records):
        res = []
        tbd = []
        for a in range(0,len(records)):
            if ts_field not in records[a]:
                continue
            keys = self.__get_keys(key_fields, records[a])
            if not self.__is_mine(keys):
                continue
            r = self.__get_records_by_keys(keys)
            if not r:
                continue

            match = []
            if self.method == 'closest':
                match.append([self.tolerance, 0])
                tdiff = False
                for i in range(0, len(r)):
                    if r[i][self.timestamp] < records[a][ts_field]:
                        t = records[a][ts_field] - r[i][self.timestamp]
                    else:
                        t = r[i][self.timestamp] - records[a][ts_field]
                    if t <= match[0][0]:
                        match[0] = [t, i]
                        tdiff = True
                if tdiff:
                    match = [match[0][1]]
                else:
                    match = []
            elif self.method == 'all':
                for i in range(0, len(r)):
                    if r[i][self.timestamp] < records[a][ts_field]:
                        t = records[a][ts_field] - r[i][self.timestamp]
                    else:
                        t = r[i][self.timestamp] - records[a][ts_field]
                    if t <= self.tolerance:
                        match.append(i)

            tres = []
            if match:
                tbd.append(a)
                for i in reversed(match):
                    tres.append({input_name: records[a], self.name: r[i]})
                    del r[i]
                if len(r) == 0:
                    for key in keys:
                        if key in self.records:
                            del self.records[key]
                res.extend(tres)
        return {'tbd': tbd, 'matches': res}

    def expire(self):
        past_ts = datetime.utcnow() - self.duration
        keys_tbd = []
        records = []
        for key in self.records.keys():
            el_tbd = []
            for i in range(0, len(self.records[key])):
                if self.records[key][i][self.timestamp] < past_ts:
                    el_tbd.append(i)
                    records.append(self.records[key][i])
                else:
                    break
            for i in el_tbd:
                if len(self.records[key]) >= i + 1:
                    del self.records[key][i]
            if len(self.records[key]) == 0:
                keys_tbd.append(key)
        for key in keys_tbd:
            del self.records[key]
        return records

    def get_status(self):
        count = 0
        for key in self.records:
            count += len(self.records[key])
        return count

    def __is_mine(self, keys):
        if len(keys) > 0:
            sig_str = '-'.join(sorted(keys[0].split('-')))
            calced_hash = (int(md5(sig_str.encode()).hexdigest(),16) % self.chunk_len)
            if calced_hash == self.chunk_id:
                return True

        return False

    def __get_record_list(self, record):
        keys = self.__get_keys(self.fields, record)
        return keys, self.__get_records_by_keys(keys)

    def __get_records_by_keys(self, keys):
        records = []
        for key in keys:
            if key in self.records:
                if len(self.records[key]) != 0:
                    records = self.records[key]
                break
        return records

    def __get_keys(self, key_fields, record):
        keys = []
        for key_set in key_fields:
            k = ''
            for key in key_set:
                if key not in record:
                    return []
                k += str(record[key])+'-'
            k = k[:-1]
            keys.append(k)
        return keys

    def __get_timestamp(self, record):
        if self.timestamp not in record:
            return None
        return record[self.timestamp]

    @staticmethod
    def __is_copy(a, b):
        if a.keys() == b.keys():
            for key in a.keys():
                if a[key] != b[key]:
                    return False
        else:
            return False
        return True

class Match(Parser):
    def __init__(self, log, conf, name):
        Parser.__init__(self, log)
        self.name = name
        self.conf = conf
        self.sources = {}
        self.matches = 0
        if 'sources' not in self.conf: raise Exception('Invalid configuration for '+self.name+' match')
        if 'workers' not in self.conf: raise Exception('Field workers not specified in '+self.name+' match')
        if type(self.conf['workers']) != int:
            self.log.error('Invalid value for field workers in '+self.name+' match, setting to 1')
            self.conf['workers'] = 1
        if self.conf['workers'] < 1:
            self.log.error('Invalid value for field workers in '+self.name+' match, setting to 1')
            self.conf['workers'] = 1
        for s in self.conf['sources'].keys():
            self.add_source(s, self.conf['sources'][s])

    def add_source(self, name, source):
        if len(self.sources) >= 2:
            raise Exception('Too many sources defined in '+self.name+' match')
        if 'fields' not in source: raise Exception('No fields defined in '+self.name+' match')
        if 'timestamp' not in source: raise Exception('Timestamp not defined in '+self.name+' match')
        if 'duration' not in source: raise Exception('Duration not defined in '+self.name+' match')
        if 'tolerance' not in source: raise Exception('tolerance not defined in '+self.name+' match')
        if 'method' not in source: raise Exception('method not defined in '+self.name+' match')
        if name in self.sources: raise Exception(name+' defined twice in match')
        self.sources[name] = []
        for i in range(0, self.conf['workers']):
            rx = Queue()
            tx = Queue()
            self.sources[name].append({'proc': Process(target=MatchCache.run, args=(
                name,
                source['fields'],
                source['timestamp'],
                source['tolerance'],
                source['duration'],
                source['method'],
                i,
                self.conf['workers'],
                tx,
                rx
            )), 'rx': rx, 'tx': tx})
        for p in self.sources[name]:
            p['proc'].start()

    def add_records(self, inputName, records):
        if inputName not in self.sources:
            raise Exception(self.name+' match parser received record from an unknown source')

        tbd = []
        for source in self.sources:
            if source == inputName:
                continue

            for s in self.sources[source]:
                s['tx'].put(['match', inputName, self.conf['sources'][inputName]['timestamp'], self.conf['sources'][inputName]['fields'], records])

            matches = {'tbd': [], 'matches': []}
            for s in self.sources[source]:
                try:
                    matches = s['rx'].get()
                except Exception as e:
                    self.log.error(str(e)+' - Exception in '+source+' in match')

                if matches['matches']:
                    self.matches += len(matches['matches'])
                    self.send(matches['matches'])
                if matches['tbd']:
                    tbd.extend(matches['tbd'])

        if tbd:
            for i in reversed(sorted(tbd)):
                del records[i]

        for s in self.sources[inputName]:

            s['tx'].put(['add', records])

    def expire_records(self):
        for source in self.sources:
            for s in self.sources[source]:
                s['tx'].put(['expire'])

            num = 0
            for s in self.sources[source]:
                try:
                    num += len(s['rx'].get())
                except Exception as e:
                    self.log.error(str(e)+' - Exception in '+source+' in match')
            #for record in records:
            #    for s in self.sources:
            #        if s == source: continue
            #        matches = self.sources[s].getMatches(record['record']['_keys'],record['ts'])
            #        if matches:
            #            self.matches += len(matches)
            #            for match in matches:
            #                self.send({s: match, source: record})
            if num:
                self.log.debug('Expired '+str(num)+' records in '+source+' in '+self.name+' match')

    def get_status(self):
        msg = 'Parser Match '+self.name+' - '
        for name in self.sources:
            for s in self.sources[name]:
                s['tx'].put(['status'])
            msg += name+': '
            num = 0
            for s in self.sources[name]:
                num += s['rx'].get()
            msg += str(int(num / len(self.conf['sources'][name]['fields'])))+' '
        msg += 'matches: '+str(self.matches)+' '
        self.matches = 0
        return msg
