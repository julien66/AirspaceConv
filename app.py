import re
from flask import Flask, render_template, render_template_string, request, Response
import pandas as pd
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.debug = True
Bootstrap(app)

@app.route('/export', methods=['POST'])
def export():
    if request.method == 'POST':
        zones_string = request.form['airspace']
        zones = eval(zones_string)

        output_from_parsed_template = render_template('airspace_file.html', zones=zones)
        with open("airspace.txt", "w") as f:
            f.write(output_from_parsed_template)

        return Response(output_from_parsed_template, mimetype="txt/plain")

@app.route('/convert', methods=['POST'])
def convert():
    if request.method == 'POST':
        zones_string = request.form['airspace']
        pressure = int(request.form['pressure'])
        if pressure == 1013:
            pressure = 1013.25

        unit = request.form['unit']
        zones = eval(zones_string)
        for zone in zones:
            zone = convert(zone, pressure, unit)

        data_frame = pd.DataFrame(zones)
        data_frame = data_frame[['name', 'class', 'ceiling', 'new_ceiling', 'floor', 'new_floor', 'coords']]

        return render_template('index.html',
                               data=zones,
                               toPrint=True,
                               table=data_frame.to_html(
                                   classes=["table", "table-bordered", "table-striped", "table-hover"],
                                   index=False
                               ))

def convert(zone, pressure, unit):
    try :
        zone['new_ceiling'] = change_altitude(zone['ceiling'], pressure, unit)
        zone['new_floor'] = change_altitude(zone['floor'], pressure, unit)
    except KeyError:
        zone
    return zone;

def change_altitude (limit, pressure, unit):
    feet_to_meter = 0.3048
    std = 1013.25
    feet = re.split('feet|ft', limit, 1)
    fl = re.split('FL', limit, 1)
    pure_number = re.split('([0-9]*)', limit, 1)
    if len(feet) > 1:
        rest = feet[1]
        bound = round((int(feet[0])) * feet_to_meter)
    elif len(fl) > 1:
        rest = 'AMSL'
        bound = round((int(fl[1])*100) * feet_to_meter)
    elif len(pure_number) > 1:
        bound = round(int(pure_number[1]) * feet_to_meter)
        rest = pure_number[2]
    else:
        return limit

    if bound:
        bound = round(bound * pressure / std)

    if bound == 0:
        bound = 1

    if unit == "fake":
        return str(bound) + 'ft ' + rest.lstrip()
    elif unit == "meter":
        return str(bound) + 'm ' + rest.lstrip()
    elif unit == "feet":
        return str(round(bound*(1/feet_to_meter))) + 'ft ' + rest.lstrip()

@app.route('/airspace', methods=['POST'])
def get_airspace_file():
    if request.method == 'POST':
        file = request.files['airspace']
        if file:
            zones = parseOpenair(file)
            data_frame = pd.DataFrame(zones)
            data_frame = data_frame[['name', 'class', 'ceiling', 'floor', 'coords']]
        return render_template('index.html',
                               data=zones,
                               table=data_frame.to_html(
                                   classes=["table", "table-bordered", "table-striped", "table-hover"],
                                   index=False
                               ))

def parseOpenair(file) :
    zones = []
    file_data = file.read().decode('utf-8')
    raw_zones = split_on_empty_lines(file_data)
    for zone in raw_zones:
        zone_data = zone.splitlines()
        zone = build_airspace_object(zone_data)
        if zone :
            zones.append(zone)
    return zones

def split_on_empty_lines(s):
    # greedily match 2 or more new-lines
    blank_line_regex = r"(?:\r?\n){2,}"
    return re.split(blank_line_regex, s.strip())

def build_airspace_object(zone_data) :
    zone = {'coords': []}
    comment_regex = r"^#|^\*"
    for line in zone_data:
        if len(re.split(comment_regex, line)) > 1:
            continue
        elif len(re.split("^AC", line, 1)) > 1:
            zone['class'] = re.split("^AC", line, 1)[1]
        elif len(re.split("^AN", line, 1)) > 1:
            zone['name'] = re.split("^AN", line, 1)[1]
        elif len(re.split("^AH", line, 1)) > 1:
            zone['ceiling'] = re.split("^AH", line, 1)[1]
        elif len(re.split("^AL", line, 1)) > 1:
            zone['floor'] = re.split("^AL", line, 1)[1]
        else:
            zone['coords'].append(line)
    return zone

@app.route('/')
def launch_app():
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
