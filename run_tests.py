#!/usr/bin/env python3
import argparse
from http.client import BadStatusLine
import os
import subprocess
import sys
import timeit
from urllib.error import HTTPError
from urllib.request import urlopen

BASE = os.path.dirname(__file__)
PROJECTS = [
    'mbh-android',
    #'mbh-betarelease', # release files no longer on meteor's servers
    'mbh-dynometadata',
    'mbh-ironscaffold',
    'mbh-subdir',
    'mbh-vanilla',
    'mbh-old1.1.0.3',
    'mbh-old1.2.1',
    'mbh-old1.3.5',
    'mbh-1.4'
]

parser = argparse.ArgumentParser()
parser.add_argument("--buildpack",
    default="https://github.com/AdmitHub/meteor-buildpack-horse.git#devel")
parser.add_argument("project", nargs='?', default=PROJECTS)
parser.add_argument("--verbose", action='store_true', default=False)
parser.add_argument("--clear-cache", action='store_true', default=False)

def run_tests(args):
    test_procs = []
    errors = []
    for project in args.project:
        start = timeit.default_timer()
        project_base = os.path.join(BASE, "projects", project)
        # Create a commit so we can push.
        print("################################")
        print("{}: {}".format(project, project_base))

        # Set up buildpack
        buildpacks = subprocess.check_output(["heroku", "buildpacks"], cwd=project_base)
        cur_buildpack = buildpacks.strip().split()[-1].decode('utf-8')
        if args.buildpack != cur_buildpack:
            subprocess.check_call(["heroku", "buildpacks:set", args.buildpack],
                    cwd=project_base)
        if args.verbose:
            subprocess.check_call(["heroku", "config:set", "BUILDPACK_VERBOSE=1"],
                cwd=project_base)
        else:
            subprocess.check_call(["heroku", "config:unset", "BUILDPACK_VERBOSE"],
                    cwd=project_base)
        if args.clear_cache:
            subprocess.check_call(["heroku", "config:set", "BUILDPACK_CLEAR_CACHE=1"],
                    cwd=project_base)
        else:
            subprocess.check_call(["heroku", "config:unset", "BUILDPACK_CLEAR_CACHE"],
                    cwd=project_base)

        # Checkout latest project code
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
        stop = timeit.default_timer()
        elapsed = stop - start
        # Check the result.
        if test['proc'].returncode != 0:
            errors.append({
                'name': test['name'],
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'code': test['proc'].returncode,
            })
            print(errors[-1]['stderr'])
            print("BUILD TIME: ", elapsed, "seconds")
        else:
            print(stdout.decode('utf-8'))
            print(stderr.decode('utf-8'))
            print("BUILD TIME: ", elapsed, "seconds")
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
    sys.exit(1 if len(errors) else 0)

if __name__ == "__main__":
    args = parser.parse_args()
    run_tests(args)

