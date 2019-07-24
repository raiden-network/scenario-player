##################################
Scenario-Player Contributing Guide
##################################

.. toctree::
    :local:

Workflows
=========

.. admonition:: Required Reading

    Please have a look at nvie's " Successful git branching model" for an in-depth
    explanation of the branching model we're using in this repository.

Features & Fixes
----------------

In order to submit a new feature or a fix for an existing one, the following
steps need to be taken:

1. Fork the project, if you have not already done so.
2. Create a new branch from **dev** (`git checkout dev && git checkout -b ${NEW_BRANCH_NAME}`).
3. Implement the feature or fix - be atomic in your commits and do not squash them!
4. Make sure your fix passes linter checks and the test harness (`make lint && tox`)
5. Push your commits (`git push -u origin ${NEW_BRANCH_NAME}`
6. Open a PR, requesting to merge into **`dev`** .
7. Wait for feedback or approval.

    7.1. **Maintainers only**: After approving a PR, merge it using the following REGEX pattern for the commit title:

            ^\[(?P<type>(FEAT|FIX))-(?P<issue>#\d+)\]\w?(?P<description>.*)$

Hotfixes
--------

Hotfixes are a special case in our workflow. They are the only temporary branches
starting from `master` and going back into it. They also need to be merged into
`dev`, in order to have that hotfix present in the next release (and avoid possible
conflicts whem merging `dev` into `master`). Our CI setup partially takes care of
merging the fix into `dev`, but a human is always required to sign off the PR created by it.
The following listing outlines the workflow associated with hotfixes:

1. Fork the project, if you have not already done so.
2. Create a new branch from **master** (`git checkout dev && git checkout -b ${NEW_BRANCH_NAME}`).
3. Implement the feature or fix - be atomic in your commits and do not squash them!
4. Make sure your fix passes linter checks and the test harness (`make lint && tox`)
5. Push your commits (`git push -u origin ${NEW_BRANCH_NAME}`
6. Open a PR, requesting to merge into **`master`** .
7. Wait for feedback or approval.

    7.1. **Maintainers only**: After approving a PR, merge it using the following REGEX pattern for the commit title:

        ^\[(?P<type>HOTFIX)-(?P<issue>#\d+)\]\w?(?P<description>.*)$

8. Two new PRs will be opened, containing the same commits, but requesting to merge into `dev` and `release` (if present).
9. Resolve any conflicts that may arise.
10. Request a review

        12.1 **Maintainers only**: After approval, merge using the regex from step 8.

Releases
--------

Releases are cut from `dev` and merged into `master` at regular intervals. In order
to allow polishing a release, a new branch is created (`release`), originating
from `dev`. This branch only takes (HOT)Fix commits, and will reject all others.
Once polishing is complete, the branch is merged back into `dev` as well as `master`.

1. `git checkout dev`
2. `git checkout -b release`
3. `git push -u origin release`
4. < Let development commence [...]>

Once polishing is complete and we're ready to merge/release:

1. Create a PR from `release` to `master`
2. Once all checks pass, request a review from a fellow maintainer.
3. Merge PR into `master` using the following REGEX for the commit message:

    ^\[(?P<type>RELEASE)]\w?(?P<description>.*)$

4. Open a new PR, requesting to merge `release` back into `dev`
5. Review the PR, and merge after approval using the REGEX from step 3.
6. Delete the `release` branch after the PR is merged.


.. note::

    This workflow is only executed by administrators and developers with appropriate rights.
    However, we felt it was good practice to be transparent about this workflow
    nonetheless.

