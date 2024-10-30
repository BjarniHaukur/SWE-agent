import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)


GITBUG_DIR = Path(__file__).parent / "../gitbug-java"
REPO_DIR = GITBUG_DIR / "repos"
REPO_DIR.mkdir(exist_ok=True)
ISSUES_DIR = GITBUG_DIR / "issues"
ISSUES_DIR.mkdir(exist_ok=True)


def get_all_bids()->list[str]:
    return subprocess.run(
        ["uv", "run", "gitbug_java.py", "bids"],
        capture_output=True,
        text=True,
        cwd=GITBUG_DIR
    ).stdout.splitlines()  # make sure they are always in the same order

def checkout_repo(bid:str):
    repo_dir = REPO_DIR / bid
    repo_dir.mkdir(exist_ok=True)
    subprocess.run(
        ["uv", "run", "gitbug_java.py", "checkout", bid, repo_dir],
        cwd=GITBUG_DIR
    )

def run_tests(bid:str, verbose:bool=False):
    """Runs the tests and logs the failed tests to a JSON file."""
    subprocess.run(
        ["uv", "run", "gitbug_java.py", "run", REPO_DIR / bid, "-v" if verbose else ""],
        cwd=GITBUG_DIR
    )

    test_results = get_test_results(bid)
    failed_tests = {"timestamp": datetime.now().isoformat(), "failed_tests": test_results.get('failed_tests', [])}

    # Open the JSON file and append the results
    log_file = 'failed_tests.json'
    data = json.load(open(log_file, 'r')) if Path(log_file).exists() else {}

    # append the failed tests under the bid
    data[bid] = data.get(bid, []) + [failed_tests]

    # Write back to the JSON file
    json.dump(data, open(log_file, 'w'), indent=4)

def get_test_results(bid:str)->dict:
    return json.load(open(f"{REPO_DIR}/{bid}/.gitbug-java/test-results.json", "r"))

def run_sweagent(bid:str):
    subprocess.run([
        "uv", "run", "run.py",
        "--model_name", "chatgpt-4o-latest",  # normally I prefer 3.5-sonnet but Anthropic won't take my money for some reason
        "--data_path", str(ISSUES_DIR / f"{bid}.md"),  # 
        "--repo_path", str(REPO_DIR / bid),
        "--config_file", str(Path(__file__).parent / "config/gitbug.yaml"),  # applies our slight changes to the default config, such as running tests via gitbug-java
        "--apply_patch_locally",  # run git apply on the generated patch
        "--noinstall_environment",  # since we are not using python
    ])

def initialize_issue(bid:str):
    failed_tests = get_test_results(bid)["failed_tests"]
    assert len(failed_tests) != 0, "No failed tests found, cannot initialize issue"
    
    # doesnt currently work since the agent operates in a separate VM
    # Once you've made your changes, **submit** them using the 'submit' command. You can then confirm that the issue is resolved by running 'run_dockerized_tests'.
    
    msg = """We're currently addressing a problem with the codebase.
Some tests are failing, and your task is to diagnose and resolve the underlying cause. Begin by examining the list of failing tests, identify what's causing the failures, and make the necessary code fixes.

Failed tests:
"""
    for test in failed_tests:
        msg += f" - {test['name']} in {test['classname']}\n"
    
    with open(ISSUES_DIR / f"{bid}.md", "w") as f:
        f.write(msg)

def initialize_repo(bid:str):
    """SWE requires that the git repo is clean before the agent starts working.
    In gitbug-java, the most recent change is unstaged, so we stage and commit it.
    """
    subprocess.run(["git", "add", "-u"], cwd=REPO_DIR / bid)  # not . since we dont want gitbug-java metadata to confuse the agent
    subprocess.run(["git", "commit", "-m", "clean for SWE-agent"], cwd=REPO_DIR / bid)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run SWE-agent on gitbug-java bugs')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print verbose output')
    args = parser.parse_args()

    bids = get_all_bids()

    if len(list(REPO_DIR.glob("*"))) == 0:  # if no repos are checked out, checkout all
        for bid in bids: checkout_repo(bid)

    bids = bids[:10]  # arbitrary limit for $/token and time reasons

    # normally I would multiprocess something like this, but I've had gitbug-java throw some errors when run in parallel
    for bid in bids:
        logging.info(f"Running Initial Tests for {bid}")
        run_tests(bid, verbose=args.verbose)  # to get which tests are failing

        initialize_issue(bid)  # create a file detailing which tests are failing
        initialize_repo(bid)  # make sure the repo is clean

        logging.info(f"Running SWE-agent for {bid}")
        run_sweagent(bid)  # let the agent do its thing

        # the agent has access to the run_tests function throught the 'run_dockerized_tests' command
        # but it is executed on a VM, so the log file is not updated with the failed tests
        # so we run the tests manually here
        logging.info(f"Running Final Tests for {bid}")
        run_tests(bid, verbose=args.verbose)


