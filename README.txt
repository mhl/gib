========================================================================

gib: Yet another git based backup system
----------------------------------------

gib is a script for backing up multiple directories to a single
git repository, so as to take advantage of git's efficient
storage of redundant data.  This script started as a rewrite of
gibak in Python 3.1, but now has significantly different
behaviour.

This has been only tested by myself (Mark) so far, so please use
this script with great caution.

You can find some brief guidance on installation and usage below.

  Copyright (c) 2007 Jean-Francois Richard <jean-francois@richard.name>
            (c) 2008 Mauricio Fernandez <mfp@acm.org>
            (c) 2009, 2010 Mark Longair <mark-gib@longair.net>

Installation:
-------------

The dependencies for this script can be installed with:

 sudo apt-get install git python3.1-minimal ocaml-nox rsync

You need to run "make" to create the binaries from ocaml.  Then
you need to copy (or symlink) the following files to somewhere on
your PATH:

  gib
  find-git-files
  find-git-repos
  ometastore

========================================================================

Usage A: (one home directory to back-up to ~/.git):
---------------------------------------------------

Create a repository in ~/.git/ for backing-up ~ to:

 $ gib init

Now edit ~/.gitignore here to exclude web browser caches,
temporary directories, etc.

Create your first backup of your home directory with:

 $ gib commit

Look at the output of "git status" which was printed at the end
of that output - check that you understand what is left as
modified or untracked after the commit.  (These may be files
that were created or modified while you were backing up, or
files that couldn't be added because they were too large or
unreadable.)

To record future states of your home directory, just run:

 $ gib commit

... again.

Usage B: (one home directory to back up to a removable disk):
-------------------------------------------------------------

Plug in your USB mass storage device, and say that's mounted as
/media/big-disk/.  Then you initialise a backup repository for
your home directory with:

 $ gib --git-directory=/media/big-disk/git-backups.git init

... and you can then commit the state of your home directory to
the master branch in that repository with:

 $ gib commit

... since the "init" step will create a file ~/.gib.conf which
specifies the git directory.  (As above, check that the "git
status" output looks reasonable.)

Usage C: (multiple home directories backed up to a single
repository on a removable disk):
---------------------------------------------------------

This is similar to Usage B, but you need to specify a branch
name for each home directory when you use "init".  For example,
if your computer is called "jupiter" and the removable disk is
mounted as above, you would initialize it with:

 $ gib --git-directory=/media/big-disk/git-backups.git \
       --branch=jupiter-home \
       init

Thereafter you can just run:

 $ gib commit

... to commit the state of your home directory as before.

Usage D: (multiple arbitrary directories backed up to a single
repository on a removable disk):
--------------------------------------------------------------

This is similar to usage D, but when initializing you need to
also specify the directory to back up.  e.g. if the situation is
as above, but you want to also back up the directory
/projects/robot/ to the same directory, you could do:

 $ gib --git-directory=/media/big-disk/git-backups.git \
       --directory=/projects/robot/ \
       --branch=robot \
       init

To record the state, you also have to specify the directory, so
that the configuration file that was created by init
(/projects/robot/.gib.conf) can be found.  i.e.:

 $ gib --directory=/projects/robot/ commit

========================================================================

Running arbitrary git commands on your backup:
----------------------------------------------

Your backup repository is just a normal git repository, but to
manipulate it you need to have the working tree and repository
set when calling git.  To make this simpler, you can just run
(for example):

 $ gib git status

... if you are backing up your home directory, or (for example):

 $ gib git -d /projects/robot status

... if you are backing up another directory.  (-d is just the
short form of --directory=, as used above.)

If you need to supply options to your git command, you will need
to use "--" to indicate to gib that it should stop parsing
options for itself.  So, for example, you would have to do:

 $ gib -- git ls-tree -r HEAD

... to stop gib from producing an error that it doesn't
understand the "-r" option.

========================================================================

Extracting a single file from your backup:
------------------------------------------

As an example, to output the most recent version of your .bashrc
to standard output, you can run:

 $ gib show .bashrc

You can also ask to see the file from an aribtrary version but
supplying a commit.  e.g. the version of bashrc from two backups
ago would be:

 $ gib show .bashrc HEAD^^

========================================================================

Extract a subdirectory (tree) from your backup:
-----------------------------------------------

(n.b. currently extracting a particular subtree with "extract"
will not preserve the permissions as "restore".  This is bug.)

To extract a complete subdirectory from your backup you can use
the "extract" subcommand of gib.  For example:

 $ gib extract Documents/papers/ /var/tmp/extracted-papers/

...  would create:

  /var/tmp/extracted-papers/Documents/papers/introduction.pdf
  /var/tmp/extracted-papers/Documents/papers/briefing.pdf
  /var/tmp/extracted-papers/Documents/papers/background.pdf
  ... etc.

========================================================================

Restoring a complete backup:
----------------------------

You can restore a backup to a directory with, for example:

 $ gib -g /media/big-disk/git-backups.git \
       -d /mnt/restored-home-directory \
       -b jupiter-home \
       restore

That will restore the directory that was backed-up to the branch
jupiter-home in the repository /media/big-disk/git-backups.git
to the directory /mnt/restored-home-directory, potentially
overwriting everything in that directory.

========================================================================

Saving disk space by "eating" large files:
------------------------------------------

If you have a large file which you would like to preserve in the
backup but no longer need in your home directory, you can use
the "eat" command to ensure that the contents of the files are
committed, and then removing them from the working tree.  For
example, you could use:

 $ gib eat disk-images/obselete-version.iso

... which will make sure that the current version of that file
is committed to your backup and then remove it from your home
directory.

========================================================================

Finding files in your backup:
-----------------------------

You can find files in the most recent backup that contain the
name "arthur", for example, with:

 $ gib -- git ls-files -r HEAD | grep -i arthur

If you want to search through the whole history of that
directory for a particular file, or find a file on any branch in
your repository, you might want to try the script
find-in-repository.py in this package.  For example, to find
files matching "arthur" in the complete history of your home
directory on jupiter, you might use:

 $ cd /media/big-disk/git-backups.git
 $ find-in-repository.py --all-history \
                         --start-ref=jupiter-home \
                         [aA]rthur

... or to find files matching that regular expression in any
branch in the repository in their entire history, you could try:

 $ cd /media/big-disk/git-backups.git
 $ find-in-repository.py --all-history [aA]rthur

(That will be very slow.)

If you know the file is under a particular tree, you can specify
that to speed up the search, e.g.:

 $ cd /media/big-disk/git-backups.git
 $ find-in-repository.py --start-tree=jupiter-home:audio [aA]rthur

The columns of output include the object name of the commit
which the files were found in, any readable ref names in the
second column (in brackets), the tree or blob's object name and
finally the name of the file.
