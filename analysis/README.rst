Scenario Player Analysis
========================
This is an analysis tool to show performance metrics of a scenario using the logs of a scenario run.

Prerequisites
"""""""""""""
- `pyenv <https://github.com/pyenv/pyenv>`_
- `virtualenvwrapper <https://github.com/virajkanwade/venvwrapper>`_

You may also use other python virtual environments

Installation
""""""""""""

.. code-block:: bash

    pyenv shell 3.7.0
    mkvenv raiden-analysis
    pip install -r requirements.txt

How To Use
""""""""""
Either start the analysis directly or print out the help:

.. code-block:: bash

    python analysis.py $PATH_TO_SCENARIO_LOG_FILE

    python analysis.py -h

Result
""""""
There are currently two output files generated:

- a gantt plot is rendered in a HTML file called (default: ``raiden-gantt-analysis.html``)
- a CSV file is created which contains the duration of the tasks: (default: ``raiden-gantt-analysis.csv``)
- a JSON file is with the statistic summary calculated on base of transfers (default: ``raiden-scenario-player-analysis.json``)

Limitations/Caveats
"""""""""""""""""""
- the duration of a task is done by looking at the next event in the list of events (sorted by time)
- parallel task processing might not be visualized not correctly
- the number of ticks on the y-axis can be to much when too many tasks have been emitted in the log, in that case uncomment the ``showticklabels`` line in the ``draw_gantt()`` method.
- log messages are grouped by task-id, resulting in request/response calls are grouped