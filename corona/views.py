from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime
import os, sys
import json
import folium
import pandas as pd
from datetime import datetime, timedelta
from matplotlib import pyplot as plt
from data.scatter_generator import ScatterGenerator
from data.map_generator import MapGenerator

global map_name
map_name = ['', '', 'map.html']
global new_unique_href
new_unique_href = 'asd'


class Holder:
    def __init__(self):
        self.switched = False
        self.midX = True
        self.midY = True
        self.regression = True
        self.countries = []
        self.first_render = True
        self.continent = 'World'

    def toggle_switch(self):
        self.switched = not self.switched

    def is_empty(self):
        return not self.midX and not self.midY and not self.regression

    def is_not_clear(self):
        return self.midX or self.midY or self.regression

    def check_data(self):
        dct = {}
        if self.midX:
            dct.update({'midX': 'checked'})
        if self.midY:
            dct.update({'midY': 'checked'})
        if self.regression:
            dct.update({'regression': 'checked'})
        return dct


vals = Holder()

date_format = "%Y-%m-%d"
first_day = '2019-12-31'


# todo each day for update: clear charts and maps; load new data
# todo map loading
def transform_date_to_digit(date):
    a = datetime.strptime(first_day, date_format)
    b = datetime.strptime(date, date_format)
    diff = b - a
    if diff.days < 0:
        return 0
    else:
        return diff.days


def transform_date_back(digit):
    td = timedelta(days=digit)
    # your calculated date
    return datetime.strftime(datetime.strptime(first_day, date_format) + td, date_format)


def get_day_dif(first, day):
    diff = datetime.strptime(day, date_format) - datetime.strptime(first, date_format)
    return diff


# m = MapGenerator()
# IMPORTANT! Map generator goes first cause it save important files

sg = ScatterGenerator()
sg.create_base_layer('total_cases', 'total_deaths', continent='World')


def index(request, cases='total_cases', continent='World'):
    # get map html
    continent_base = continent

    global map_name
    continent = ' '.join(continent.split('_'))
    map_name[0] = continent
    map_name[1] = cases
    sg.save_figure_plot(cases=cases)

    return render(request, 'index.html', {
        'map_num': 186,
        continent_base: 'active',
        cases: 'active'
    })


def changealtlines(alt_lines):
    if 'regression' in alt_lines:
        vals.regression = True
    else:
        vals.regression = False
    if 'midX' in alt_lines:
        vals.midX = True
    else:
        vals.midX = False
    if 'midY' in alt_lines:
        vals.midY = True
    else:
        vals.midY = False


def screen2(request, continent='World', case_a='total_cases', case_b=None):
    base_continent = continent
    continent = continent.replace('_', ' ')

    if 'axes' in request.POST.getlist('axes'):
        switch_axes = 'axes'
        # case_a, case_b = case_b, case_a
    else:
        switch_axes = None

    myDate = datetime.now()

    alt_lines = sorted(request.POST.getlist('line'))
    global new_unique_href
    new_unique_href = continent + '_' + '_'.join(alt_lines) + case_a + '_'
    print(vals.midX, vals.midY, vals.regression)
    if switch_axes == 'axes':
        vals.toggle_switch()
    elif alt_lines:
        changealtlines(alt_lines)

    # unique name to avoid creating the same files
    if case_b:
        new_unique_href += case_b
    else:
        new_unique_href += 'no_b'
    if case_b and len(case_b) > 4:
        if vals.switched:
            print('switch_axes')
            sg.create_base_layer(case_b, case_a, continent=continent)
        else:
            sg.create_base_layer(case_a, case_b, continent=continent)
        url = 'regression'
    else:
        url = 'regression'

    # Displays something like: Aug. 27, 2017, 2:57 p.m.
    formatedDate = myDate.strftime("%m-%d-%Y")
    country_list = sg.corona_df['iso_code'].unique().tolist()
    vals.continent = base_continent
    args = {'date': formatedDate,
            'url': url,
            case_a: 'active',
            base_continent: 'active',
            case_b: 'active',
            'country_list_part2': country_list[::2],
            'country_list_part1': country_list[1::2]
            }
    args.update(vals.check_data())
    print(vals.check_data())
    # Do something with the formatted date
    return render(request, 'screen2.html', args)



def show_map(request):
    global map_name
    all_maps = os.listdir('corona_full/templates/maps')
    cases = map_name[1]
    continent = map_name[0]
    outfile = '_'.join(map_name)

    if map_name not in all_maps:
        # optimize = True to load faster
        sg.generate_map(cases, optimize=True, continent=continent, outfile=outfile)
    return render(request, f'maps/{outfile}')


def regression_chart(request, name='regression', *args, **kwargs):

    # uncomment to makecheck if file exists to not to create it again
    # current_dir = os.listdir('corona_full/templates/charts')
    # if '%%%' not in new_unique_href and new_unique_href + '.html' in current_dir:
    #     print('File exists, skipping creating')
    #     return render(request, f'charts/{new_unique_href}.html')
    new_unique_href = 'block_this'
    try:
        sg.create_scatter(name=f'{new_unique_href}.html')
    except AttributeError:
        pass
    return render(request, f'charts/{new_unique_href}.html')
