#!/usr/bin/env python3
import os
import subprocess

BASE = os.path.dirname(__file)
test_projects = [
    'mbh-android',
    'mbh-betarelease',
    'mbh-dynometadata',
    'mbh-ironscaffold',
    'mbh-subdir',
    'mbh-old1.1.0.3',
    'mbh-old1.2.1',
    'mbh-vanilla'
]

def run_tests(test_projects):
    test_procs = []
    for project in test_projects:
        project_base = os.path.join(BASE, "projects", project)
        # Make sure buildpack is set correctly.
        subprocess.check_call([
            "heroku",
            "buildpacks:set",
            "https://github.com/AdmitHub/meteor-buildpack-horse.git#devel"
        ], cwd=project_base)
        # Create a commit so we can push.
        subprocess.check_call([
            "git", "commit", "--allow-empty", "-m", "Rebuild"
        ], cwd=project_base)
        # Push to heroku.
        proc = subprocess.Popen(["git", "push", "heroku", "master"],
            cwd=project_base, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        text_procs.append((project, proc))

    errors = []
    for name, proc in test_procs:
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            errors.append({
                'name': name,
                'stdout': stdout,
                'stderr': stderr,
                'code': proc.returncode
            })

    if errors:
        for error in errors:
            print("## {name} exited with status {code}:".format(error))
            print("STDOUT:\n{stdout}".format(error))
            print("STDERR:\n{stdout}".format(error))
    print("{} projects passed, {} failed.".format(
        len(test_procs) - len(errors),
        len(errors)
    ))
    sys.exit(len(errors) > 0)

if __name__ == "__main__":
    run_tests()
