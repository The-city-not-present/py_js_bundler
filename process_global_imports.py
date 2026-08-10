
def process(module):
    source = f'import * as {module.name} from \'{module.source}\';\n'
    return source
