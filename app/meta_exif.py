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

from exiftool import ExifTool
from app.db_handler import DBHandler
import json


def parse_img_region(region: dict, img_width: int, img_height: int):

    bound = region['RegionBoundary']

    if bound['RbUnit'] == 'relative':
        mx = img_width
        my = img_height
    else:
        mx = 1
        my = 1

    if bound['RbShape'] == 'polygon':

        vert = bound['RbVertices']

        coordinates = [[float(x['RbX']) * mx, float(x['RbY']) * my] for x in vert]
        coordinates.append(coordinates[0])
        object_type = 'polygon'

    elif bound['RbShape'] == 'rectangle':
        x = float(bound['RbX']) * mx
        y = float(bound['RbY']) * my
        w = float(bound['RbW']) * mx
        h = float(bound['RbH']) * my

        coordinates = [[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]]
        object_type = 'rectangle'
    else:
        x = float(bound['RbX']) * mx
        y = float(bound['RbY']) * my
        radius = float(bound['RbRx']) * mx
        coordinates = [x, y, radius]
        object_type = 'circle'

    data = {"attributes": region, 'coords': coordinates}

    return object_type, data, ''


def meta_writer(db1: DBHandler, user: str, keep_orig: bool = False) -> bool:

    print('\nWrite Data to Image - ImageRegions')

    count_image_written = 0

    db = DBHandler()
    db.db_load(db1.db_path, user)
    db.db_user = user

    try:
        et = ExifTool(executable=r"app\bin\exiftool-12.52.exe")
        et.run()
        print("\tStart running Exiftool")
    except OSError as err:
        print("\tStart running Exiftool failed")
        print("\tOS error:", err)

        return False

    images = db.db_load_images_list()

    for img in images:

        # image deleted_orig_tag will show that original tag is deleted and thus anyhow gets written
        force_change = True if img['deleted_orig_tag'] else False

        if img['s_count'] > 0 or img['deleted_orig_tag']:

            objects = db.db_load_objects_image(img['id'])
            img_regions = []

            for count, obj in enumerate(objects):

                if obj['changed']:
                    force_change = True
                img_region = json.loads(obj['data'])['attributes']

                img_regions.append(img_region)

            if img['orig_img_region_leftover']:
                region_leftover = json.loads(img['orig_img_region_leftover'])
                for reg in region_leftover:
                    img_regions.append(reg)

            if force_change:
                if len(img_regions) == 0:
                    # delete region if no region anymore in image
                    img_region_parsed = ''
                else:
                    img_region_parsed = json.dumps(img_regions, ensure_ascii=False,
                                                   separators=(', ', '= ')).replace('"', '')
                if not keep_orig:
                    et.execute(*['-overwrite_original', '-struct',
                                 '-xmp:ImageRegion=' + img_region_parsed, img['path']])
                else:
                    et.execute(*['-struct', '-xmp:ImageRegion=' + img_region_parsed, img['path']])
                if et.last_status:
                    print("\tProblem writing EXIF to: " + img['path'])
                else:
                    count_image_written += 1

    et.terminate()

    if count_image_written:
        print('\tSuccessfully wrote metadata: ImgNr. %i' % count_image_written)
    else:
        print('\tNo images needed to be changed')
    return True
