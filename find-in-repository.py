#!/usr/bin/python3.1

from subprocess import Popen, PIPE, check_call
import re
import sys
import os
from optparse import OptionParser
import errno

# A small script for finding files in a git repository and optionally
# extracting them.  This is mostly useful for:
#
#   - Extracting trees from bare git repositories (normally you can
#     only extract single blobs with "git show".
#
#   - Finding files that you know appeared in the history at some
#     point, but can't remember where.
#
# ------------------------------------------------------------------------

# Find the umask, so we can extract files with appropriate permissions
original_umask = os.umask(0)
os.umask(original_umask)

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

parser = OptionParser(usage="Usage: %prog [OPTIONS] PATH-REGEXP")
parser.add_option('--extract-to', '-e',
                  dest="extract_to",
                  metavar="[DIR]",
                  default=None,
                  help="extract matching files to [DIR]")
parser.add_option('--start-ref',
                  dest="start_ref",
                  metavar="[REF]",
                  default=None,
                  help="instead of going through all refs, just do [REF]")
parser.add_option('--start-tree',
                  dest="start_tree",
                  metavar="[TREE]",
                  default=None,
                  help="instead of going through all refs, start at the tree object [TREE]")
parser.add_option('--all-history','-a',
                  action="store_true",
                  dest="all_history",
                  default=False,
                  help="when starting from refs, look through their complete history")

options,args = parser.parse_args()

if len(args) != 1:
    parser.print_help()
    sys.exit(1)

extract = options.extract_to

if extract:
    if not os.path.exists(extract):
        print("The directory '{}' doesn't exist.".format(extract),file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(extract):
        print("'{}' is not a directory.".format(extract),file=sys.stderr)
        sys.exit(1)

path_regexp = args[0]

all_refs = {}

if options.start_ref and options.start_tree:
    print("You can't specify both a start ref and a start tree",file=sys.stderr)
    sys.exit(1)

if options.start_tree and options.all_history:
    print("You can't search all history when starting from a particular tree",file=sys.stderr)
    sys.exit(1)

if options.start_ref:
    for line in command_to_lines(['git','rev-parse',options.start_ref]):
        m = re.search('(\S+)',line)
        if m:
            object_name = m.group(1)
            all_refs.setdefault(object_name,[])
            all_refs[object_name].append(options.start_ref)
else:
    for line in command_to_lines(["git","for-each-ref"]):
        m = re.search('(\S+)\s+\S+\s+(\S+)',line)
        if m:
            object_name = m.group(1)
            all_refs.setdefault(object_name,[])
            all_refs[object_name].append(m.group(2))

# Cache all already explored trees:
trees_dictionary = {}

def tree_to_recursive_list(tree):
    if tree in trees_dictionary:
        return trees_dictionary[tree]
    files = []
    for line in command_to_lines(["git","ls-tree","-z",tree],nul=True):
        m = re.search('(\S+)\s+(\S+)\s+(\S+)\s+(.*)',line)
        if m:
            mode, object_type, object_name, entry_name = m.groups()
            mode_int = int(mode,8) % 0o1000
            if object_type == "tree":
                files_in_tree = tree_to_recursive_list(object_name)
                for t in files_in_tree:
                    files.append((t[0],os.path.join(entry_name,t[1]),t[2]))
            elif object_type == "blob":
                files.append((object_name,entry_name,mode_int))
    trees_dictionary.setdefault(tree,files)
    return files

def deal_with_tree(tree,prefix,d='.'):
    for t in tree_to_recursive_list(tree):
        if re.search(path_regexp,t[1]):
            print("{} {} {}".format(prefix,t[0],t[1]))
            if extract:
                destination = os.path.join(extract,d,os.path.dirname(t[1]))
                try:
                    os.makedirs(destination)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                destination_filename = os.path.join(destination,
                                                    os.path.basename(t[1]))
                check_call("git show {} > {}".format(
                        t[0],
                        shellquote(destination_filename)),shell=True)
                permissions = t[2] & ~ original_umask
                check_call(["chmod","{:o}".format(permissions),destination_filename])

if options.start_tree:
    deal_with_tree(options.start_tree,'None ()')
else:
    for r in all_refs:
        prefix = "{} ({})".format(r,','.join(all_refs[r]))
        deal_with_tree(r,prefix,r)
        if options.all_history:
            for commit in command_to_lines(["git","log","--format=%H",r])[1:]:
                prefix = commit+" ()"
                deal_with_tree(commit,prefix,commit)