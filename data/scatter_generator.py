import json
import folium
import pandas as pd
import altair as alt
import geopandas as gpd
from matplotlib import pyplot as plt
from datetime import datetime, timedelta
from folium.plugins import TimeSliderChoropleth

date_format = "%Y-%m-%d"
first_day = '2019-12-31'


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


class ScatterGenerator:
    def __init__(self, file='https://covid.ourworldindata.org/data/owid-covid-data.json'):
        self.data, self.countries = self.read_data(file)
        self.geodata_shapes = 'corona_full/static/world-countries.json'
        self.geodata_file = 'corona_full/static/world-countries.json'
        self.data_file = 'corona_full/static/res.json'
        self.days_from_dc = self.get_days_from_december()

        self.corona_df_full = pd.DataFrame()
        self.corona_df = pd.DataFrame()
        self.transform_days_and_complete_gaps()

        self.res = ['total_cases', 'new_cases', 'total_tests', 'new_tests', 'total_cases_per_million',
                    'new_cases_per_million', 'total_deaths_per_million', 'new_deaths_per_million',
                    'total_tests_per_thousand', 'new_tests_per_thousand', 'population', 'population_density']
        self.colorscale = ["#c4c4c4", "#0d6f05", "#01d609", "#9eff00", "#ffe603",
                           "#fda804", "#fe6c03", "#ff0202"]

        self.create_df()

    # main data processing function
    def transform_days_and_complete_gaps(self):
        """
        We have a lot of gap days in covid data file
        Loop thorugh each of them and update our values to make
        all days from 2019-12-31 till now

        return: None
        """
        # blank data to fill later

        no_data = {'date': '2019-12-31', 'total_cases': 0.0, 'new_cases': 0.0, 'total_deaths': 0.0, 'new_deaths': 0.0,
                   'total_cases_per_million': 0.0, 'new_cases_per_million': 0.0, 'total_deaths_per_million': 0.0,
                   'new_deaths_per_million': 0.0, 'stringency_index': 0, 'new_tests_per_thousand': 0,
                   'total_tests_per_thousand': 0,
                   'new_tests': 0, 'total_tests': 0}

        for i in self.countries:
            data = self.data[i]['data']
            if len(data) >= self.days_from_dc:
                # date is completed
                self.data[i]['data'] = self.data[i]['data'][len(self.data[i]['data']) - self.days_from_dc:]
            date_list = [0] * self.days_from_dc
            for el in data:
                date = el['date']
                index = transform_date_to_digit(date)
                try:
                    date_list[index] = el
                except IndexError:
                    date_list[-1] = el
            # if no date from the first day - add it like no cases
            if date_list[0] == 0:
                date_list[0] = no_data.copy()

            # Оновити порожні значення на ті, що попередні
            for j in range(len(date_list) - 1):
                if date_list[j + 1] == 0:
                    # !important - make copy of prev data here
                    date_list[j + 1] = date_list[j].copy()
                    date_list[j + 1]['date'] = transform_date_back(j + 1)
            self.data[i]['data'] = date_list

        with open(self.data_file, 'w') as f:
            json.dump(self.data, f)

    def create_df(self):
        """
        Read data file in .json format
        and fill some gaps in data
        """
        df1 = pd.read_json(self.data_file).transpose()

        total_cases = df1['data'].fillna(0).tolist()
        all_iso = df1.index.tolist()
        population = df1['population'].tolist()

        df_cols = df1.columns.tolist()
        df_cols.remove('data')
        # new df --> these cols + date + total_cases +
        additional_cols = ['date', 'total_cases', 'new_cases', 'total_deaths', 'new_deaths',
                           'total_cases_per_million', 'new_cases_per_million', 'total_deaths_per_million',
                           'new_deaths_per_million', 'total_tests', 'new_tests', 'total_tests_per_thousand',
                           'new_tests_per_thousand', 'stringency_index']
        new_df_cols = ['iso_code'] + df_cols + additional_cols

        new_df_rows = []
        for i in range(len(total_cases)):  # for each country
            # i is index of current country in DF
            if all_iso[i] == 'OWID_WRL':
                continue
            if population[i] < 1000000:
                continue
            lst = [all_iso[i]]  # new row for new df
            for col in df_cols:
                lst.append(df1[col][all_iso[i]])
            for day in total_cases[i]:
                days_lst = lst.copy()
                for j in additional_cols:
                    try:
                        days_lst.append(day[j])
                    except KeyError:
                        days_lst.append(0)

                new_df_rows.append(days_lst)
        self.corona_df_full = pd.DataFrame(new_df_rows, columns=new_df_cols)

        date = self.corona_df_full['date']
        transformed_date = [transform_date_to_digit(i) for i in date]
        self.corona_df_full['date_transformed'] = transformed_date

        self.corona_df_full['tests_share'] = self.corona_df_full['total_cases'] / self.corona_df_full['total_tests']
        self.corona_df_full['tests_share_7d'] = self.corona_df_full['total_cases'] / self.corona_df_full['total_tests']
        self.corona_df_full['case_death'] = self.corona_df_full['total_cases'] / self.corona_df_full['total_deaths']
        self.corona_df_full['case_death_7d'] = self.corona_df_full['total_cases'] / self.corona_df_full['total_deaths']

        # allow working with big datasets
        alt.data_transformers.enable('default', max_rows=None)

    def get_last_7_d(self):
        """
        return: list
            with last week dates + today
        """
        last_day = self.get_range_max()
        last_7_d = [transform_date_back(last_day - i) for i in range(8)]
        print(last_7_d)
        return last_7_d

    def get_range_max(self):
        # get last day with data
        days = self.corona_df_full['date']
        range_max = transform_date_to_digit(max(days))
        return range_max

    def get_binding_range(self):
        range_max = self.get_range_max()

        if '7d' in self.case_a or '7d' in self.case_b:
            input_dropdown = alt.binding_range(min=range_max - 7, max=range_max, step=1, name='Date:')
        else:
            input_dropdown = alt.binding_range(min=0, max=range_max, step=1, name='Date:')

        selection = alt.selection_single(fields=['date_transformed'], bind=input_dropdown,
                                         init={'date_transformed': range_max})
        return selection

    def create_base_layer(self, case_a, case_b, continent='World'):
        """
        case_a: str
            X data range
        case_b: str
            Y data range
        continent: str
        """
        if continent in ['Europe', 'Asia', 'Africa', 'Oceania', 'North America',
                         "South America"]:
            self.corona_df = self.corona_df_full.loc[self.corona_df_full['continent'] == continent]

        else:
            self.corona_df = self.corona_df_full
        self.case_a = case_a
        self.case_b = case_b

        self.corona_df[case_a] = self.corona_df[case_a].abs()
        self.corona_df[case_b] = self.corona_df[case_b].abs()
        self.selection = self.get_binding_range()
        color = self.get_color(self.selection)
        case_a_col = self.corona_df[case_a].tolist()
        case_b_col = self.corona_df[case_b].tolist()

        country_len = len(case_b_col) // self.days_from_dc

        def get_median(case_col):
            medianX_data = []
            for i in range(self.days_from_dc):
                lst = []
                for j in range(country_len):
                    lst.append(case_col[j * self.days_from_dc + i])
                lst = sorted(lst)
                median = lst[(len(lst) - 1) // 2]
                medianX_data.append(median)
            medianX_data *= country_len
            return medianX_data

        medianX_data = get_median(case_a_col)
        medianY_data = get_median(case_b_col)

        self.corona_df['medianX'] = medianX_data
        self.corona_df['medianY'] = medianY_data

        all_iso = self.corona_df['iso_code'].tolist()
        self.corona_df['text_popup'] = all_iso

        self.chart = alt.Chart(self.corona_df).mark_point().encode(
            x=alt.Y(f'{case_a}:Q', title=case_a),
            y=alt.Y(f'{case_b}:Q', title=case_b),
            color=color,
            tooltip=[alt.Tooltip('location:N', title='Country')] + [
                alt.Tooltip(case_a, type='quantitative', title=case_a),
                alt.Tooltip(case_b, type='quantitative', title=case_b)],
        )

    def create_scatter(self, name='chart.html'):
        """
        :param name: str
            name of the output file
        """
        case_a = self.case_a
        case_b = self.case_b

        # add regression layer, True by default
        regression_layer = self.chart + self.chart.transform_regression(case_a, case_b).mark_line(color='black')
        # nearest will popup data of the nearest point
        nearest = alt.selection(type='single', nearest=True, on='mouseover',
                                fields=['x'], empty='none')

        text = alt.Chart(self.corona_df).mark_text(
            align='left',
            baseline='middle',
            color='black',
            dy=-9,
            dx=-7,
            fontSize=15,
        ).encode(
            text='text_popup',
            tooltip=[alt.Tooltip('location:N', title='Country')] + [
                alt.Tooltip(case_a, type='quantitative', title=case_a),
                alt.Tooltip(case_b, type='quantitative', title=case_b)],
            x=f'{case_a}:Q',
            y=f'{case_b}:Q'
        ).add_selection(nearest)
        text_layer = self.chart + text

        line = self.chart + alt.Chart(self.corona_df).mark_rule(color='red', strokeWidth=2).encode(
            y='medianY:Q') + alt.Chart(self.corona_df).mark_rule(color='red', strokeWidth=2).encode(
            x='medianX:Q')

        # add layers to the map
        layers = [line, regression_layer, text_layer]

        chart = alt.LayerChart(self.corona_df, layers)

        chart = chart.add_selection(self.selection
                                    ).transform_filter(self.selection
                                                       ).properties(width=490, height=395, padding=40
                                                                    # interactive to add interaction to the plot
                                                                    # Cant work on Android
                                                                    ).interactive()

        # save here
        dir = 'corona_full/templates/charts/'
        location = dir + name
        # renderer svg is a bit faster
        chart.save(location, embed_options={'renderer': 'svg'})

        # update created HTML page
        new_style = '''
       <script>
const msPerDay = 24 * 60 * 60 * 1000;
const date = new Date('December 31, 2019').getTime()

function toDateTime(x) {
// transform ms to date
	let new_date = new Date(x * msPerDay + date);
	return new_date.toLocaleDateString();

}

function Init () {
      // Launch in start - attach event to the only input
      var target = document.getElementsByTagName("input")[0];
			if (target.addEventListener) {
				target.addEventListener("input", updateTextInput, false);
			} else if (target.attachEvent) {
				target.attachEvent("oninout", updateTextInput);
			} else {
				target["oninput"] = updateTextInput;
			}
  }


function getTexts() {
    let g_el = document.getElementsByClassName('mark-text role-mark layer_2_layer_1_marks')[0]
    let iso_code = parent.document.getElementsByName('iso_code');
    let checked = []

    for (let i = 0; i<iso_code.length;i++) {
    if (iso_code[i].checked) {checked.push(iso_code[i].value)}
         }
    var texts = g_el.getElementsByTagName('text');
    return [texts, checked]
}

function clearIso() {
    a =  getTexts()
    let texts = a[0]
    let checked = a[1]
    for (let i=0; i<texts.length; i++) {
      if (checked.includes(texts[i].innerHTML)) {
        texts[i].style.display = 'block'
        }

        else {
            texts[i].style.display = 'none'
          }
        }
}

async function updateTextInput(val) {
      // Show date of showed data on page
      // base day is 31.12.2019
      var x = document.getElementsByClassName("vega-bind-name")[0]
		  val = document.getElementsByTagName("input")[0].value
		  val = toDateTime(val);
		  x.innerHTML = val;
      //console.log('UpdateTextInput', getTexts()[0][0], getTexts()[0][0].style)
      await sleep(1)

      clearIso()
}

window.onload = function() {
  // Hide iso codes text: needed by default
  clearIso()
  Init();
  // attach some buttons
  var divv = document.createElement("div");

  // next day
  a= createfn('+', plus)
  // auto scroll
  b = createfn('auto', changeAuto)
  // prev day
  c = createfn('-', minus)

  divv.appendChild(c);
  divv.appendChild(b);
  divv.appendChild(a);
  divv.classList.add('button-div');
  document.getElementsByTagName('body')[0].appendChild(divv);
    // let inputElement = document.getElementsByTagName("input")[0]
    // attach one more event to input, clearIso() on change
    // inputElement.addEventListener("input", clearIso, false);
    // inputElement.addEventListener("change", clearIso, false);

}
function plus(){
    let inputElement = document.getElementsByTagName("input")[0]
    inputElement.value++;
		inputElement.dispatchEvent(new Event('input'))
// await sleep(.01)
// clearIso();

}

function minus(){
	let inputElement = document.getElementsByTagName("input")[0]
	inputElement.value--;
	inputElement.dispatchEvent(new Event('input'))
}

function sleep(ms) {
  return new Promise(
    resolve => setTimeout(resolve, ms)
  );
}

run = false
async function changeAuto() {
  // change showed day
	run = !run
	var ele = document.getElementsByTagName('input')[0];
	if (ele.value === ele.max && run) {
		ele.value = 0;
	}
	do {
    plus();
    // wait half sec
		await sleep(499);
	}
	while (run);
}

function createfn(sign, operation){
    // create a button with a function on click
    var element = document.createElement("button");
    var para = document.createTextNode(sign);
    element.appendChild(para);
  	element.addEventListener("click", operation, false);
    return element
}

</script>

<style>
input {
width: 95%;
}

span {
display: none;
}

span[class] {
display: inline;
}
.vega-bind-name {
visibility: visible;
}

.vega-bind {
	text-align: center;
	paddin-left: 2%;
	padding-right: 3%;
}

.button-div {
  display: table;
  margin-right: auto;
  margin-left: auto;

 }
 '''  # NO ENDING STYLE TAG !!!
        with open(location, 'r', encoding='utf-8') as fr:
            data = fr.read()

        current_day = max(self.corona_df_full['date'])
        data = data.replace('<style>', new_style).replace('Date:', current_day)
        # write new styles and JS to the sasme document
        with open(location, 'w', encoding='utf-8') as fw:
            fw.write(data)

    def get_joined_df(self, total_cases, continent):
        """ Alt function to process data in df """
        if continent == 'Asia and Pacific':
            a = self.corona_df_full[self.corona_df_full['continent'] == 'Asia']
            b = self.corona_df_full[
                self.corona_df_full['continent'] == 'Oceania']
            corona_df = pd.concat([a, b])
        elif continent in ['Europe', 'Asia', 'Africa', 'Oceania', 'North America',
                           "South America"]:
            corona_df = self.corona_df_full.loc[self.corona_df_full['continent'] == continent]

        else:
            corona_df = self.corona_df_full
        # get shapes and borders of world countries
        countries = gpd.read_file('corona_full/static/99bfd9e7-bb42-4728-87b5-07f8c8ac631c2020328-1-1vef4ev.lu5nk.shp')

        corona_df = corona_df.replace({'location': 'US'},
                                      'United States')
        corona_df = corona_df.replace({'location': 'UK'},
                                      'United Kingdom')
        corona_df = corona_df.replace({'location': 'North Ireland'},
                                      'United Kingdom')
        countries = countries.replace({'CNTRY_NAME': 'Byelarus'},
                                      'Belarus')
        countries = countries.replace({'CNTRY_NAME': 'Macedonia'},
                                      'North Macedonia')

        # create 7d average data
        if '7d' in total_cases:
            days = self.get_last_7_d()
            corona_df = corona_df.loc[corona_df['date'].isin(days)]

        # rename some cols
        countries = countries.rename(columns={'CNTRY_NAME': 'location'})
        countries = countries.rename(columns={'CNTRY_NAME': 'location'})
        # drop with no cases
        corona_df = corona_df[corona_df[total_cases] != 0]
        sorted_df = corona_df.sort_values(['location', 'date']).reset_index(drop=True)
        sum_df = sorted_df.groupby(['location', 'date'], as_index=False).sum()
        joined_df = sum_df.merge(countries, on='location')

        return joined_df

    def process_joined_df(self, total_cases, continent):
        joined_df = self.get_joined_df(total_cases, continent=continent)
        joined_df[total_cases] = joined_df[total_cases].abs()

        median_data = {}
        all_dates = joined_df['date'].unique().tolist()

        for date in all_dates:
            df_trash = joined_df[joined_df['date'] == date]
            _ = df_trash[total_cases].tolist()
            median_for_day = sum(_) / len(_)
            median_data[date] = median_for_day

        dates = joined_df['date'].tolist()
        medians = [''] * len(dates)

        for i in range(len(dates)):
            medians[i] = median_data[dates[i]]
        joined_df['median'] = medians
        joined_df['median'] = joined_df[total_cases] / joined_df['median']
        # avoid cases with 5+x scale
        joined_df['median'].values[joined_df['median'].values > 5] = 5

        joined_df['date_sec'] = pd.to_datetime(joined_df['date']).astype('int64') / 10 ** 9
        joined_df['date_sec'] = joined_df['date_sec'].astype(int).astype(str)
        br = '<br>'
        joined_df['header'] = joined_df['location'] + '         ' + joined_df['date'] + br

        style_dict = self.gen_style_dict(joined_df)

        countries_df = self.generate_map_tooltip(joined_df)
        return countries_df, style_dict

    def gen_style_dict(self, joined_df):
        country_list = joined_df['location'].unique().tolist()
        country_idx = range(len(country_list))

        style_dict = {}
        for i in country_idx:
            country = country_list[i]
            result = joined_df[joined_df['location'] == country]
            inner_dict = {}
            for _, r in result.iterrows():
                inner_dict[r['date_sec']] = {'color': self.my_color_function(r['median']), 'opacity': 0.8}
            style_dict[str(i)] = inner_dict
        return style_dict

    def generate_map(self, total_cases, continent="World", optimize=True, outfile='map.html'):
        """
        :param total_cases: str
        :param continent: str
        :param optimize: bool: True
            False to make map with all tooltips
            WARNING! can cause MemoryError!
        :param outfile: str
            name of the outer file
        """
        if continent not in ['Europe', 'Asia and Pacific', 'Africa', 'North America',
                             "South America"]:
            continent = 'World'

        # continent and center of the continent with zoom
        continent_locations = {'World': [45, 45, 1], 'Europe': [50, 5, 3], 'North America': [48, -102, 3],
                               'South America': [-26, -60, 3], 'Africa': [9, 35, 3], 'Asia and Pacific': [0, 100, 2.5]}
        countries_df, style_dict = self.process_joined_df(total_cases, continent=continent)

        continent_data = continent_locations[continent]
        # drop cols for faster processing
        countries_gdf = gpd.GeoDataFrame(countries_df[['geometry']])
        countries_gdf = countries_gdf.drop_duplicates().reset_index()

        slider_map = folium.Map(min_zoom=2, zoom_start=continent_data[2], location=continent_data[0:2],
                                max_bounds=True, tiles='cartodbpositron')
        TimeSliderChoropleth(
            data=countries_gdf.to_json(),
            styledict=style_dict,
        ).add_to(slider_map)

        # again drop cols but leave header and tooltip
        countries_gdf = gpd.GeoDataFrame(countries_df[['geometry', 'header', 'tooltip']])

        # if optimized - leave only last day data
        if optimize:
            countries_gdf = countries_gdf.drop_duplicates(subset=['geometry'], keep="last")

        # add tooltip layer to map
        folium.GeoJson(
            data=countries_gdf.to_json(),
            style_function=lambda x: {
                'color': 'black',
                'weight': 1
            },
            tooltip=folium.features.GeoJsonTooltip(
                fields=['header', 'tooltip'],
                aliases=['', '']
            ),
        ).add_to(slider_map)

        location = f'corona_full/templates/maps/{outfile}'
        slider_map.save(outfile=location)

        # set current time slider val to max
        query = '"value", 0'

        timestamplast = 'var current_timestamp = timestamps[timestamps.length - 1];'
        current_timestamp = 'var current_timestamp = timestamps[0];'
        with open(location, 'r') as fr:
            data = fr.read().replace(query, '"value", timestamps.length - 1')
            data = data.replace(current_timestamp, timestamplast)
        with open(location, 'w') as fw:
            fw.write(data)

    def save_figure_plot(self, cases, continent='World'):
        """
        A function to save a plot of current continent data:
        date and cases

        :param cases: str
            Y data
        :param continent: str

        generates a plot with "data_plot.png" name
        """

        if continent == 'World':
            base_df = self.corona_df_full
        else:
            try:
                base_df = self.corona_df_full[self.corona_df_full['continent'] == continent]
            except KeyError:
                base_df = self.corona_df_full
        dates = base_df['date'].unique().tolist()

        x, y = dates, []
        for i in range(len(dates)):
            new_df = base_df[base_df['date'] == dates[i]]
            y.append(sum(new_df[cases].tolist()))
        x = [transform_date_to_digit(i) for i in x]

        # clear figure before plotting
        plt.clf()
        fig, ax = plt.subplots()

        right_side = ax.spines["right"]
        top_side = ax.spines["top"]
        right_side.set_visible(False)
        top_side.set_visible(False)

        plt.plot(x, y)
        plt.savefig('corona_full/static/data_plot.png')

    @staticmethod
    def generate_map_tooltip(joined_df):
        fields = ['geometry', 'header', 'total_cases', 'new_cases', 'total_tests', 'new_tests',
                  'total_cases_per_million',
                  'new_cases_per_million', 'total_deaths_per_million', 'new_deaths_per_million',
                  'total_tests_per_thousand', 'new_tests_per_thousand', 'population', 'population_density']
        countries_df = joined_df[fields]

        def b(a):
            # wrap text in bold tag
            return '<b>' + a + '</b>'

        # create a tooltip from a couuple of other columns
        countries_df['tooltip'] = b('Total confirmed cases: ') + joined_df[fields[2]].astype('str') + '<br>' + b(
            'New confirmed cases: ') + joined_df[fields[3]].astype('str') + '<br>' + b('Total tests: ') + \
                                  joined_df[fields[4]].astype('str') + '<br>' + b('New tests: ') + joined_df[
                                      fields[5]].astype(
            'str') + '<br><br>' + b('Total confirmed cases per 1M:') + joined_df[fields[6]].astype('str') + '<br>' + b(
            'New confirmed cases per 1M: ') + joined_df[fields[7]].astype('str') + '<br>' + b('Total deaths per 1M: ') + \
                                  joined_df[fields[8]].astype('str') + '<br>' + b('New deaths per 1M: ') + joined_df[
                                      fields[9]].astype('str') + '<br>' + b('Total tests per 1M: ') + \
                                  joined_df[fields[10]].astype('str') + '<br>' + b("New tests per 1M: ") + joined_df[
                                      fields[11]].astype(
            'str') + '<br><br>' + b('Population: ') + joined_df[fields[12]].astype('str') + '<br>' + b(
            "Populatiion density: ") + joined_df[fields[13]].astype('str')
        return countries_df

    @staticmethod
    def read_data(file):
        """
        import synchro data from server
        file: str
            url of the .json covid data
        return: [list, list]  data itself and all keys - countries
        """
        import requests
        r = requests.get(file, allow_redirects=True)
        data = r.content
        data = json.loads(data)
        countries = list(data.keys())
        return data, countries

    @staticmethod
    def get_days_from_december():
        """
        Count number of days passed from 2019-12-31
        return: int
        """
        days_from_december = datetime.now() - datetime.strptime(first_day, date_format)
        return days_from_december.days

    @staticmethod
    def my_color_function(x):
        """ Maps values to proper colors considering relativeness """

        colorscale = ["#c4c4c4", "#0d6f05", "#01d609", "#9eff00", "#ffe603",
                      "#fda804", "#fe6c03", "#960000", "#ff0202"]

        relative_population = x
        if relative_population <= 0.25:
            return colorscale[1]
        elif relative_population <= .5:
            return colorscale[2]
        elif relative_population <= 1:
            return colorscale[3]
        elif relative_population <= 2:
            return colorscale[4]
        elif relative_population <= 3:
            return colorscale[5]
        elif relative_population <= 5:
            return colorscale[6]
        else:
            return colorscale[7]

    @staticmethod
    def get_color(selection):
        color = alt.condition(selection,
                              alt.Color('continent:N', legend=None),
                              alt.value('blue'))
        return color


if __name__ == '__main__':
    sg = ScatterGenerator()
    # sg.generate_map('tests_share_7d', continent='World')
    sg.create_base_layer(case_a='total_cases', case_b='tests_share_7d')
    sg.create_scatter(name='regression.html')