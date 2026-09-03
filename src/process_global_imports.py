
def process(module, config):
    source = f'import * as {module.name} from \'{module.source}\';\n'
    return source
