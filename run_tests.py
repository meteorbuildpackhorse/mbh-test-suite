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
    for project in test_projects:
        project_base = os.path.join(BASE, "projects", project)
        # Create a commit so we can push.
        print("{}:".format(project))
        subprocess.check_call([
            "git", "commit", "--allow-empty", "-m", "Rebuild"
        ], cwd=project_base)
        # Push to heroku.
        proc = subprocess.Popen(
            ["git", "push", "--force", "heroku", "master"],
            cwd=project_base,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        test_procs.append({
            'name': project,
            'proc': proc,
            'basedir': project_base
        })

    errors = []
    for test in test_procs:
        # Wait for heroku build to finish.
        stdout, stderr = test['proc'].communicate()
        # Revert the commit.
        subprocess.check_call(["git", "reset", "--hard", "HEAD~1"], cwd=test['basedir'])
        # Check the result.
        if test['proc'].returncode != 0:
            errors.append({
                'name': test['name'],
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'code': test['proc'].returncode
            })
        else:
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
    run_tests([
        'mbh-android',
        'mbh-betarelease',
        'mbh-dynometadata',
        'mbh-ironscaffold',
        'mbh-subdir',
        'mbh-old1.1.0.3',
        'mbh-old1.2.1',
        'mbh-vanilla'
    ])

