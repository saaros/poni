"""
version control with Git

Copyright (c) 2010-2012 Mika Eloranta
See LICENSE for details.

"""

from cStringIO import StringIO
import errno
import fnmatch
import os
import re

try:
    import dulwich
    from dulwich.objects import Blob
    from dulwich.patch import write_blob_diff
    from dulwich.repo import Repo
except ImportError:
    dulwich = None


VCS_IGNORE = [
    "*~",
    "*.pyc",
    "*.pyo",
    ]


class VersionControl(object):
    def __init__(self, repo_dir):
        self.repo_dir = repo_dir


class GitVersionControl(VersionControl):
    def __init__(self, repo_dir, init=False):
        assert dulwich, "dulwich not installed or too old"
        VersionControl.__init__(self, repo_dir)
        self.ignore_at_ctime = {}
        if init:
            self.git = self.init_repo(repo_dir)
        else:
            self.git = Repo(repo_dir)

    @staticmethod
    def init_repo(repo_dir):
        """create a new git repository and add .gitignore to it"""
        try:
            os.makedirs(repo_dir)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise
        git = Repo.init(repo_dir)
        open("{0}/.gitignore".format(repo_dir), "w").write("\n".join(VCS_IGNORE) + "\n")
        git.stage([".gitignore"])
        git.do_commit("initial commit")
        return git

    gaf_ignore = re.compile("^\\.|" + "|".join(fnmatch.translate(p) for p in VCS_IGNORE))
    @staticmethod
    def get_all_files(path):
        idx = 0
        dirs = [path]
        while len(dirs) > idx:
            entries = os.listdir(dirs[idx])
            for entry in entries:
                if GitVersionControl.gaf_ignore.match(entry):
                    continue
                fullname = os.path.join(dirs[idx], entry)
                if os.path.isdir(fullname):
                    dirs.append(fullname)
                else:
                    yield fullname[len(path)+1:]
            idx += 1

    def commit_all(self, message):
        self.git.stage(self.get_all_files(self.repo_dir))
        self.git.do_commit(message)

    def status(self):
        changes = 0
        untracked = set()
        index = self.git.open_index()
        for f in self.get_all_files(self.repo_dir):
            if f not in index:
                untracked.add(f)
                continue
            index_blob = index[f]
            index_blob_id = index_blob[-2]

            cwd_blob_path = os.path.join(self.repo_dir, f)
            cwd_blob_stat = os.stat(cwd_blob_path)
            if self.ignore_at_ctime.get(f) == cwd_blob_stat.st_ctime:
                continue  # had no changes at this ctime the last time, ignore
            if cwd_blob_stat.st_ctime == index_blob[0][0]:
                continue  # ctimes match, ignore

            cwd_blob_data = open(cwd_blob_path).read()
            cwd_blob = Blob.from_raw_string(Blob.type_num, cwd_blob_data)
            if cwd_blob.id == index_blob_id:
                # don't check this file again unless it changes
                self.ignore_at_ctime[f] = cwd_blob_stat.st_ctime
                continue

            if not changes:
                yield "Changes\n"
            changes += 1
            diff = StringIO()
            obj1 = (f, index_blob[4], self.git.get_blob(index_blob[8]))
            obj2 = (f, cwd_blob_stat.st_mode, cwd_blob)
            write_blob_diff(diff, obj1, obj2)
            yield diff.getvalue()

        if untracked:
            yield "\n\nUntracked files:\n"
            for file_path in untracked:
                yield "  %s\n" % file_path


def create_vc(repo_dir):
    if os.path.exists(os.path.join(repo_dir, ".git")):
        return GitVersionControl(repo_dir)
    else:
        return None
