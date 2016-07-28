#!/usr/bin/env python3
import os
import sys
import subprocess
from urllib.request import urlopen
from http.client import BadStatusLine
from urllib.error import HTTPError

BASE = os.path.dirname(__file__)

def run_tests(test_projects):
    test_procs = []
    errors = []
    for project in test_projects:
        project_base = os.path.join(BASE, "projects", project)
        # Create a commit so we can push.
        print("################################")
        print("{}: {}".format(project, project_base))
        print("checkout master")
        subprocess.check_call(["git", "-C", project_base, "checkout", "master"])
        print("add empty commit")
        subprocess.check_call([
            "git", "-C", project_base, "commit", "--allow-empty", "-m", "Rebuild"
        ])
        # Push to heroku.
        print("Push to heroku")
        proc = subprocess.Popen(
            ["git", "-C", project_base, "push", "--force", "heroku", "master"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        test_procs.append({
            'name': project,
            'proc': proc,
            'basedir': project_base
        })
        test = test_procs[-1]

        # Wait for heroku build to finish.
        stdout, stderr = test['proc'].communicate()
        # Revert the commit.
        subprocess.check_call(["git", "-C", test['basedir'], "reset", "--hard", "HEAD~1"])
        # Check the result.
        if test['proc'].returncode != 0:
            errors.append({
                'name': test['name'],
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'code': test['proc'].returncode
            })
            print(errors[-1]['stderr'])
        else:
            print(stdout.decode('utf-8'))
            print(stderr.decode('utf-8'))
            # Build succeeded -- try curl'ing page.
            root_url = subprocess.check_output(
                ["heroku", "config:get", "ROOT_URL"],
                cwd=test['basedir']
            ).decode('utf-8').strip()
            if not root_url:
                # dyno-metadata won't have a root URL; punt on it.
                print("Skipping GET for {} (ROOT_URL not defined)".format(test['name']))
                continue
            try:
                res = urlopen(root_url)
                code = res.getcode()
            except (BadStatusLine, HTTPError):
                print("Status error!")
                code = 500
            print("GET {}: {}".format(root_url, code))
            if code != 200:
                # Curl'ing page failed.
                errors.append({
                    'name': test['name'],
                    'stdout': '',
                    'stderr': "Status code {} retrieving {}".format(
                        code,
                        root_url
                    ),
                    'code': -1,
                })

    if errors:
        print("###############################################################")
        for error in errors:
            print("## {name} exited with status {code}:".format(**error))
            print("STDOUT:\n{stdout}".format(**error))
            print("STDERR:\n{stderr}".format(**error))
    print("{} projects passed, {} failed.".format(
        len(test_procs) - len(errors),
        len(errors)
    ))
    sys.exit(len(errors))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        tests = sys.argv[1:]
    else:
        tests = [
            'mbh-android',
            #'mbh-betarelease', # release files no longer on meteor's servers
            'mbh-dynometadata',
            'mbh-ironscaffold',
            'mbh-subdir',
            'mbh-vanilla',
            'mbh-old1.1.0.3',
            'mbh-old1.2.1',
            'mbh-1.4'
        ]
    run_tests(tests)

