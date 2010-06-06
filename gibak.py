#!/usr/bin/python3.1

# Copyright (c) 2007 Jean-Francois Richard <jean-francois@richard.name>
#           (c) 2008 Mauricio Fernandez <mfp@acm.org>
#           (c) 2009, 2010 Mark Longair <mark-gibak.py@longair.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

# ------------------------------------------------------------------------

# The script reimplements some of the "gibak" script in Python 3.1,
# and changes its behaviour in a couple of key respects.  For more
# information, please see [FIXME: write a blog post about this...]

from subprocess import call, check_call, Popen, PIPE
import errno
import sys
import re
import os
import stat
import datetime
from optparse import OptionParser

required_git_version = [ 1, 7, 0, 3 ]
required_git_version_reason = """(This script requires a version that honours the config
option gc.pruneExpire being set to 'never'.)"""

script_name = sys.argv[0]

hostname = Popen(["hostname"],stdout=PIPE).communicate()[0].decode().strip()

def abort_on_no(name):
    try:
        p = Popen([name, "--version"], stdout=PIPE)
    except OSError as e:
        if e.errno == errno.ENOENT:
            print(name+" is not your PATH",file=sys.stderr)
            sys.exit(1)
        else:
            # Re-raise any other error:
            raise
    c = p.communicate()
    if p.returncode != 0:
        print("'git --version' failed",file=sys.stderr)
        sys.exit(2)
    output = c[0].decode()
    return output

def abort_unless_never_prune():
    required_setting = "never"
    p = Popen(["git","config","gc.pruneExpire"],stdout=PIPE)
    c = p.communicate()
    if 0 == p.returncode:
        # Then check that the option is right:
        current_value = c[0].decode().strip()
        if current_value != required_setting:
            print("The current value for gc.pruneExpire is "+current_value+", should be: "+required_setting,file=sys.stderr)
            sys.exit(12)
    else:
        print("The gc.pruneExpire config option was not set, setting to "+required_setting,file=sys.stderr)
        check_call(["git","config","gc.pruneExpire",required_setting])

# Check that git is on your PATH and find the version:

output = abort_on_no("git")
m = re.search('^git version (.*)$',output)
if not m:
    print("The git version string ('{}') was of an unknown format".format(output),file=sys.stderr)
    sys.exit(3)
git_version = m.group(1).strip()

def int_or_still_string(s):
    try:
        return int(s,10)
    except ValueError:
        return s

git_version_split = [ int_or_still_string(x) for x in git_version.split('.') ]

if not git_version_split >= required_git_version:
    print("Your git version is "+git_version+", version "+(".".join(required_git_version))+" is required:\n")
    print(required_git_version_reason)
    sys.exit(8)

if 'HOME' not in os.environ:
    print("The HOME environment variable was not set",file=sys.stderr)
    sys.exit(4)

usage_message = '''Usage: %prog [OPTIONS] COMMAND

COMMAND must be one of:

    init
    commit'''

parser = OptionParser(usage=usage_message)
parser.add_option('--directory',
                  dest="directory",
                  default=os.environ['HOME'],
                  help="directory to backup [default %default]")
options,args = parser.parse_args()

directory_to_backup = options.directory
os.chdir(directory_to_backup)

old_umask = os.umask(0o077)

# print("Set umask to 0o077; the old umask was: 0o{:03o}".format(old_umask))

def exists_and_is_directory(path):
    if not os.path.exists(path):
        return False
    real_path = os.path.realpath(path)
    mode = os.stat(real_path)[stat.ST_MODE]
    if not stat.S_ISDIR(mode):
        raise Exception("{} ({}) existed, but was not a directory".format(path,real_path))
    return True

def has_objects_refs(path):
    objects_path = os.path.join(path,"objects")
    refs_path = os.path.join(path,"refs")
    return exists_and_is_directory(objects_path) and exists_and_is_directory(refs_path)

def git_initialized():
    path = os.path.join(directory_to_backup,".git")
    return has_objects_refs(path)

def abort_if_initialized():
    if git_initialized():
        print("You already have git data in "+directory_to_backup,file=sys.stderr)
        print("Please use '{} rm-all' if you wish to *delete* it.".format(script_name),file=sys.stderr)
        sys.exit(5)

def require_work_tree():
    return 0 == call(['sh','-c','. $(git --exec-path)/git-sh-setup && require_work_tree'])

def abort_if_not_initialized():
    if not git_initialized():
        print("You probably did not initialize your home history repository",file=sys.stderr)
        print("Please use '{} init' to initialize it".format(script_name),file=sys.stderr)
        sys.exit(6)
    if not require_work_tree():
        print("There was no valid git working tree in "+directory_to_backup,file=sys.stderr)
        sys.exit(7)

# def find_git_repositories(start_path=directory_to_backup):
#     repository_directories = set([])
#     for root, dirs, files in os.walk(start_path):
#         if has_objects_refs(root):
#             repository_directories.add(os.path.realpath(root))
#     return repository_directories

def find_git_repositories(start_path=directory_to_backup):
    p = Popen(["find-git-repos","-i","-z"],stdout=PIPE)
    c = p.communicate()
    return [ x for x in c[0].decode().split('\0') if len(x) > 0 ]

def ensure_trailing_slash(path):
    return re.sub('/*$','/',path)

def handle_git_repositories(start_path=directory_to_backup):
    abort_if_not_initialized()
    check_call(["rm","-f",".gitmodules"])
    base_directory = os.path.join(start_path,os.path.join(".git","git-repositories"))
    check_call(["mkdir","-p",base_directory])
    for r in find_git_repositories(start_path):
        r_dot_git = ensure_trailing_slash(os.path.join(r,".git"))
        relative_repository = re.sub('^/*','',r_dot_git)
        destination_repository = os.path.join(base_directory,relative_repository)
        call(["mkdir","-p","-v",os.path.split(destination_repository)[0]])
        print("rsyncing: "+r+" => "+destination_repository)
        check_call(["rsync","-rltD","--relative","--delete-after","--delay-updates",r_dot_git,destination_repository])
        fp = open(".gitmodules","a")
        fp.write('''[submodule "%s"]
    path = %s
    url= %s
''' % (r,r,destination_repository))
        fp.close()
    check_call(["touch",".gitmodules"])
    check_call(["git","add","-f",".gitmodules"])
    check_call(["git","submodule","init"])

def init():
    abort_if_initialized()

    check_call("git","init","--shared=umask")
    check_call("chmod","-R","u+rwX,go-rwx",".git")

    fp = open(os.path.join(".git","description"),"w")
    fp.write("Backup of {} on {}".format(directory_to_backup,hostname))
    fp.close()

    default_user_name = re.sub(',.*$','',pwd.getpwuid(os.getuid())[4])
    if 0 != call(["git","config","user.name"]):
        call(["git","config","user.name",default_user_name])

    hooks_directory = os.path.join(".git","hooks")

    pre_commit_hook_path = os.path.join(hooks_directory,"pre-commit")
    post_checkout_hook_path = os.path.join(hooks_directory,"post-checkout")

    fp = open(pre_commit_hook_path,"w")
    fp.write('''#!/bin/sh
ometastore -x -s -i --sort
git add -f .ometastore''')
    fp.close()

    fp = open(post_checkout_hook_path,"w")
    fp.write('''#!/bin/sh
ometastore -v -x -a -i''')

    for h in ( pre_commit_hook_path, post_checkout_hook_path ):
        check_call(["chmod","u+x",h])

    if not os.path.exists(".gitignore"):
        fp = open(".gitignore","w")
        fp.write('''# Here are some examples of what you might want to ignore
# in your git-home-history.  Feel free to modify.
##
# The rules are read from top to bottom, so a rule can
# "cancel" out a previous one.  Be careful.
#
# For more information on the syntax used in this file,
# see "man gitignore" in a terminal or visit
# http://www.kernel.org/pub/software/scm/git/docs/gitignore.html
''')

    check_call(["git","add","-f",".gitignore"])
    check_call(["git","commit","-q","-a","-mInitialized by "+script_name])

    suggestion = '''You might be interested in tweaking the file:

  {}

Please run '{} commit' to save a first state in your history'''

    print(suggestion.format(os.path.join(directory_to_backup,'.gitignore'),
                            script_name))

def modified_or_untracked():
    p = Popen(["git","ls-files","-z","--modified","--others","--exclude-standard"],stdout=PIPE)
    c = p.communicate()
    if p.returncode != 0:
        print("Finding the modified files failed",file=sys.stderr)
        sys.exit(10)
    return [ x for x in c[0].decode().split('\0') if len(x) > 0 ]

def commit():
    abort_if_not_initialized()

    if [ x for x in modified_or_untracked() if re.search('(^|/).gitignore$',x) ]:
        print("Some .gitignore added or modified, determining newly ignored files.",file=sys.stderr)
        check_call("ometastore -d -i -z | xargs -0 git rm --cached -r -f --ignore-unmatch -- 2>/dev/null",shell=True)

    print("Adding new and modified files.",file=sys.stderr)

    command = [ "git", "add", "-v", "--ignore-errors" ]
    command.append(".")

    if 0 != call(command):
        print("Could not complete addition of files to history store!",file=sys.stderr)
        sys.exit(11)

    print("Removing deleted files from the repository",file=sys.stderr)
    check_call("git ls-files --deleted -z | xargs -0 -r git rm --ignore-unmatch",shell=True)

    print("Using rsync to back up git repositories (not working trees)",file=sys.stderr)
    handle_git_repositories()

    print("Committing the new state of "+directory_to_backup,file=sys.stderr)
    command = [ "git",
                "commit",
                "-m",
                "Committed on "+datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z") ]
    check_call(command)

    print("Optimizing and compacting repository (might take a while).",file=sys.stderr)
    check_call(["git","gc","--auto"])

if len(args) != 1:
    parser.print_help()
    print("Expected exactly one command",file=sys.stderr)
    sys.exit(9)

command = args[0]

if command == "init":
    init()
    abort_unless_never_prune()
elif command == "commit":
    abort_unless_never_prune()
    commit()
    print("After committing the new backup, git status is:",file=sys.stderr)
    print(Popen(["git","status"],stdout=PIPE).communicate()[0].decode())
else:
    print("Unknown command '{}'".format(command))
