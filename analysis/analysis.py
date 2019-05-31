import plotly.offline as py
import plotly.figure_factory as ff
import sys
import re
import random
import json
import csv
from datetime import datetime
from datetime import timedelta


def index_of_first(lst, pred):
    for i, v in enumerate(lst):
        if pred(v):
            return i
    return None


def has_more_specific_task_bracket(task_bracket, task_indices):
    for other in task_indices:
        if other == task_bracket:
            continue
        if other[0] in range(task_bracket[0], task_bracket[1]):
            # theoretically other[1] == end should also be checked for inclusiveness
            # however we expect to have a tree here where this should not happen
            return True
    return False


def append_subtask(gantt_rows, csv_rows, subtasks):
    if len(subtasks) == 2:
        gantt_rows.append({"Task": subtasks[0][1] + "/" + subtasks[1][1], "Start": subtasks[0][0], "Finish": subtasks[1][0], "Description": json.dumps(
            subtasks[0][2], sort_keys=True, indent=4).replace('\n', '<br>') + "<br>------------------------------------<br>" + json.dumps(subtasks[1][2], sort_keys=True, indent=4).replace('\n', '<br>')})
        csv_rows.append(['', subtasks[0][1] + "/" + subtasks[1][1],
                         calculate_duration(subtasks[0][0], subtasks[1][0])])
        return
    for index, item in enumerate(subtasks):
        start = item[0]
        if index == subtasks.__len__() - 1:
            finish = start
        else:
            finish = subtasks[index + 1][0]
        if re.match('starting task', item[1], re.IGNORECASE) or re.match('task successful', item[1], re.IGNORECASE):
            continue
        gantt_rows.append({"Task": item[1], "Start": start, "Finish": finish, "Description": json.dumps(
            item[2], sort_keys=True, indent=4).replace('\n', '<br>')})
        csv_rows.append(['', item[1], calculate_duration(start, finish)])


def calculate_duration(start, finish):
    start_datetime = datetime.strptime(start, '%Y-%m-%d %H:%M:%S.%f')
    finish_datetime = datetime.strptime(finish, '%Y-%m-%d %H:%M:%S.%f')
    return finish_datetime - start_datetime


def create_task_brackets(stripped_content):
    content_length = len(stripped_content)
    task_indices = []
    for i in range(content_length):
        if re.match('starting task', stripped_content[i][1], re.IGNORECASE):
            for j in range(i, content_length):
                if "task" not in stripped_content[j][2]:
                    continue
                if stripped_content[i][2]["task"] == stripped_content[j][2]["task"] and (re.match('task successful', stripped_content[j][1], re.IGNORECASE) or re.match('task errored', stripped_content[j][1], re.IGNORECASE)):
                    task_indices.append([i, j])
                    break
    return task_indices


def read_raw_content():
    with open(sys.argv[1]) as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    stripped_content = []
    for row in content:
        x = json.loads(row)
        stripped_content.append([x["timestamp"], x["event"], x])

    # sort by timestamp
    stripped_content.sort(key=lambda e: e[0])

    # remove startup and teardown events
    stripped_content = stripped_content[:index_of_first(
        stripped_content, lambda e: e[1] == 'Run finished') + 1]
    stripped_content = stripped_content[index_of_first(
        stripped_content, lambda e: e[1] == 'Received token network address') + 1:]
    return stripped_content


def draw_gantt(gantt_rows):
    fig = ff.create_gantt(gantt_rows, title='Raiden Analysis', show_colorbar=False,
                          bar_width=0.5, showgrid_x=True, showgrid_y=True, height=928, width=1680)

    fig['layout'].update(yaxis={
        # "showticklabels":False
        "automargin": True
    }, hoverlabel={'align': 'left'})

    py.offline.plot(fig, filename='raiden-gantt-analysis.html')


def write_csv(csv_rows):
    with open('raiden-gantt-analysis.csv', 'w', newline='') as csv_file:
        csv_writer = csv.writer(
            csv_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(['Task', 'Sub-Task', 'Duration'])
        for r in csv_rows:
            csv_writer.writerow(r)


def fill_rows(gantt_rows, csv_rows, task_brackets, stripped_content):
    for task_bracket_index, task_bracket in enumerate(task_brackets):
        task_start_item = stripped_content[task_bracket[0]]
        task_finish_item = stripped_content[task_bracket[1]]
        task_body = task_start_item[2]["task"].split(":", 1)
        task_name = re.sub('<', '', task_body[0]).strip()
        task_desc = re.sub('>', '', task_body[1]).strip()

        # add main task to rows
        gantt_rows.append({"Task": task_name, "Start": task_start_item[0], "Finish": task_finish_item[0], "Description": json.dumps(
            json.loads(re.sub('\'', '"', task_desc)), sort_keys=True, indent=4).replace('\n', '<br>')})
        csv_rows.append([task_name, '', calculate_duration(
            task_start_item[0], task_finish_item[0])])

        # Only add subtasks for leafs of the tree
        main_task_debug_string = str(task_bracket) + ": " + task_name + " - (" + task_desc + ")"
        if not has_more_specific_task_bracket(task_bracket, task_brackets):
            subtasks = stripped_content[task_bracket[0] + 1:task_bracket[1]]
            print(main_task_debug_string + " - subtasks = " + str(len(subtasks)))
            print("----------------------------------------------------------------")
            append_subtask(gantt_rows, csv_rows, subtasks)
        else:
            print(main_task_debug_string)
            print("----------------------------------------------------------------")


def main():
    stripped_content = read_raw_content()

    task_brackets = create_task_brackets(stripped_content)

    gantt_rows = []
    csv_rows = []

    fill_rows(gantt_rows, csv_rows, task_brackets, stripped_content)

    draw_gantt(gantt_rows)
    write_csv(csv_rows)


if __name__ == "__main__":
    main()
