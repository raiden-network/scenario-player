import plotly.offline as py
import plotly.figure_factory as ff
import sys
import re
import json
import csv
from datetime import datetime
from datetime import timedelta


def index_of_first(lst, pred):
    for i, v in enumerate(lst):
        if pred(v):
            return i
    return None


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
    stripped_content, lambda e: e[1] == 'Run finished')+1]
stripped_content = stripped_content[index_of_first(
    stripped_content, lambda e: e[1] == 'Received token network address')+1:]

df = []
for index, item in enumerate(stripped_content):
    start = item[0]
    if index == stripped_content.__len__() - 1:
        finish = start
    else:
        finish = stripped_content[index+1][0]
    if re.match('starting task', item[1], re.IGNORECASE) or re.match('task successful', item[1], re.IGNORECASE):
        continue

    start_datetime = datetime.strptime(start, '%Y-%m-%d %H:%M:%S.%f')
    finish_datetime = datetime.strptime(finish, '%Y-%m-%d %H:%M:%S.%f')
    delta = finish_datetime - start_datetime
    print(delta)
    df.append({"Task": item[1], "Start": start, "Finish": finish, "Description": json.dumps(
        item[2], sort_keys=True, indent=4).replace('\n', '<br>')})

fig = ff.create_gantt(df, title='Raiden Analysis', show_colorbar=False,
                      bar_width=0.5, showgrid_x=True, showgrid_y=True, height=928, width=1680)

fig['layout'].update(yaxis={
    # "showticklabels":False
    "automargin": True
})

py.offline.plot(fig, filename='raiden-gantt-analysis.html')

with open('raiden-gantt-analysis.csv', 'w', newline='') as csvfile:
    csv_writer = csv.writer(
        csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL, fieldnames=[])
    csv_writer.writeheader()
    csv_writer.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])
