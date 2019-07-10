Scenario Player Analysis
========================
This is an analysis tool to show performance metrics using the logs of a scenario player run.

Prerequisites
^^^^^^^^^^^^^
- Python 3.7

We strongly recommend using a virtual python env like `pyenv <https://github.com/pyenv/pyenv>`_
(in addition to that you can use `virtualenvwrapper <https://github.com/virajkanwade/venvwrapper>`_)

Installation
^^^^^^^^^^^^

.. code-block:: bash

    pyenv shell 3.7.0
    mkvenv raiden-analysis
    pip install -r requirements.txt

How To Use
^^^^^^^^^^
Either start the analysis directly or print out the help:

.. code-block:: bash

    python analysis.py $PATH_TO_SCENARIO_LOG_FILE

    python analysis.py -h


See an example result below.

Examples
^^^^^^^^
Two different scenarios are currently available as examples and each have three generated files:

- A gantt plot is rendered in an HTML file - it contains a legend and a summary
- A CSV file is created which contains the duration of the tasks
- A HTML file with a statistic summary and histogram on the basis of each task type is getting calculated

Simple-Scenario
"""""""""""""""

- Gantt: `<example/simple-scenario/gantt-overview.html>`_
- CSV: `<example/simple-scenario/durations.csv>`_
- Statistics: `<example/simple-scenario/statistics.html>`_

Mediated-Transfers-Scenario
"""""""""""""""""""""""""""

- Gantt: `<example/mediated-transfers-scenario/gantt-overview.html>`_
- CSV: `<example/mediated-transfers-scenario/durations.csv>`_
- Statistics: `<example/mediated-transfers-scenario/statistics.html>`_


Limitations/Caveats
^^^^^^^^^^^^^^^^^^^
- the duration of a task is done by looking at the next event in the list of events (sorted by time)
- parallel task processing might not be visualized correctly
- the number of ticks on the y-axis can be too much when too many tasks have been emitted in the log. In that case uncomment the ``showticklabels`` line within the ``draw_gantt()`` method.
- log messages are grouped by task-id, resulting in request/response calls being grouped
