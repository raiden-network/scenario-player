Scenario Player Analysis
========================
This is an analysis tool to show performance metrics of a scenario using the logs of a scenario run.

Installation
""""""""""""

.. code-block:: bash

    pip install -r requirements.txt

How To Use
""""""""""

.. code-block:: bash

    python analysis.py $PATH_TO_LOG_FILE_OF_SCENARIO

Result
""""""
After execution the plot is rendered in a HTML file called ``raiden-gantt-analysis.html``.

Besides that a CSV file is created which contains the raw deltas between the tasks: ``raiden-gantt-analysis.csv``.

Limitations
"""""""""""
- The duration of a task is done by looking at the next event in the list of events (sorted by time)
- parallel task processing might not be visualized not correctly
- The number of ticks on the y-axis can be to much when too many tasks have been emitted in the log, in that case uncomment the ``showticklabels`` line in the ``draw_gantt()`` method.