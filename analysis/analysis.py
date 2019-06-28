import argparse
import csv
import fileinput
import json
import math
import os
import random
import re
import sys
from datetime import datetime, timedelta

import numpy as np
import plotly.figure_factory as ff
import plotly.offline as py
from jinja2 import Environment, FileSystemLoader
from scipy import stats


def has_more_specific_task_bracket(task_bracket, task_indices):
    for other in task_indices:
        if other == task_bracket:
            continue
        if other[0] in range(task_bracket[0], task_bracket[1]):
            # theoretically other[1] == end should also be checked for inclusiveness
            # however we expect to have a tree here where this should not happen
            return True
    return False


def append_subtask(main_task_name, table_rows, csv_rows, subtasks):
    ids = set(map(lambda t: t[2]["id"], subtasks))
    for id in ids:
        filtered_tasks = []
        for idx, subtask in enumerate(subtasks):
            if "id" not in subtask[2]:
                continue
            if id == subtask[2]["id"]:
                filtered_tasks.append(subtask)

        joined_content = "<br>------------------------------------<br>".join(
            map(
                lambda t: json.dumps(t, sort_keys=True, indent=4).replace("\n", "<br>"),
                filtered_tasks,
            )
        )
        start = filtered_tasks[0][0]
        finish = filtered_tasks[-1][0]
        table_rows.append(
            {
                "id": id,
                "name": "Subtasks(#" + id + ")",
                "duration": calculate_duration(start, finish),
                "description": joined_content,
            }
        )
        csv_rows.append(
            [main_task_name, "Subtasks(#" + id + ")", calculate_duration(start, finish), ""]
        )


def calculate_duration(start, finish):
    start_datetime = datetime.strptime(start, "%Y-%m-%d %H:%M:%S.%f")
    finish_datetime = datetime.strptime(finish, "%Y-%m-%d %H:%M:%S.%f")
    return finish_datetime - start_datetime


def create_task_brackets(stripped_content):
    task_indices = []
    for i, start_content in enumerate(stripped_content):
        start_event = start_content[1]
        start_id = start_content[2]["id"]
        if re.match("starting task", start_event, re.IGNORECASE):
            for j, following_content in enumerate(stripped_content[i:], start=i):
                following_event = following_content[1]
                following_id = following_content[2]["id"]
                if "task" not in following_content[2]:
                    continue
                ids_identical = start_id == following_id
                event_matches_successful = re.match(
                    "task successful", following_event, re.IGNORECASE
                )
                event_matches_errored = re.match("task errored", following_event, re.IGNORECASE)
                if ids_identical and (event_matches_successful or event_matches_errored):
                    task_indices.append([i, j])
                    break
    return task_indices


def read_raw_content(input_file):
    content = []
    if not input_file:
        content = [line.strip() for line in fileinput.input(input_file)]
    else:
        with open(input_file[0]) as f:
            content = [line.strip() for line in f.readlines()]

    stripped_content = []
    for row in content:
        x = json.loads(row)
        if "id" in x:
            stripped_content.append([x["timestamp"], x["event"], x])

    # sort by timestamp
    stripped_content.sort(key=lambda e: e[0])

    return stripped_content


def draw_gantt(gantt_output_file, gantt_rows, table_rows, summary):
    fig = ff.create_gantt(
        gantt_rows,
        title="Raiden Analysis",
        show_colorbar=False,
        bar_width=0.5,
        showgrid_x=True,
        showgrid_y=True,
        height=928,
        width=1680,
    )

    fig["layout"].update(
        yaxis={
            # 'showticklabels':False
            "automargin": True
        },
        hoverlabel={"align": "left"},
    )

    div = py.offline.plot(fig, output_type="div")

    j2_env = Environment(
        loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))), trim_blocks=True
    )
    output_content = j2_env.get_template("chart_template.html").render(
        gantt_div=div,
        summary_header='Tasks matched "' + summary["name"] + '" (in ' + summary["unit"] + ")",
        count=summary["count"],
        min=summary["min"],
        max=summary["max"],
        mean=summary["mean"],
        median=summary["median"],
        stdev=summary["stdev"],
        task_table=table_rows,
    )

    with open(gantt_output_file, "w") as text_file:
        text_file.write(output_content)


def write_csv(csv_output_file, csv_rows):
    with open(csv_output_file, "w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(["MainTask", "SubTask", "Duration", "Hops"])
        for r in csv_rows:
            csv_writer.writerow(r)


def generate_summary(csv_rows):
    result = {}
    # TODO: match too greedy
    duration_transfers = list(
        map(
            lambda r: r[2].total_seconds(),
            filter(lambda r: re.match("transfer", r[0], re.IGNORECASE), csv_rows),
        )
    )
    data = np.array(duration_transfers)
    description = stats.describe(data)
    result["name"] = "Transfer"
    result["unit"] = "Seconds"
    result["min"] = description.minmax[0]
    result["max"] = description.minmax[1]
    result["mean"] = description.mean
    result["median"] = stats.scoreatpercentile(data, 50)
    result["stdev"] = math.sqrt(description.variance)
    result["count"] = description.nobs
    return result


def write_summary(summary_output_file, summary):
    with open(summary_output_file, "w", newline="") as summary_file:
        json.dump(summary, summary_file)


def fill_rows(gantt_rows, csv_rows, table_rows, task_brackets, stripped_content):
    for task_bracket in task_brackets:
        task_start_item = stripped_content[task_bracket[0]]
        task_finish_item = stripped_content[task_bracket[1]]
        task_body = task_start_item[2]["task"].split(":", 1)
        task_id = task_start_item[2]["id"]
        task_name = task_body[0].replace("<", "").strip() + "(#" + task_id + ")"
        task_desc = task_body[1].replace(">", "").strip()
        task_body_json = json.loads(task_desc.replace("'", '"'))

        # add main task to rows
        task_full_desc = json.dumps(task_body_json, sort_keys=True, indent=4).replace("\n", "<br>")
        gantt_rows.append(
            {
                "Task": task_name,
                "Start": task_start_item[0],
                "Finish": task_finish_item[0],
                "Description": task_full_desc,
            }
        )
        hops = ""
        if task_name.startswith("Transfer"):
            transfer_from = task_body_json["from"]
            transfer_to = task_body_json["to"]
            hops = str(abs(transfer_from - transfer_to))
        table_rows.append(
            {
                "id": task_id,
                "name": task_name,
                "duration": calculate_duration(task_start_item[0], task_finish_item[0]),
                "description": task_full_desc,
                "hops": hops,
            }
        )
        csv_rows.append(
            [task_name, "", calculate_duration(task_start_item[0], task_finish_item[0]), hops]
        )

        # Only add subtasks for leafs of the tree
        main_task_debug_string = "{0} {1}: {2}".format(str(task_bracket), task_name, task_desc)
        if not has_more_specific_task_bracket(task_bracket, task_brackets):
            subtasks = list(filter(lambda t: t[2]["id"] == task_id, stripped_content))
            print("{0} - subtasks = {1}".format(main_task_debug_string, str(len(subtasks))))
            print("----------------------------------------------------------------")
            append_subtask(task_name, table_rows, csv_rows, subtasks)
        else:
            print(main_task_debug_string)
            print("----------------------------------------------------------------")


def parse_args():
    parser = argparse.ArgumentParser(description="Raiden Scenario-Player Analysis")
    parser.add_argument(
        "input_file",
        nargs="*",
        help="File name of scenario-player log file as main input, if empty, stdin is used",
    )
    parser.add_argument(
        "--output-csv-file",
        type=str,
        dest="csv_output_file",
        default="raiden-scenario-player-analysis.csv",
        help="File name of the CSV output file",
    )
    parser.add_argument(
        "--output-gantt-file",
        type=str,
        dest="gantt_output_file",
        default="raiden-scenario-player-analysis.html",
        help="File name of the Gantt Chart output file",
    )
    parser.add_argument(
        "--output-summary-file",
        type=str,
        dest="summary_output_file",
        default="raiden-scenario-player-analysis.json",
        help="File name of the summary output file",
    )

    args = parser.parse_args()

    return args


def main():
    args = parse_args()

    stripped_content = read_raw_content(args.input_file)

    task_brackets = create_task_brackets(stripped_content)

    gantt_rows = []
    csv_rows = []
    table_rows = []

    fill_rows(gantt_rows, csv_rows, table_rows, task_brackets, stripped_content)
    summary = generate_summary(csv_rows)

    draw_gantt(args.gantt_output_file, gantt_rows, table_rows, summary)
    write_csv(args.csv_output_file, csv_rows)
    write_summary(args.summary_output_file, summary)


if __name__ == "__main__":
    main()
