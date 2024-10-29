import json
import logging
import subprocess
from pathlib import Path


logging.basicConfig(level=logging.INFO)

BID = None

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
    subprocess.run(
        ["uv", "run", "gitbug_java.py", "run", REPO_DIR / bid, "-v" if verbose else ""],
        cwd=GITBUG_DIR
    )

def get_test_results(bid:str)->dict:
    return json.load(open(f"{REPO_DIR}/{bid}/.gitbug-java/test-results.json", "r"))


def run_sweagent(bid:str):
    global BID
    BID = bid

    subprocess.run([
        "uv", "run", "run.py",
        "--bid", bid,
        "--model_name", "chatgpt-4o-latest",  # normally I prefer 3.5-sonnet but Anthropic won't take my money for some reason
        "--data_path", str(ISSUES_DIR / f"{bid}.md"),
        "--repo_path", str(REPO_DIR / bid),
        "--config_file", str(Path(__file__).parent / "config/gitbug.yaml"),  # applies our slight changes to the default config, such as running tests via gitbug-java
        "--apply_patch_locally",
        "--noinstall_environment",  # since we are not using python
    ])

def initialize_issue(bid:str):
    failed_tests = get_test_results(bid)["failed_tests"]
    assert len(failed_tests) != 0, "No failed tests found, cannot initialize issue"
    
    msg = """We're currently addressing a problem with the codebase.

Some tests are failing, and your task is to diagnose and resolve the underlying cause. Begin by examining the list of failing tests, identify what's causing the failures, and make the necessary code fixes. Once you've made your changes, **submit** them using the 'submit' command. You can then confirm that the issue is resolved by running 'run_dockerized_tests' (note: the tests run in a separate, dockerized environment).

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

    parser = argparse.ArgumentParser(description='Run tests and generate issue files for gitbug-java bugs')
    parser.add_argument('bid', help='The bug ID to process')
    args = parser.parse_args()
    
    run_tests(args.bid, verbose=True)  # to get which tests are failing
    initialize_issue(args.bid)
    initialize_repo(args.bid)
    run_sweagent(args.bid)
    # checkout_repo(args.bid)