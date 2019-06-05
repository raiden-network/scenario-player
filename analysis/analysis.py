import plotly.offline as py
import plotly.figure_factory as ff
import argparse
import sys
import re
import random
import json
from scipy import stats
import numpy as np
import csv
import os
import math
from datetime import datetime
from datetime import timedelta
from jinja2 import Environment, FileSystemLoader


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


def append_subtask(main_task_name, gantt_rows, csv_rows, subtasks):
    ids = set(map(lambda t: t[2]['id'], subtasks))
    tasks_length = len(subtasks)
    for id in ids:
        filtered_tasks = []
        for i in range(tasks_length):
            if 'id' not in subtasks[i][2]:
                continue
            if id == subtasks[i][2]['id']:
                filtered_tasks.append(subtasks[i])

        joined_content = '<br>------------------------------------<br>'.join(
            map(lambda t: json.dumps(t, sort_keys=True, indent=4).replace('\n', '<br>'), filtered_tasks))
        start = filtered_tasks[0][0]
        finish = filtered_tasks[-1][0]
        gantt_rows.append({'Task': 'Subtasks(#' + id + ')', 'Start': start,
                           'Finish': finish, 'Description': joined_content})
        csv_rows.append([main_task_name, 'Subtasks(#' + id + ')',
                         calculate_duration(start, finish)])


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
                if 'task' not in stripped_content[j][2]:
                    continue
                if stripped_content[i][2]['id'] == stripped_content[j][2]['id'] and (re.match('task successful', stripped_content[j][1], re.IGNORECASE) or re.match('task errored', stripped_content[j][1], re.IGNORECASE)):
                    task_indices.append([i, j])
                    break
    return task_indices


def read_raw_content(input_file):
    with open(input_file) as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    stripped_content = []
    for row in content:
        x = json.loads(row)
        stripped_content.append([x['timestamp'], x['event'], x])

    # sort by timestamp
    stripped_content.sort(key=lambda e: e[0])

    # remove startup and teardown events
    stripped_content = stripped_content[:index_of_first(
        stripped_content, lambda e: e[1] == 'Run finished')]
    stripped_content = stripped_content[index_of_first(
        stripped_content, lambda e: e[1] == 'Received token network address') + 1:]
    return stripped_content


def draw_gantt(gantt_output_file, gantt_rows, summary):
    fig = ff.create_gantt(gantt_rows, title='Raiden Analysis', show_colorbar=False,
                          bar_width=0.5, showgrid_x=True, showgrid_y=True, height=928, width=1680)

    fig['layout'].update(yaxis={
        # 'showticklabels':False
        'automargin': True
    }, hoverlabel={'align': 'left'})

    div = py.offline.plot(fig, output_type='div')

    j2_env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))),
                         trim_blocks=True)
    output_content = j2_env.get_template('chart_template.html').render(
        gantt_div=div,
        summary_header='Tasks matched "' + summary['name'] + '" (in ' + summary['unit'] + ')',
        count=summary['count'],
        min=summary['min'],
        max=summary['max'],
        mean=summary['mean'],
        median=summary['median'],
        stdev=summary['stdev']
    )

    with open(gantt_output_file, 'w') as text_file:
        text_file.write(output_content)


def write_csv(csv_output_file, csv_rows):
    with open(csv_output_file, 'w', newline='') as csv_file:
        csv_writer = csv.writer(
            csv_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(['MainTask', 'SubTask', 'Duration'])
        for r in csv_rows:
            csv_writer.writerow(r)


def generate_summary(csv_rows):
    result = {}
    # TODO: match too greedy
    duration_transfers = list(map(lambda r: r[2].total_seconds(), filter(
        lambda r: re.match('transfer', r[0], re.IGNORECASE) , csv_rows)))
    data = np.array(duration_transfers)
    description = stats.describe(data)
    result['name'] = 'Transfer'
    result['unit'] = 'Seconds'
    result['min'] = description.minmax[0]
    result['max'] = description.minmax[1]
    result['mean'] = description.mean
    result['median'] = stats.scoreatpercentile(data, 50)
    result['stdev'] = math.sqrt(description.variance)
    result['count'] = description.nobs
    return result


def write_summary(summary_output_file, summary):
    with open(summary_output_file, 'w', newline='') as summary_file:
        json.dump(summary, summary_file)


def fill_rows(gantt_rows, csv_rows, task_brackets, stripped_content):
    for task_bracket in task_brackets:
        task_start_item = stripped_content[task_bracket[0]]
        task_finish_item = stripped_content[task_bracket[1]]
        task_body = task_start_item[2]['task'].split(':', 1)
        task_id = task_start_item[2]['id']
        task_name = re.sub('<', '', task_body[0]).strip() + '(#' + task_id + ')'
        task_desc = re.sub('>', '', task_body[1]).strip()

        # add main task to rows
        gantt_rows.append({'Task': task_name, 'Start': task_start_item[0], 'Finish': task_finish_item[0], 'Description': json.dumps(
            json.loads(re.sub('\'', '"', task_desc)), sort_keys=True, indent=4).replace('\n', '<br>')})
        csv_rows.append([task_name, '', calculate_duration(
            task_start_item[0], task_finish_item[0])])

        # Only add subtasks for leafs of the tree
        main_task_debug_string = str(task_bracket) + ' ' + task_name + ': ' + task_desc
        if not has_more_specific_task_bracket(task_bracket, task_brackets):
            subtasks = list(filter(lambda t: t[2]['id'] == task_id, stripped_content))
            print(main_task_debug_string + ' - subtasks = ' + str(len(subtasks)))
            print('----------------------------------------------------------------')
            append_subtask(task_name, gantt_rows, csv_rows, subtasks)
        else:
            print(main_task_debug_string)
            print('----------------------------------------------------------------')


def parse_args():
    parser = argparse.ArgumentParser(description='Raiden Scenario-Player Analysis')
    parser.add_argument('input_file', type=str,
                        help='File name of scenario-player log file as main input')
    parser.add_argument('--output-csv-file', type=str, dest='csv_output_file',
                        default='raiden-scenario-player-analysis.csv', help='File name of the CSV output file')
    parser.add_argument('--output-gantt-file', type=str, dest='gantt_output_file',
                        default='raiden-scenario-player-analysis.html', help='File name of the Gantt Chart output file')
    parser.add_argument('--output-summary-file', type=str, dest='summary_output_file',
                        default='raiden-scenario-player-analysis.json', help='File name of the summary output file')
    return parser.parse_args()


def main():
    args = parse_args()

    stripped_content = read_raw_content(args.input_file)

    task_brackets = create_task_brackets(stripped_content)

    gantt_rows = []
    csv_rows = []

    fill_rows(gantt_rows, csv_rows, task_brackets, stripped_content)
    summary = generate_summary(csv_rows)

    draw_gantt(args.gantt_output_file, gantt_rows, summary)
    write_csv(args.csv_output_file, csv_rows)
    write_summary(args.summary_output_file, summary)


if __name__ == '__main__':
    main()
