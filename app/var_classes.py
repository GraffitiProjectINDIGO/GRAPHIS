# Copyright (C) 2023 Martin Wieser
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from collections import namedtuple
import configparser
import numpy
from pathlib import Path


from PySide2.QtGui import QColor, QBrush, QStandardItem


CONFIG_FILE = "graffilabel.config"

COLOR_CIRCLE_START = '#fdae61'
COLOR_RECTANGLE_START = '#4dac26'
COLOR_POLYGON_START = '#2c7bb6'

CONTRIBUTOR_TAG = 'XMP-iptcExt:Contributor'

TAG_DESCRIBER = "XMP-dc:Description"
TAG_TRANSCRIBER = "XMP-dc:Title"

REGION_ROLE = 'main subject area'

REGION_CREATOR_ROLE = 'https://indigo.openatlas.eu/regioncreator'
DESCRIBER_ROLE = 'https://indigo.openatlas.eu/describer'
TRANSCRIBER_ROLE = 'https://indigo.openatlas.eu/transcriber'

RCTYPE_Standard_IDENTIFIER = 'link to indigo graffito definition'
RCTYPE_Standard_NAME = 'graffito'


image_region_role = [["cropping", "http://cv.iptc.org/newscodes/imageregionrole/cropping"],
                     ["recommended cropping", "http://cv.iptc.org/newscodes/imageregionrole/recomCropping"],
                     ["landscape format cropping", "http://cv.iptc.org/newscodes/imageregionrole/landscapeCropping"],
                     ["portrait format cropping", "http://cv.iptc.org/newscodes/imageregionrole/portraitCropping"],
                     ["square format cropping", "http://cv.iptc.org/newscodes/imageregionrole/squareCropping"],
                     ["composite image item", "http://cv.iptc.org/newscodes/imageregionrole/compositeImageItem"],
                     ["copyright region", "http://cv.iptc.org/newscodes/imageregionrole/copyrightRegion"],
                     ["subject area", "http://cv.iptc.org/newscodes/imageregionrole/subjectArea"],
                     ["main subject area", "http://cv.iptc.org/newscodes/imageregionrole/mainSubjectArea"],
                     ["area of interest", "http://cv.iptc.org/newscodes/imageregionrole/areaOfInterest"],
                     ["business use", "http://cv.iptc.org/newscodes/imageregionrole/businessUse"]]


class GeometryConfigs:
    def __init__(self):
        self.region_name_prefix = ''
        self.region_role_name = ''
        self.rctype_identifier = ''
        self.rctype_name = ''
        self.region_creator_role = ''
        self.describer_role = ''
        self.transcriber_role = ''
        self.color_start = ''

    def set_values(self, config_parser: configparser.ConfigParser, geom_type: str) -> bool:

        success = True

        if geom_type == 'POLYGON':
            color_start = COLOR_POLYGON_START
        elif geom_type == 'RECTANGLE':
            color_start = COLOR_RECTANGLE_START
        elif geom_type == 'CIRCLE':
            color_start = COLOR_CIRCLE_START
        else:
            color_start = COLOR_CIRCLE_START
            success = False

        if not config_parser.has_section(geom_type):
            success = False
            config_parser.add_section(geom_type)

        section = config_parser[geom_type]
        self.region_role_name = section.get('REGION_ROLE_NAME', REGION_ROLE)
        if not get_image_region_role(self.region_role_name):
            self.region_role_name = REGION_ROLE
            success = False

        self.region_name_prefix = section.get('REGION_NAME_PREFIX', '')
        self.rctype_identifier = section.get('RCTYPE_IDENTIFIER', RCTYPE_Standard_IDENTIFIER)
        self.rctype_name = section.get('RCTYPE_NAME', RCTYPE_Standard_NAME)
        self.region_creator_role = section.get('REGION_CREATOR_ROLE', REGION_CREATOR_ROLE)
        self.describer_role = section.get('DESCRIBER_ROLE', DESCRIBER_ROLE)
        self.transcriber_role = section.get('TRANSCRIBER_ROLE', TRANSCRIBER_ROLE)
        self.color_start = section.get('COLOUR_START', color_start)

        return success


class Instructions:
    No_Instruction = 'no'
    Polygon_Instruction = 'Polygon'
    Circle_Instruction = 'Point'
    Rectangle_Instruction = 'Rectangle'
    Move_Instruction = 'Move'
    Change_Instruction = 'Change'


preview = namedtuple("preview", "id path title image polygon_number rectangle_number circle_number")


class PreviewModelData:
    def __init__(self, id_image, path, title, image, polygon_number, rectangle_number, circle_number):
        self.id = id_image
        self.path = path
        self.title = title
        self.image = image
        self.polygon_number = polygon_number
        self.rectangle_number = rectangle_number
        self.circle_number = circle_number


PREVIEW_HEIGHT = 500
NUMBER_OF_COLUMNS = 4
CELL_PADDING = 20  # all sides
THUMBNAIL_MARGIN = 3
THUMBNAIL_FOOTER_PADDING = 3
TEXT_MARGIN = 3

zoomin_factor = 0.8
point_size = 100

color_dark_red = QBrush(QColor(103, 40, 23))
color_dark_green = QBrush(QColor(0, 113, 77))
color_mid_yellow = QColor(102, 102, 0)

color_on_image_hoover = QColor(0, 255, 0, 50)


def put_text_to_dict_or_remove(dict_attribute, tag, text: str):
    if text == '':
        if dict_attribute.get(tag, ''):
            dict_attribute.pop(tag)
    else:
        dict_attribute[tag] = text

    return dict_attribute


def put_struct_to_dict_or_remove(dict_attribute, tag, indentifier: str, name: str):
    if indentifier or name:
        dict_attribute[tag] = [{'Identifier': [indentifier],
                                'Name': name}]

    else:
        if dict_attribute.get(tag, ''):
            dict_attribute.pop(tag)

    return dict_attribute


def find_key_role(dict_attribute, dict_value, role):
    if dict_attribute.get(dict_value, ''):
        for idx, item in enumerate(dict_attribute[dict_value]):
            if item.get('Role', ''):
                if item['Role'][0] == role:
                    return True, idx

    return False, 0


def put_struc_tag_name_list(dict_attribute, tag, role, indentifier, name):
    success, idx = find_key_role(dict_attribute, tag, role)
    if success:

        if indentifier or name:

            dict_attribute[tag][idx] = {'Identifier': [indentifier],
                                        'Name': [name],
                                        'Role': [role]}
        else:
            dict_attribute[tag].pop(idx)
    else:
        if indentifier or name:
            if dict_attribute.get(tag, ''):
                dict_attribute[tag].append({'Identifier': [indentifier],
                                            'Name': [name],
                                            'Role': [role]})
            else:
                dict_attribute[tag] = [{'Identifier': [indentifier],
                                        'Name': [name],
                                        'Role': [role]}]

    return dict_attribute


def put_struc_tag(dict_attribute, tag, role, indentifier, name):
    success, idx = find_key_role(dict_attribute, tag, role)
    if success:

        if indentifier or name:

            dict_attribute[tag][idx] = {'Identifier': [indentifier],
                                        'Name': name,
                                        'Role': [role]}
        else:
            dict_attribute[tag].pop(idx)
    else:
        if indentifier or name:
            if dict_attribute.get(tag, ''):
                dict_attribute[tag].append({'Identifier': [indentifier],
                                            'Name': name,
                                            'Role': [role]})
            else:
                dict_attribute[tag] = [{'Identifier': [indentifier],
                                        'Name': name,
                                        'Role': [role]}]

    return dict_attribute


def append_struc_tag_namelist(dict_attribute, tag, role, indentifier, name):
    success, idx = find_key_role(dict_attribute, tag, role)
    if success:
        if indentifier or name:

            if (indentifier != dict_attribute[tag][idx]['Identifier'][-1]) \
                    or (name != dict_attribute[tag][idx]['Name'][-1]):
                dict_attribute[tag][idx]['Identifier'].append(indentifier)
                dict_attribute[tag][idx]['Name'].append(name)

    else:
        if indentifier or name:
            if dict_attribute.get(tag, ''):
                dict_attribute[tag].append({'Identifier': [indentifier],
                                            'Name': [name],
                                            'Role': [role]})
            else:
                dict_attribute[tag] = [{'Identifier': [indentifier],
                                        'Name': [name],
                                        'Role': [role]}]

    return dict_attribute


def get_image_region_role(name: str):
    new_id = ''
    for x in image_region_role:
        if x[0] == name:
            new_id = x[1]

    return new_id


def load_config():
    config = configparser.ConfigParser()

    success = True
    if Path(CONFIG_FILE).exists():
        config.read(CONFIG_FILE)
    else:
        success = False

    config_default = {'TAG_DESCRIBER': TAG_DESCRIBER, 'TAG_TRANSCRIBER': TAG_TRANSCRIBER,
                      'CONTRIBUTOR_TAG': CONTRIBUTOR_TAG}
    if config.has_section('TAGS'):
        if config.has_option('TAGS', 'TAG_DESCRIBER'):
            config_default['TAG_DESCRIBER'] = config['TAGS']['TAG_DESCRIBER']
        else:
            success = False
        if config.has_option('TAGS', 'TAG_TRANSCRIBER'):
            config_default['TAG_TRANSCRIBER'] = config['TAGS']['TAG_TRANSCRIBER']
        else:
            success = False

        if config.has_option('TAGS', 'CONTRIBUTOR_TAG'):
            config_default['CONTRIBUTOR_TAG'] = config['TAGS']['CONTRIBUTOR_TAG']
        else:
            success = False
    else:
        success = False

    config_polygon = GeometryConfigs()
    success = success and config_polygon.set_values(config, 'POLYGON')
    config_rectangle = GeometryConfigs()
    success = success and config_rectangle.set_values(config, 'RECTANGLE')
    config_circle = GeometryConfigs()
    success = success and config_circle.set_values(config, 'CIRCLE')

    return success, config_default, config_polygon, config_rectangle, config_circle


def list_of_points_to_list(poly):
    p_list = []
    for p in poly:
        p_list.append([p.x(), p.y()])

    return p_list


def fill_model_from_json(parent, d):
    if isinstance(d, dict):
        for key, value in d.items():
            it = QStandardItem(str(key))
            if isinstance(value, dict):
                parent.appendRow(it)
                fill_model_from_json(it, value)
            else:
                it2 = QStandardItem(str(value))
                parent.appendRow([it, it2])


def create_region_boundary(img_width, img_height, object_type, list_coordinates):
    # data = json.loads(obj['data'])
    # coords = data['coords']
    # Geometry
    bound = {'RbUnit': 'relative'}
    mx = img_width
    my = img_height

    if object_type == 'polygon':
        # RegionBoundary={RbShape=Polygon,RbUnit=Relative,RbVertices=[{RbX=0.0,RbY=0.0},{RbX=0.22,RbY=0.0},
        # {RbX=0.3,RbY=0.37},{RbX=0.12,RbY=0.76},{RbX=0.0,RbY=0.39}]}
        bound['RbShape'] = 'polygon'
        coordinates = [{"RbX": x[0] / mx, "RbY": x[1] / my} for x in list_coordinates]
        bound['RbVertices'] = coordinates

    elif object_type == 'rectangle':
        bound['RbShape'] = 'rectangle'
        np_coordinates = numpy.array(list_coordinates)
        min_rec = numpy.min(np_coordinates, axis=0)
        max_rec = numpy.max(np_coordinates, axis=0)
        w = max_rec[0] - min_rec[0]
        h = max_rec[1] - min_rec[1]
        bound['RbX'] = min_rec[0] / mx
        bound['RbY'] = min_rec[1] / my
        bound['RbW'] = w / mx
        bound['RbH'] = h / my
    elif object_type == 'circle':
        bound['RbShape'] = 'circle'
        bound['RbX'] = list_coordinates[0] / mx
        bound['RbY'] = list_coordinates[1] / my
        bound['RbRx'] = list_coordinates[2] / mx

    return bound
