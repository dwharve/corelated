# corelated
corelated is a plugin framework to facilitate log corelation from multiple 
sources. It consists of three categories: inputs, parsers, and actions. 

The initial reason for developing corelated was to add information from 
winlogbeat to Moloch. Logstash is not a viable method as it queries 
Elasticsearch for each event to find the corelating Moloch session. This 
caused Elasticsearch to be overwelhmed with queries. As a solution to this 
problem corelated uses an Elasticsearch `input` plugin to query Elasticsearch 
once per `pollTime` seconds, and keeping all records in memory to be matched 
with winlogbeat records. While this typically would not be the correct method 
to do log corelation, it falls in line with the intention of Elasticsearch to 
have live, quick results to queries. The load placed on Elasticsearch clusters 
is insignificant, and this method allows for far more than just corelation 
between two indices. It allows a python script to "walk" a large database of 
records with minimal impact to resources. 

## Configuration
###### Elasticsearch Input
```
inputs:
  Elasticsearch:                    # Input plugin name
  - name: SomeName                  # A name to reference this specific input
    host: elasticsearch:9200        # Elasticsearch host:port
    duration: 1800                  # Duration (oldest) and Delay (newest)is used as a 
    delay: 120                      # range for the timestamp field during queries
    doc_type: doc                   # Document type
    source:
    - SourceIp                      # Only return these fields
    - SourcePort
    - DestinationIp
    - DestinationPort
    - Image
    - '@timestamp'
    - ts
    - ProcessId
    - User
    - ProcessGuid
    - SourceHostname
    - DestinationHostname
    pattern: "winlogbeat-%y%m%d"    # Index pattern, uses python's strftime
    query:                          # DSL query will be added to every query
      bool:
        must:
        - term:
            Initiated: "true"
        must_not:
        - exists:
            field: moloch_id
    indexedTimestamp: '@timestamp'  # Timestamp of when the record was sent to elasticsearch
    timestamps:                     # Any field in 'source' that needs to be parsed
      '@timestamp':
        type: string                # Either 'string' or 'UNIX'
        replace:
          regex: "[Z]$"
          string: "000"
        format: "%Y-%m-%dT%H:%M:%S.%f"
      ts:
        type: string
        replace:
          regex: "[Z]$"
          string: "000"
        format: "%Y-%m-%dT%H:%M:%S.%f"
```

###### Match Parser
```
parsers:
  moloch-init:                      # A name to reference this specific parser instance
    name: Match                     # Plugin name to be used
    workers: 2                      # If Plugin inherits from TParser, the amount of threads to be used
    sources:                        # The specific Input instances to be used as sources of records
      moloch:                       # Input name (SomeName in example above)
        fields:                     # These fields will be used to match records with the other source, position sensitive
        - - 'srcIp'                 # Multidimensional array to allow matching in the fields in a different orders
          - 'srcPort'               # eg. "srcIp-srcPort-dstIp-dstPort" == "SourceIp-SourcePort-DestinationIp-DestinationPort"
          - 'dstIp'                 #  or "dstIp-dstPort-srcIp-srcPort" == "SourceIp-SourcePort-DestinationIp-DestinationPort"
          - 'dstPort'
        - - 'dstIp'
          - 'dstPort'
          - 'srcIp'
          - 'srcPort'
        timestamp: 'firstPacket'    # Timestamp to be used for identifying matches. This should be when the event happened
        duration: 1800              # How long in seconds to keep a record in memory by age of the record (The above timestamp is used as reference)
        tolerance: 10               # How many seconds can be between matching records to be considered a match
        method: closest             # closest or all. If a match is found and multiple records are within tolerance, either match all or the closest
      winlogs-init:                 # Second Input source. The match parser will throw an error if you define more than or less than 2 sources
        fields:
        - - 'SourceIp'
          - 'SourcePort'
          - 'DestinationIp'
          - 'DestinationPort'
        timestamp: 'ts'
        duration: 1800
        tolerance: 10
        method: all
```

###### Elasticsearch Action
```
actions:
  Elasticsearch:                    # Which Action plugin to use
  - name: moloch-init               # Parser instance, any record sent from this parser instance will come to this action
    host: elasticsearch:9200        # Elasticsearch host:port
    type: update                    # Only update is allowed here for now
    source: moloch                  # Which input source to update
    fields:                         # The fields not in the above 'source' contains the data that will be placed in the 
    - moloch: procs.dst.image       # corresponding new field in the 'source' record
      winlogs-resp: Image
    - moloch: procs.dst.pid
      winlogs-resp: ProcessId
    - moloch: procs.dst.user
      winlogs-resp: User
    - moloch: procs.dst.pguid
      winlogs-resp: ProcessGuid
    - moloch: procs.dst.host
      winlogs-resp: SourceHostname
    - moloch: procs.dst.dstHost
      winlogs-resp: DestinationHostname

```
