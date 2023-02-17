from exiftool import ExifTool
from app.db_handler import DBHandler
import json
import numpy


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

		coords = [[float(x['RbX']) * mx, float(x['RbY']) * my] for x in vert]
		coords.append(coords[0])
		object_type = 'polygon'

	elif bound['RbShape'] == 'rectangle':
		x = float(bound['RbX']) * mx
		y = float(bound['RbY']) * my
		w = float(bound['RbW']) * mx
		h = float(bound['RbH']) * my

		coords = [[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]]
		object_type = 'rectangle'
	else:
		x = float(bound['RbX']) * mx
		y = float(bound['RbY']) * my
		radius = float(bound['RbRx']) * mx
		coords = [x, y, radius]
		object_type = 'circle'

	data = {"attributes": region, 'coords': coords}

	return object_type, data, ''


def meta_writer(db1: DBHandler, user: str) -> bool:

	print('\nWrite Data to Image - ImageRegions')

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

		if img['s_count'] > 0:

			objects = db.db_load_objects_image(img['id'])
			img_regions = []
			img_width = img['width']
			img_height = img['height']
			for count, obj in enumerate(objects):

				img_region = json.loads(obj['data'])['attributes']

				# Geometry
				bound = {'RbUnit': 'relative'}

				mx = img_width
				my = img_height

				if obj['object_type'] == 'polygon':

					# RegionBoundary={RbShape=Polygon,RbUnit=Relative,RbVertices=[{RbX=0.0,RbY=0.0},{RbX=0.22,RbY=0.0},
					# {RbX=0.3,RbY=0.37},{RbX=0.12,RbY=0.76},{RbX=0.0,RbY=0.39}]}
					bound['RbShape'] = 'polygon'
					data = json.loads(obj['data'])
					coordinates = [{"RbX": x[0]/mx, "RbY": x[1]/my} for x in data['coords']]

					coordinates.pop()
					bound['RbVertices'] = coordinates

				elif obj['object_type'] == 'rectangle':
					bound['RbShape'] = 'rectangle'
					data = json.loads(obj['data'])
					np_coords = numpy.array(data["coords"])
					min_rec = np_coords.min(axis=0)
					max_rec = np_coords.max(axis=0)
					w = max_rec[0] - min_rec[0]
					h = max_rec[1] - min_rec[1]
					bound['RbX'] = min_rec[0] / mx
					bound['RbY'] = min_rec[1] / my
					bound['RbW'] = w / mx
					bound['RbH'] = h / my

				elif obj['object_type'] == 'circle':
					bound['RbShape'] = 'circle'
					data = json.loads(obj['data'])
					np_coords = data["coords"]
					bound['RbX'] = np_coords[0] / mx
					bound['RbY'] = np_coords[1] / my
					bound['RbRx'] = np_coords[2] / mx

				img_region["RegionBoundary"] = bound
				img_regions.append(img_region)

			if img['orig_img_region_leftover']:
				region_leftover = json.loads(img['orig_img_region_leftover'])
				for reg in region_leftover:
					img_regions.append(reg)

			img_region_parsed = json.dumps(img_regions, ensure_ascii=False, separators=(', ', '= ')).replace('"', '')
			et.execute(*['-overwrite_original', '-struct', '-xmp:ImageRegion=' + img_region_parsed, img['path']])
			if et.last_status:
				print("\tProblem writing EXIF to: " + img['path'])

	et.terminate()
	return True
