#!/root/miniconda3/bin/python

# @yaml
# signature: run_dockerized_tests
# docstring: Runs all the tests in a dockerized environment, prints any failed tests to the console.
import os
from pathlib import Path

os.chdir(Path(__file__).parent.parent.parent)
from gitbug import run_tests, get_test_results


if __name__ == "__main__":
    BID = os.getenv("BID")
    run_tests(BID)
    results = get_test_results(BID)
    print("===============================")
    print("PRINTING TEST RESULTS NOW!!!!!") 
    print("===============================")
    print(results["failed_tests"])
    

    #This function is quite slow and should therefore only be called for final verification of results.

