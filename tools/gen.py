#!/usr/bin/env python3
import os
import glob
import re
from sys import argv
from datetime import date
from datetime import timedelta
from dataclasses import dataclass
from typing import TypeVar
from jinja2 import Environment, FileSystemLoader, select_autoescape

config = dict(
    path = '.',
    weburl = 'https://www.cutebotcalendar.com',
    pages = dict(
        index = 'index.html',
        archive = 'archive.html',
        rss = 'rss.xml'
    ),
    images = 'asset/cc',
    templates = 'templates',
    alt_text = 'alt_text.txt',
    output = 'cc'
)

Comic = TypeVar('Comic')

@dataclass
class Comic:
    file_path: str
    image_path: str
    page_path: str
    date: date
    alt: str
    has_alt: bool = False
    month_header: str = None
    next: Comic = None
    prev: Comic = None

#Comic = namedtuple('Comic', ['file_path', 'image_path', 'date', 'alt'])
date_re = re.compile(r'.*?(\d+)[-_]+(\d+)[-_]+(\d+)')

def make_date(str):
    m = date_re.match(str)
    if m is None: return None
    groups = m.groups()
    try:
        return date(int(groups[0]), int(groups[1]), int(groups[2]))
    except:
        return None

def clear_output():
    path = os.path.join(config['path'], config['output'])
    if os.path.exists(path):
        for f in os.listdir(path):
            os.remove(os.path.join(path, f))
    else:
        os.mkdir(path)

def get_comic_data(cutoff_date):
    data = []
    path = os.path.join(config['path'], config['images'])
    images = glob.glob(os.path.join(path, '*.png'))
    for i in images:
        file_name = os.path.basename(i)
        comic_date = make_date(file_name)
        if comic_date is None: 
            print("Failed to convert " + i)
            continue
        if cutoff_date is not None and comic_date > cutoff_date:
            continue;
        if any(i for i in data if i.date == comic_date):
            print("Found duplicate " + i)
            continue

        def_alt = "Comic for " + comic_date.strftime('%B %d, %Y')
        page = '/' + config['output'] + '/' + comic_date.strftime("%Y-%m-%d") + '.html'
        data.append(Comic(
            i,
            '/' + config['images'] + '/' + file_name,
            page,
            comic_date,
            def_alt))
    data.sort(reverse = True, key = lambda i: i.date)
    return data

def process_alt_data(comic_data, cutoff_date):
    path = os.path.join(config['path'], config['alt_text'])
    with open(path, encoding='utf-8') as file:
        lines = [line.rstrip() for line in file]
    for l in lines:
        if l == '' or l.startswith('#'): continue
        alt_date = make_date(l);
        if alt_date == None:
            print("Failed to parse alt line " + l)
            continue
        c = [i for i in comic_data if i.date == alt_date]
        if len(c) == 0:
            if cutoff_date is None or alt_date <= cutoff_date:
                print("Found alt text but no comic for '" + l + "'")
            continue
        c[0].has_alt = True
        c[0].alt = l[l.index(' '):].lstrip()
    with open(path, encoding='utf-8', mode="a") as file:
        for c in comic_data:
            if c.has_alt: continue
            file.write(c.date.strftime("%Y-%m-%d") + " " + c.alt + "\n")

def find_next_prev(data):
    for i in range(0, len(data)):
        if i != 0:
            data[i].next = data[i-1]
        if i != len(data) - 1:
            data[i].prev = data[i+1]
        if i == 0:
            data[i].month_header = data[i].date.strftime("%B %Y")
        else:
            d1 = data[i-1].date.replace(day=1)
            d2 = data[i].date.replace(day=1)
            if d1 != d2:
                data[i].month_header = data[i].date.strftime("%B %Y")

cutoff_date = None
if len(argv) > 1:
    print("Cutoff date " + argv[1])
    cutoff_date = date.fromisoformat(argv[1])

clear_output()
comic_data = get_comic_data(cutoff_date)
process_alt_data(comic_data, cutoff_date)
find_next_prev(comic_data)

env = Environment(
    loader=FileSystemLoader(os.path.join(config['path'], config['templates'])),
    autoescape=select_autoescape()
)

comic_template = env.get_template("template_comic.html")
for c in comic_data:
    html = comic_template.render(comic = c)
    path = os.path.join(config['path'], c.page_path[1:])
    with open(path, encoding='utf-8', mode='w') as file:
        file.write(html)

path = os.path.join(config['path'], config['pages']['rss'])
with open(path, encoding='utf-8', mode='w') as file:
    html = env.get_template("template_rss.xml")\
        .render(comics=comic_data[:30], config=config)
    file.write(html)

path = os.path.join(config['path'], config['pages']['archive'])
with open(path, encoding='utf-8', mode='w') as file:
    html = env.get_template("template_archive.html").render(comics=comic_data)
    file.write(html)

path = os.path.join(config['path'], config['pages']['index'])
with open(path, encoding='utf-8', mode='w') as file:
    html = env.get_template("template_index.html").render(comic = comic_data[0])
    file.write(html)