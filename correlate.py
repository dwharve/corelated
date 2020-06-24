import sys
from time import sleep
from exis.config import Config
from exis.logger import Logger
from exis.plugins import Plugins

verbosity = 1
if len(sys.argv) >= 2:
    verbosity = int(sys.argv[1])
log = Logger(verbosity)

stored_config = Config(log, 'config.yml')

plugins = {
    'action': {'module': Plugins(log, './actions'), 'plugins': {}},
    'parser': {'module': Plugins(log, './parsers'), 'plugins': {}},
    'input': {'module': Plugins(log, './inputs'), 'plugins': {}}
}


def __get_plugin(ptype, plugin, conf=None, name=None):
    if plugin not in plugins[ptype]['plugins']:
        p = plugins[ptype]['module'].get(plugin)
        if not p:
            return None
        if name:
            plugins[ptype]['plugins'][name] = p(log, conf, name)
        else:
            plugins[ptype]['plugins'][plugin] = p(log, conf)
    if name:
        return plugins[ptype]['plugins'][name]
    else:
        return plugins[ptype]['plugins'][plugin]


def __get_actions_by_parser(name):
    actions = []
    for action in plugins['action']['plugins'].keys():
        if name in plugins['action']['plugins'][action].get_sources():
            actions.append(plugins['action']['plugins'][action])
    return actions


def __get_parsers_by_input(name):
    parsers = []
    input_sources = plugins['input']['plugins'][name].get_sources()
    for parser in plugins['parser']['plugins'].keys():
        for s in plugins['parser']['plugins'][parser].get_sources():
            for i in input_sources:
                if s in i and plugins['parser']['plugins'][parser] not in parsers:
                    parsers.append((i, plugins['parser']['plugins'][parser]))
    return parsers


def __check_plugin(ptype):
    if len(plugins[ptype]['plugins']) < 1:
        log.error('No '+ptype+'instantiated')
        exit(1)
    if ptype != 'action':
        count = 0
        for p in plugins[ptype]['plugins']:
            tmp = plugins[ptype]['plugins'][p].get_outputs()
            for t in tmp:
                count += tmp[t]
        if count < 1:
            log.error('No ouputs attached to any '+ptype)


def __run(ptype):
    for p in plugins[ptype]['plugins'].keys():
        try:
            plugins[ptype]['plugins'][p].run()
        except Exception as e:
            log.error(str(e))


def __get_status():
    res = ''
    for parser in plugins['parser']['plugins']:
        try:
            res += plugins['parser']['plugins'][parser].get_status()+' \n'
        except Exception as e:
            log.error(str(e))
    return res[:-1]


def __expire_records():
    for parser in plugins['parser']['plugins'].keys():
        try:
            plugins['parser']['plugins'][parser].expire_records()
        except Exception as e:
            log.error(str(e))


poll_time = 5


def __load_config():
    global poll_time
    config = stored_config.load()

    if len(config) < 1:
        log.warn('Loaded configuraiton is empty')
        exit(1)

    if 'pollTime' in config:
        poll_time = config['pollTime']

    if 'inputs' not in config:
        log.error('No inputs in configuration')
        exit(1)
    if 'parsers' not in config:
        log.error('No parsers in configuration')
        exit(1)
    if 'actions' not in config:
        log.error('No actions in configuration')
        exit(1)

    for action in config['actions'].keys():
        a = __get_plugin('action', action, config['actions'][action])
        if not a:
            log.error('Unable to instantiate '+action+' action')
            exit(1)
        else:
            log.debug('Instantiated '+action+' action')
    __check_plugin('action')

    for parser in config['parsers'].keys():
        if 'name' not in config['parsers'][parser]:
            log.error('Missing plugin name in '+parser+' parser')
            exit(1)
        p = __get_plugin('parser', config['parsers'][parser]['name'], config['parsers'][parser], parser)
        if not p:
            log.error('Unable to instantiate '+parser+' parser')
            exit(1)
        else:
            log.debug('Instantiated '+parser+' parser')
        actions = __get_actions_by_parser(parser)
        for action in actions:
            p.add_output(action)
            log.debug('    added '+str(action)+' to '+parser)
    __check_plugin('parser')

    for inp in config['inputs'].keys():
        i = __get_plugin('input', inp, config['inputs'][inp])
        if not i:
            log.error('Unable to instantiate '+inp+' input')
            exit(1)
        else:
            log.debug('Instantiated '+inp+' input')
        parsers = __get_parsers_by_input(inp)
        for parser in parsers:
            i.add_output(parser[0], parser[1])
            log.debug('    added '+str(parser)+' to '+inp)
    __check_plugin('input')


__load_config()

while True:
    if stored_config.isNew():
        __load_config()
        log.info('Loaded new config')
    __run('input')
    __expire_records()
    __run('action')
    status = __get_status()
    for line in status.split('\n'):
        log.info(line)
    sleep(poll_time)
