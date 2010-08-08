#!/usr/bin/python3.1

from subprocess import call, Popen, PIPE, check_call
import re
import sys
import os
import errno

# Find the umask, so we can extract files with appropriate permissions
original_umask = os.umask(0)
os.umask(original_umask)

if len(sys.argv) != 3:
    print("Usage: {} <tree-ish> <output-directory>".format(sys.argv[0]),file=sys.stderr)
    sys.exit(1)

treeish, output_directory = sys.argv[1:]

# From http://stackoverflow.com/questions/35817/whats-the-best-way-to-escape-os-system-calls-in-python
def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

# Get the output of a command, split on line endings or NUL ('\0'):
def command_to_lines(command,nul=False):
    p = Popen(command,stdout=PIPE)
    output = p.communicate()[0]
    if p.returncode != 0:
        print("'{}' failed.".format(' '.join(command),file=sys.stderr))
        sys.exit(1)
    str_output = output.decode()
    if nul:
        return str_output.split('\0')
    else:
        return str_output.splitlines(False)

# A generator that recursively parses the output of "git ls-tree -z" to
# yield a tupe for each blob in the tree:
def get_blobs_in_tree(tree,path_prefix=""):
    for line in command_to_lines(["git","ls-tree","-z",tree],nul=True):
        m = re.search('(\S+)\s+(\S+)\s+(\S+)\s+(.*)',line)
        if m:
            mode, object_type, object_name, entry_name = m.groups()
            mode_int = int(mode,8)
            if object_type == "tree":
                for t in get_blobs_in_tree(object_name,os.path.join(path_prefix,entry_name)):
                    yield t
            elif object_type == "blob":
                yield (object_name, entry_name, mode_int, path_prefix)

# Print out information about a blob:
def print_blob( object_name, entry_name, mode_int, path_prefix ):
    print("{} {:o} {}".format(object_name,mode_int,os.path.join(path_prefix,entry_name)))

# Extract a blob to an output directory + leading directory components:
def extract_blob_to(object_name,entry_name,git_file_mode,path_prefix,output_directory):
    destination = os.path.join(output_directory,path_prefix,os.path.dirname(entry_name))
    try:
        os.makedirs(destination)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    destination_filename = os.path.join(destination,
                                        os.path.basename(entry_name))
    if git_file_mode == 0o120000:
        # Then this is a symlink:
        p = Popen(["git","show",object_name],stdout=PIPE)
        symlink_destination = p.communicate()[0]
        check_call(["ln","-s",symlink_destination,destination_filename])
    else:
        check_call("git show {} > {}".format(
                object_name,
                shellquote(destination_filename)),shell=True)
        permissions = (git_file_mode % 0o1000) & ~ original_umask
        check_call(["chmod","{:o}".format(permissions),destination_filename])

for object_name, entry_name, git_file_mode, path_prefix in get_blobs_in_tree(treeish):
    print_blob(object_name, entry_name, git_file_mode, path_prefix)
    extract_blob_to(object_name, entry_name, git_file_mode, path_prefix, output_directory)
