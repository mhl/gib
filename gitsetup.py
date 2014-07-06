from configparser import RawConfigParser
import os
import re
from subprocess import call, check_call, Popen, PIPE, STDOUT
import sys

from errors import Errors
from general import (
    exists_and_is_directory, shellquote, print_stderr
)
from githelpers import has_objects_and_refs

class OptionFrom:
    '''enum-like values to indicate the source of different options, used in
    directory_to_backup_from, git_directory_from and branch_from'''
    COMMAND_LINE = 1
    CONFIGURATION_FILE = 2
    DEFAULT_VALUE = 3
    string_versions = { COMMAND_LINE : "command line",
                        CONFIGURATION_FILE : "configuration file",
                        DEFAULT_VALUE : "default value" }

class GibSetup:
    def __init__(self, command_line_options):

        self.configuration_file = '.gib.conf'

        self.directory_to_backup = None
        self.directory_to_backup_from = None

        self.git_directory = None
        self.git_directory_from = None

        self.branch = None
        self.branch_from = None

        if command_line_options.directory:
            self.directory_to_backup = command_line_options.directory
            self.directory_to_backup_from = OptionFrom.COMMAND_LINE
        else:
            if 'HOME' not in os.environ:
                # Then we can't use HOME as default directory:
                print_stderr("The HOME environment variable was not set")
                sys.exit(Errors.STRANGE_ENVIRONMENT)
            self.directory_to_backup = os.environ['HOME']
            self.directory_to_backup_from = OptionFrom.DEFAULT_VALUE

        # We need to make sure that this is an absolute path before
        # changing directory:

        self.directory_to_backup = os.path.abspath(self.directory_to_backup)

        if not exists_and_is_directory(self.directory_to_backup):
            sys.exit(Errors.DIRECTORY_TO_BACKUP_MISSING)

        # Now we know the directory that we're backing up, try to load the
        # config file:

        configuration = RawConfigParser()
        configuration.read(os.path.join(self.directory_to_backup,
                                        self.configuration_file))

        # Now set the git directory:

        if command_line_options.git_directory:
            self.git_directory = command_line_options.git_directory
            self.git_directory_from = OptionFrom.COMMAND_LINE
        elif configuration.has_option('repository','git_directory'):
            self.git_directory = configuration.get(
                'repository','git_directory'
            )
            self.git_directory_from = OptionFrom.CONFIGURATION_FILE
        else:
            self.git_directory = os.path.join(self.directory_to_backup,'.git')
            self.git_directory_from = OptionFrom.DEFAULT_VALUE

        if not os.path.isabs(self.git_directory):
            print_stderr("The git directory must be an absolute path.")
            sys.exit(Errors.GIT_DIRECTORY_RELATIVE)

        # And finally the branch:

        if command_line_options.branch:
            self.branch = command_line_options.branch
            self.branch_from = OptionFrom.COMMAND_LINE
        elif configuration.has_option('repository','branch'):
            self.branch = configuration.get('repository','branch')
            self.branch_from = OptionFrom.CONFIGURATION_FILE
        else:
            self.branch = 'master'
            self.branch_from = OptionFrom.DEFAULT_VALUE

        # Check that the git_directory ends in '.git':

        if not re.search('\.git/*$',self.git_directory):
            message = "The git directory ({}) did not end in '.git'"
            print_stderr(message.format(self.git_directory))
            sys.exit(Errors.BAD_GIT_DIRECTORY)

        # Also check that it actually exists:

        if not os.path.exists(self.git_directory):
            message = "The git directory '{}' does not exist."
            print_stderr(message.format(self.git_directory))
            sys.exit(Errors.GIT_DIRECTORY_MISSING)

    def get_directory_to_backup(self):
        return self.directory_to_backup

    def get_git_directory(self):
        return self.git_directory

    def get_file_list_directory(self):
        return os.path.join(
            self.get_git_directory(),
            'file-lists'
        )

    def get_branch(self):
        return self.branch

    def print_settings(self):
        print_stderr('''Settings for backup:
backing up the directory {} (set from the {})
... to the branch "{}" (set from the {})
... in the git repository {} (set from the {})'''.format(
                self.directory_to_backup,
                OptionFrom.string_versions[self.directory_to_backup_from],
                self.branch,
                OptionFrom.string_versions[self.branch_from],
                self.git_directory,
                OptionFrom.string_versions[self.git_directory_from]),
        )

    def get_invocation(self):
        '''Return an invocation that would run the script with options
        that will set directory_to_backup, git_directory and branch as on
        this invocation.  After init has been called, we can just specify
        the directory to backup, since the configuration file .gib.conf in
        that directory will store the git_directory and the branch.  If
        the directory to backup is just the current user's home directory,
        then that doesn't need to be specified either.'''
        invocation = sys.argv[0]
        if self.directory_to_backup != os.environ['HOME']:
            invocation += " " + "--directory="
            invocation += shellquote(self.directory_to_backup)
        return invocation

    def git(self,rest_of_command):
        '''Create an list (suitable for passing to subprocess.call or
        subprocess.check_call) which runs a git command with the correct
        git directory and work tree'''
        return [ "git",
                 "--git-dir="+self.git_directory,
                 "--work-tree="+self.directory_to_backup ] + rest_of_command

    def git_for_shell(self):
        '''Returns a string with shell-safe invocation of git which can be used
        in calls that are subject to shell interpretation.'''
        command = "git --git-dir="+shellquote(self.git_directory)
        command += " --work-tree="+shellquote(self.directory_to_backup)
        return command

    def git_initialized(self):
        '''Returns True if it seems as if the git directory has already
        been intialized, and returns False otherwise'''
        return has_objects_and_refs(self.git_directory)

    def abort_if_not_initialized(self):
        '''Check that the git repository exists and exit otherwise'''
        if not self.git_initialized():
            message = "You don't seem to have initialized {} for backup."
            print_stderr(message.format(self.directory_to_backup))
            message = "Please use '{} init' to initialize it"
            print_stderr(message.format(self.get_invocation()))
            sys.exit(Errors.REPOSITORY_NOT_INITIALIZED)

    def check_ref(self,ref):
        '''Returns True if a ref can be resolved to a commit and False
        otherwise.'''
        return 0 == call(
            self.git(["rev-parse","--verify",ref]),
            stdout=open('/dev/null','w'),
            stderr=STDOUT
        )

    def check_tree(self,tree):
        '''Returns True if 'tree' can be understood as a tree, e.g. with
        "git ls-tree" or false otherwise'''
        with open('/dev/null','w') as null:
            return 0 == call(
                self.git(["ls-tree",tree]),
                stdout=null,
                stderr=STDOUT
            )

    def set_HEAD_to(self,ref):
        '''Update head to point to a particular branch, without touching
        the index or the working tree'''
        check_call(
            self.git(["symbolic-ref","HEAD","refs/heads/{}".format(ref)])
        )

    def currently_on_correct_branch(self):
        '''Return True if HEAD currently points to 'self.branch', and
        return False otherwise.'''
        p = Popen(self.git(["symbolic-ref","HEAD"]),stdout=PIPE)
        c = p.communicate()
        if 0 != p.returncode:
            print_stderr("Finding what HEAD points to failed")
            sys.exit(Errors.FINDING_HEAD)
        result = c[0].decode().strip()
        if self.branch == result:
            return True
        elif ("refs/heads/"+self.branch) == result:
            return True
        else:
            return False

    def switch_to_correct_branch(self):
        self.set_HEAD_to(self.branch)
        self.abort_unless_HEAD_exists()
        # Also reset the index to match HEAD.  Otherwise things go
        # horribly wrong when switching from backing up one computer to
        # another, since the index is still that from the first one.
        msg = "Now working on a new branch, so resetting the index to match..."
        print_stderr(msg)
        check_call(self.git(["read-tree","HEAD"]))

    def config_value(self,key):
        '''Retrieve the git config value for "key", or return
        None if it is not defined'''
        p = Popen(self.git(["config",key]),stdout=PIPE)
        c = p.communicate()
        if 0 == p.returncode:
            # Then check that the option is right:
            return c[0].decode().strip()
        else:
            return None

    def set_config_value(self,key,value):
        check_call(self.git(["config",key,value]))

    def unset_config_value(self,key):
        call(self.git(["config","--unset",key]))

    def abort_unless_particular_config(self,key,required_value):
        '''Unless the git config has "required_value" set for "key", exit.'''
        current_value = self.config_value(key)
        if current_value:
            if current_value != required_value:
                message = "The current value for {} is {}, should be: {}"
                print_stderr(message.format(
                    key,
                    current_value,
                    required_value
                ))
                sys.exit(Errors.GIT_CONFIG_ERROR)
        else:
            message = "The {} config option was not set, setting to {}"
            print_stderr(message.format(key,required_value))
            self.set_config_value(key,required_value)

    def abort_unless_no_auto_gc(self):
        '''Exit unless git config has gc.auto set to "0"'''
        self.abort_unless_particular_config("gc.auto","0")

    def abort_unless_HEAD_exists(self):
        if not self.check_ref("HEAD"):
            message = '''The branch you are trying to back up to does not exist.
(Perhaps you haven't run "{} init")'''
            print_stderr(message.format(self.get_invocation()))
            sys.exit(Errors.NO_SUCH_BRANCH)
