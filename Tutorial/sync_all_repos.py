
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# .git이 있는 최상위 폴더에 있는 모든 git repo에 대해 fetch -> pull -> push를 한다.
# 폴더 최상위에 py파일을 두고, run python file 클릭해주시면 됩니다.
# 본, 파일은 python 3.11.9 인터프리터 에서 작동함을 확인했습니다.
"""
sync_all_repos.py
- Walk a ROOT directory and for each git repo, do: fetch -> pull -> push
- Modes:
    safe       : skip dirty trees, pull --ff-only
    aggressive : pull --rebase --autostash (may rewrite local commits)
Usage:
    python sync_all_repos.py --root "D:\Total" --mode safe
    python sync_all_repos.py --root "D:\Total" --mode aggressive
"""
import os
import sys
import argparse
import subprocess
from datetime import datetime

def sh(cmd, cwd=None, check=False):
    """Run a shell command and return (rc, out, err)."""
    try:
        p = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        out, err = p.communicate()
        out = out.strip() if out else ""
        err = err.strip() if err else ""
        
        if check and p.returncode != 0:
            raise subprocess.CalledProcessError(
                p.returncode, cmd, output=out, stderr=err
            )
            
        return p.returncode, out, err
    except Exception as e:
        print(f"[ERROR] Command failed: {cmd}")
        print(f"        Error: {str(e)}")
        return -1, "", str(e)

def is_git_repo(path):
    # consider both .git dir and file
    git_path = os.path.join(path, ".git")
    if os.path.isdir(git_path) or os.path.isfile(git_path):
        # also confirm with git
        rc, out, _ = sh('git rev-parse --is-inside-work-tree', cwd=path)
        return rc == 0 and out.strip() == 'true'
    return False

def current_branch(path):
    rc, out, _ = sh('git symbolic-ref -q --short HEAD', cwd=path)
    return out.strip() if rc == 0 and out.strip() else None

def upstream(path):
    rc, out, _ = sh('git rev-parse --abbrev-ref "@{u}"', cwd=path)
    return out.strip() if rc == 0 and out.strip() else None

def is_dirty(path):
    rc, out, _ = sh('git status --porcelain', cwd=path)
    return bool(out.strip())

def ahead_behind(path):
    rc, out, _ = sh('git rev-list --left-right --count @{u}...HEAD', cwd=path)
    if rc != 0 or not out.strip():
        return (None, None)
    parts = out.split()
    if len(parts) >= 2:
        behind = int(parts[0])
        ahead = int(parts[1])
        return (behind, ahead)
    return (None, None)

def fetch_all(path, log):
    rc, _, err = sh('git fetch --all --prune')
    if rc != 0:
        log.append(f"  [ERR] fetch failed: {err}")
    return rc == 0

def pull_safe(path, log):
    rc, _, err = sh('git pull --ff-only', cwd=path)
    if rc != 0:
        log.append(f"  [ERR] pull --ff-only failed: {err}")
    return rc == 0

def pull_aggressive(path, log):
    rc, _, err = sh('git pull --rebase --autostash', cwd=path)
    if rc != 0:
        log.append(f"  [ERR] pull --rebase --autostash failed: {err}")
    return rc == 0

def push_if_ahead(path, log):
    behind, ahead = ahead_behind(path)
    log.append(f"  [STATE] behind={behind} ahead={ahead}")
    if ahead is not None and ahead > 0:
        rc, _, err = sh('git push', cwd=path)
        if rc != 0:
            log.append(f"  [ERR] push failed: {err}")
            return False
        log.append("  [PUSH] pushed upstream")
        return True
    return True

def walk_repos(root):
    # Walk and yield repo roots (where .git exists as file or dir)
    for base, dirs, files in os.walk(root):
        if '.git' in dirs or '.git' in files:
            yield base
            # don't recurse deeper into this repo
            dirs[:] = [d for d in dirs if d == '.git']  # limit traversal
        # avoid descending into .git internals
        if '.git' in dirs:
            dirs.remove('.git')

def main():
    # Get the directory where this script is located
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description='Sync multiple git repositories')
    parser.add_argument('--root', default=SCRIPT_DIR, 
                      help=f'Root directory containing git repositories (default: {SCRIPT_DIR})')
    parser.add_argument('--mode', choices=['safe', 'aggressive'], default='safe',
                      help='Sync mode: safe (ff-only) or aggressive (rebase)')
    args = parser.parse_args()

    # Convert to absolute path and normalize
    root = os.path.abspath(os.path.normpath(args.root))
    if not os.path.isdir(root):
        print(f"Error: Directory not found: {root}", file=sys.stderr)
        return 1
        
    print(f"Script location: {SCRIPT_DIR}")

    print(f"Syncing repositories in: {root}")
    print(f"Mode: {args.mode}")
    print("-" * 50)

    for repo_path in walk_repos(root):
        print(f"\nProcessing: {repo_path}")
        
        if not is_git_repo(repo_path):
            print("  [WARN] Not a valid git repository")
            continue
            
        branch = current_branch(repo_path)
        if not branch:
            print("  [WARN] Could not determine current branch")
            continue
            
        print(f"  Branch: {branch}")
        # Check for uncommitted changes and commit them
        if is_dirty(repo_path):
            print("  Uncommitted changes found, committing...")
            # Add all changes
            rc, out, err = sh('git add .', cwd=repo_path)
            if rc != 0:
                print(f"  [ERROR] Failed to stage changes: {err}")
                continue
            # Commit with auto message
            commit_msg = f"Auto-commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            rc, out, err = sh(f'git commit -m "{commit_msg}"', cwd=repo_path)
            if rc != 0:
                print(f"  [ERROR] Failed to commit changes: {err}")
                continue
            print("  Successfully committed changes")
            # Push the committed changes
            rc, out, err = sh('git push', cwd=repo_path)
            if rc != 0:
                print(f"  [ERROR] Failed to push changes: {err}")
                continue
            print("  Successfully pushed changes")
            
        up = upstream(repo_path)
        if not up:
            print("  [WARN] No upstream branch set")
            continue
            
        ahead, behind = ahead_behind(repo_path)
        print(f"  Upstream: {up} (ahead: {ahead or 0}, behind: {behind or 0})")
        
        # Fetch updates
        print("  Fetching...")
        rc, out, err = sh('git fetch --all --prune', cwd=repo_path)
        if rc != 0:
            print(f"  [ERROR] Fetch failed: {err}")
            continue
            
        # Pull changes
        print(f"  Pulling ({args.mode} mode)...")
        if args.mode == 'safe':
            rc, out, err = sh('git pull --ff-only', cwd=repo_path)
        else:
            rc, out, err = sh('git pull --rebase --autostash', cwd=repo_path)
            
        if rc != 0:
            print(f"  [ERROR] Pull failed: {err}")
            continue
            
        # Check if there are local commits to push
        rc, out, err = sh('git log --branches --not --remotes --oneline', cwd=repo_path)
        if out.strip():  # If there are local commits not pushed
            print("  Local commits found, pushing...")
            rc, out, err = sh('git push --force-with-lease', cwd=repo_path)
            if rc == 0:
                print("  Successfully pushed local commits")
            else:
                print(f"  [ERROR] Push failed: {err}")
        else:
            print("  No local commits to push")
            
    print("\nSync complete!")
    return 0

if __name__ == "__main__":
    main()
