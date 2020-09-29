##################################
Scenario-Player Contributing Guide
##################################

.. toctree::
    :local:

Workflows
=========

..admonition:: The Golden Rule

    For each and every single PR, all of the following must hold true in order to be merged:

        * Linter/Style checks are passing (`make lint`)
        * Tests are passing (`make test-harness`)
        * Test coverage does not decrease
        * PR passes the smoketests stage on CI

    If any of these are not true, the PR will not be merged. **No exceptions!**

..admonition:: Merge vs Rebase

    The git history is a protocol of our development. As such, it is untouchable.
    Never `git push --force` to `master`. Commits on PRs are fair game to squashing, and
    keeping a clean commit history is encouraged. However, do **not** squash all your commits
    into a single one before merging. Let commits be atomic changes.



Features & Fixes
----------------

In order to submit a new feature or a fix for an existing one, the following
steps need to be taken:

1. Fork the project, if you have not already done so.
2. Create a new branch from **master** (`git checkout -b ${NEW_BRANCH_NAME}`).
3. Implement the feature or fix - be atomic in your commits and do not squash them!
4. Make sure your fix passes linter checks and the test harness (`make lint && test-harness`)
5. Push your commits (`git push -u origin ${NEW_BRANCH_NAME}`
6. Open a PR, requesting to merge into **`master`** .
7. Wait for feedback or approval.
