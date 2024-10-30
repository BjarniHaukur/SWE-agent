#!/root/miniconda3/bin/python

# @yaml
# signature: run_dockerized_tests
# docstring: Runs all the tests in a dockerized environment, prints any failed tests to the console.
import os
import json
from pathlib import Path
import subprocess


# simply duplicated code, for simplicities sake
GITBUG_DIR = Path(__file__).parent / "../gitbug-java"
REPO_DIR = GITBUG_DIR / "repos"

def run_tests(bid:str, verbose:bool=False):
    subprocess.run(
        ["uv", "run", "gitbug_java.py", "run", REPO_DIR / bid, "-v" if verbose else ""],
        cwd=GITBUG_DIR
    )

def get_test_results(bid:str)->dict:
    return json.load(open(f"{REPO_DIR}/{bid}/.gitbug-java/test-results.json", "r"))

if __name__ == "__main__":
    # NOTE: This is slightly buggy (and really slow) and therefore ommitted from the main script
    # requires that SWE has already applied the patch to the code
    # here we should apply the most recent patch, call gitbug-java, then revert the patch
    BID = os.getenv("ROOT")
    run_tests(BID)
    results = get_test_results(BID)
    print("===============================")
    print("PRINTING TEST RESULTS NOW!!!!!") 
    print("===============================")
    print(results["failed_tests"])
    

    #This function is quite slow and should therefore only be called for final verification of results.

