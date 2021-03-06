class Errors:
    '''enum-like values to use as exit codes'''
    USAGE_ERROR = 1
    DEPENDENCY_NOT_FOUND = 2
    VERSION_ERROR = 3
    GIT_CONFIG_ERROR = 4
    STRANGE_ENVIRONMENT = 5
    EATING_WITH_STAGED_CHANGES = 6
    BAD_GIT_DIRECTORY = 7
    BRANCH_EXISTS_ON_INIT = 8
    NO_SUCH_BRANCH = 9
    REPOSITORY_NOT_INITIALIZED = 10
    GIT_DIRECTORY_RELATIVE = 11
    FINDING_HEAD = 12
    BAD_TREE = 13
    GIT_DIRECTORY_MISSING = 14
    DIRECTORY_TO_BACKUP_MISSING = 15
