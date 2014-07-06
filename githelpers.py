import os

from general import exists_and_is_directory

def has_objects_and_refs(path):
    '''Returns True if <path>/objects and <path>/refs both exist and
    (after resolving any symlinks) are directories; returns False
    otherwise.  The existence of this directory structure is a
    resonable sanity check on <path> being a git repository'''
    objects_path = os.path.join(path,"objects")
    refs_path = os.path.join(path,"refs")
    return exists_and_is_directory(objects_path) and \
        exists_and_is_directory(refs_path)

def probable_non_bare_repository(path):
    git_directory_path = os.path.join(path,'.git')
    return has_objects_and_refs(git_directory_path)

def is_in_another_git_repository(relative_path):
    if not exists_and_is_directory(relative_path):
        raise Exception("{} was not a directory".format(relative_path))
    while True:
        parent = os.path.dirname(relative_path)
        if not parent:
            return False
        if probable_non_bare_repository(parent):
            return True
        relative_path = parent
