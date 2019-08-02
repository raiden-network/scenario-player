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

    If any of these are not true, the PR will not be able to merged. **No exceptions!**

..admonition:: Merge vs Rebase

    The git history is a protocol of our development. As such, it is untouchable. Never rebase
    a PR onto `dev` or `master`. What you do on your own branches is your own business, though.



Features & Fixes
----------------

In order to submit a new feature or a fix for an existing one, the following
steps need to be taken:

1. Fork the project, if you have not already done so.
2. Create a new branch from **dev** (`git checkout dev && git checkout -b ${NEW_BRANCH_NAME}`).
3. Implement the feature or fix - be atomic in your commits and do not squash them!
4. Make sure your fix passes linter checks and the test harness (`make lint && test-harness`)
5. Push your commits (`git push -u origin ${NEW_BRANCH_NAME}`
6. Open a PR, requesting to merge into **`dev`** .
7. Wait for feedback or approval.

Then, for **Maintainers only**:

8.After approving a PR, merge it using the following REGEX pattern for the commit title:

    ^\[(?P<type>(FEAT|FIX))-(?P<issue>#\d+)\]\w?(?P<description>.*)$

Hotfixes
--------

Hotfixes are a special case in our workflow. They are the only temporary branches
starting from `master` and going back into it. They also need to be merged into
`dev`, in order to have that hotfix present in the next release (and avoid possible
conflicts whem merging `dev` into `master`).
The following listing outlines the workflow associated with hotfixes:

1. Fork the project, if you have not already done so.
2. Create a new branch from **master** (`git checkout dev && git checkout -b ${NEW_BRANCH_NAME}`).
3. Implement the feature or fix - be atomic in your commits and do not squash them!
4. Make sure your fix passes linter checks and the test harness (`make lint && make test-harness`)
5. Push your commits (`git push -u origin ${NEW_BRANCH_NAME}`
6. Open a PR, requesting to merge into **`master`** .
7. Wait for feedback or approval.

Then, for **Maintainers only**:

8. After approving a PR, merge it using the following REGEX pattern for the commit title:

    ^\[(?P<type>HOTFIX)-(?P<issue>#\d+)\]\w?(?P<description>.*)$

8. Open a new PR, requesting to merge into `dev`.
9. Resolve any conflicts that may arise.
10. Merge the PRs.

Releases
--------

Releases are cut from `dev` and merged into `master` at regular intervals.

1. Create a PR from `release` to `master`
2. Once all checks pass, request a review from a **maintainer**.

Then, for **Maintainers only**:

3. if all looks good: merge PR into `master` using the following REGEX for the commit message:

    ^\[(?P<type>RELEASE)]\w?(?P<description>.*)$

.. note::

    This workflow is only executed by administrators and developers with appropriate rights.
    However, we felt it was good practice to be transparent about this workflow
    nonetheless.

