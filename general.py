# These are useful functions used by gib that are not specifically
# related to git.

from contextlib import contextmanager
import datetime
import errno
import os
from os.path import realpath
import pwd
import re
import stat
from subprocess import Popen, PIPE
import sys

from errors import Errors

def get_hostname():
    '''Return the unqualified hostname of this computer'''
    return Popen(["hostname"],stdout=PIPE).communicate()[0].decode().strip()

def current_date_and_time_string():
    return datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

def get_real_name():
    return re.sub(',.*$','',pwd.getpwuid(os.getuid())[4])

def shellquote(s):
    '''Quote a string to protect it from the shell.  This implementation is
    suggested in:
    http://stackoverflow.com/questions/35817/whats-the-best-way-to-escape-os-system-calls-in-python
    '''
    return "'" + s.replace("'", "'\\''") + "'"

def mkdir_p(path):
    '''The equivalent of 'mkdir -p' in Python

    This implementation is from http://stackoverflow.com/a/600612/223092
    '''
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def run_with_option_or_abort(name,option="--version"):
    '''Try to run the program "name" with "option"; if "name" is not
    on your PATH, exit.  If the command fails, exit.  If the command
    succeeds, return what the command printed to stdout.'''
    try:
        p = Popen([name, option], stdout=PIPE)
    except OSError as e:
        if e.errno == errno.ENOENT:
            print(name+" is not your PATH",file=sys.stderr)
            sys.exit(Errors.DEPENDENCY_NOT_FOUND)
        else:
            # Re-raise any other error:
            raise
    c = p.communicate()
    if p.returncode != 0:
        print("'{} {}' failed".format(name,option),file=sys.stderr)
        sys.exit(Errors.VERSION_ERROR)
    output = c[0].decode()
    return output

def exists_and_is_directory(path):
    '''Returns True if <path> exists and (after resolving any
    symlinks) is a directory.  Otherwise returns False.'''
    if not os.path.exists(path):
        return False
    real_path = realpath(path)
    mode = os.stat(real_path)[stat.ST_MODE]
    if not stat.S_ISDIR(mode):
        raise Exception("{} ({}) existed, but was not a directory".format(path,real_path))
    return True

def map_filename_for_directory_change(f, original_current_directory, directory_to_backup):
    '''In commands when we specify files or directories, we would like
    to be able to tab-complete relative filenames.  This method maps a
    filename relative to the original working directory to a filename
    relative to the directory that is being backed up.'''
    if os.path.isabs(f):
        return os.path.relpath(f, directory_to_backup)
    else:
        return os.path.relpath(os.path.join(original_current_directory,f),
                               directory_to_backup)

def ensure_trailing_slash(path):
    '''If path ends in a slash, return path, otherwise return path
    with a trailing slash added'''
    return re.sub('/*$','/',path)

# This is reformatted version of the recipe here:
#    http://bugs.python.org/issue1152248
# It's amazing that there's nothing like this built into Python...

def file_iter_bytes_records(input_file,
                            separator=b'\n',
                            output_separator=None,
                            read_size=8192):
   '''Like the normal file iter but you can set what string indicates
   newline.

   The newline string can be arbitrarily long; it need not be
   restricted to a single character.  You can also set the read size
   and control whether or not the newline string is left on the end of
   the iterated lines.  Setting newline to b'\0' is particularly good
   for use with an input file created with something like
   "os.popen('find -print0')".'''
   if output_separator is None:
       output_separator = separator
   partial_line = bytes()
   while True:
       just_read = input_file.read(read_size)
       if not just_read:
           break
       partial_line += just_read
       lines = partial_line.split(separator)
       partial_line = lines.pop()
       for line in lines:
           yield line + output_separator
   if partial_line:
       yield partial_line

@contextmanager
def cd(path):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)
