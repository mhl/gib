#!/usr/bin/python3.1

from subprocess import call, Popen, PIPE, check_call
import re
import sys
import os
import errno
from tempfile import mkdtemp
from shutil import rmtree

# Find the umask, so we can extract files with appropriate permissions
original_umask = os.umask(0)
os.umask(original_umask)

if len(sys.argv) != 3:
    print("Usage: {} <refA> <refB>",file=sys.stderr)
    sys.exit(1)

ref1, ref2 = sys.argv[1:]

def check_ref(ref):
    print("Checking "+ref+":")
    return 0 == call(["git","rev-parse","--verify",ref])

ref1_ok = check_ref(ref1)
ref2_ok = check_ref(ref2)

if not (ref1_ok and ref2_ok):
    # git rev-parse will have output an error, so just exit
    sys.exit(1)

dir1 = mkdtemp()
dir2 = mkdtemp()

# From http://stackoverflow.com/questions/35817/whats-the-best-way-to-escape-os-system-calls-in-python
def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

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

def apply_to_blobs_in_tree(tree,f,path_prefix=""):
    for line in command_to_lines(["git","ls-tree","-z",tree],nul=True):
        m = re.search('(\S+)\s+(\S+)\s+(\S+)\s+(.*)',line)
        if m:
            mode, object_type, object_name, entry_name = m.groups()
            mode_int = int(mode,8)
            if object_type == "tree":
                apply_to_blobs_in_tree( object_name, f, os.path.join(path_prefix,entry_name) )
            elif object_type == "blob":
                f( object_name, entry_name, mode_int, path_prefix )

def print_blob( object_name, entry_name, mode_int, path_prefix ):
    print("{} {:o} {}".format(object_name,mode_int,os.path.join(path_prefix,entry_name)))

def create_extraction_closure(output_directory):
    def extract_blob_to(object_name,entry_name,git_file_mode,path_prefix):
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
    return extract_blob_to

def extract_tree_to(tree,output_directory):
    apply_to_blobs_in_tree( tree, create_extraction_closure(output_directory) )

try:
    extract_tree_to(ref1,dir1)
    extract_tree_to(ref2,dir2)
    call(["meld",dir1,dir2])
finally:
    rmtree(dir1)
    rmtree(dir2)
