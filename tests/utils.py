import os

def get_example_data_path():
    cdir, cfile = os.path.split(__file__)
    return os.path.realpath(os.path.join(cdir, '..', 'example_data'))