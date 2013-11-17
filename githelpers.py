from general import *

def has_objects_and_refs(path):
    '''Returns True if <path>/objects and <path>/refs both exist and
    (after resolving any symlinks) are directories; returns False
    otherwise.  The existence of this directory structure is a
    resonable sanity check on <path> being a git repository'''
    objects_path = os.path.join(path,"objects")
    refs_path = os.path.join(path,"refs")
    return exists_and_is_directory(objects_path) and exists_and_is_directory(refs_path)

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

# default parameter was: setup.get_directory_to_backup()
def find_git_repositories(start_path):
    '''Use the find-git-repos command to return a list of all directories
    which are working trees with git repositories.  (In other words, this
    does not find bare repositories.)

    This used to be done by find-git-repos, but that inexplicably missed
    some paths.  This version isn't quite good enough, because it doesn't
    pay attention to .gitignore files - FIXME when I have time.  Instead
    for the moment if finds all non-bare git repositories, even if they
    would have been ignored.'''
    new_start_path = re.sub(r'/*$', '/', start_path)
    git_directories = []
    for root, dirs, files in os.walk(start_path):
        directories_to_prune = []
        for i, potential_git_directory in enumerate(dirs):
            full_name = os.path.join(root, potential_git_directory)
            if probable_non_bare_repository(full_name):
                relative_name = re.sub('^' + re.escape(new_start_path),
                                       '',
                                       full_name)
                git_directories.append(relative_name)
                directories_to_prune.append(i)
        for i in reversed(directories_to_prune):
            del dirs[i]
    return git_directories
