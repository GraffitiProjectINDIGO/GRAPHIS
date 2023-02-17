from pathlib import Path
from sqlite3 import dbapi2, IntegrityError, DatabaseError
from .createDb import create
from .createDb import init
import sys
import json


class DBHandler:
    def __init__(self):
        self.con = dbapi2.Connection('')
        self.db_path = Path
        self.db_user = ''
        self.db_is_set = False
        self.is_locked = False

    def db_close(self):
        self.db_is_set = False
        self.con.close()

    def db_create(self, db_path: Path, user):
        try:
            create(db_path.as_posix())
            self.con = dbapi2.connect(db_path.as_posix())
            init(self.con)
            self.db_path = db_path
            self.db_user = user
            self.db_is_set = True
            return True
        except DatabaseError:
            print('Database can not be created: Probably locked', file=sys.stderr)
            return False

    def db_load(self, db_path: Path, user):
        self.con = dbapi2.connect(db_path.as_posix())
        init(self.con)
        self.db_path = db_path
        self.db_user = user
        self.db_is_set = True

    def db_store_image(self, image_path: Path):
        query = r"""Insert into images 
        (path,user,name)
        Values
        (:path,:user,:name)"""
        try:
            data = self.con.execute(query, {'path': image_path.as_posix(), 'user': self.db_user,
                                            'name': image_path.name})
            self.con.commit()
        except IntegrityError:
            return -1
        return data.lastrowid

    def db_store_size(self, image_id, width, height):
        query = r"""Update images
        SET width = :width,
            height = :height
        where id=:id"""
        self.con.execute(query, {'id': image_id, 'width': width, 'height': height})
        self.con.commit()

    def db_store_blob(self, image_id, blob, width, height):
        query = r"""Update images
        SET preview = :blob,
            width = :width,
            height = :height
        where id=:id"""
        self.con.execute(query, {'blob': blob, 'id': image_id, 'width': width, 'height': height})
        self.con.commit()

    def db_store_image_region(self, image_id, orig_image_region=''):

        query = r"""Update images
                SET orig_img_region_leftover = :orig_img_region
                where id=:id"""
        self.con.execute(query,  {'id': image_id, 'orig_img_region': json.dumps(orig_image_region)})
        self.con.commit()

    def db_load_images_list(self):
        query = r""" select images.*, Count(objects.image) as s_count,
                    SUM(IIF(objects.object_type == 'polygon', 1, 0)) as polygon_count,
                    SUM(IIF(objects.object_type == 'rectangle', 1, 0)) as rectangle_count,
                    SUM(IIF(objects.object_type == 'circle', 1, 0)) as circle_count from images
                left join objects on images.id = objects.image
                group by images.id
                order by images.id"""
        data = self.con.execute(query).fetchall()
        return data

    def db_delete_geometry(self, object_id: int):
        # GET IMAGE ID for IMAGE NAME in SFM DB
        self.con.execute(r'''DELETE FROM objects WHERE id = :id ''', {'id': object_id})
        self.con.commit()

    def db_load_object(self, obj_id: int):
        query = r"""SELECT * FROM objects 
        Where id = :id """

        data = self.con.execute(query, {'id': obj_id}).fetchone()
        return data

    def db_store_object(self, image_id: int, obj: str, data: dict, user=''):
        query = r"""Insert into objects 
        (image,user,object_type,data)
        Values
        (:image,:user, :obj, :data)"""
        if not user:
            user = self.db_user
        data = self.con.execute(query, {'image': image_id, 'user': user, 'obj': obj, 'data': json.dumps(data)})
        self.con.commit()
        return data.lastrowid

    def db_store_object_imgregion(self, image_id: int, obj: str, data: dict, user='', orig_img_region=None):
        query = r"""Insert into objects 
        (image,user,object_type,data, orig_img_region)
        Values
        (:image,:user, :obj, :data, :orig_img_region)"""
        if not user:
            user = self.db_user
        data = self.con.execute(query, {'image': image_id, 'user': user, 'obj': obj, 'data': json.dumps(data),
                                        'orig_img_region': json.dumps(orig_img_region)})
        self.con.commit()
        return data.lastrowid

    def update_object(self, obj_id, coordinates: list = None, data: dict = None):

        if (coordinates is not None) and (data is None):
            obj = self.db_load_object(obj_id)
            if obj:
                data = json.loads(obj['data'])
                data['coords'] = coordinates

        query = r"""Update objects
        SET data = :data
        where id=:id"""
        self.con.execute(query, {'data': json.dumps(data), 'id': obj_id})
        self.con.commit()

    def db_load_image(self, image_id: int):
        query = r"""SELECT id, image,data as data,object_type as object_type FROM objects 
        Where image = :id """

        data = self.con.execute(query, {'id': image_id}).fetchall()
        return data

    def db_load_objects_all(self):
        query = r"""select images.path as imgpath, images.name as image_name,  objects.*  from objects
                join images where images.id = objects.image order by images.id"""
        data = self.con.execute(query).fetchall()
        return data

    def db_load_objects_image(self, image_id: int):
        query = r"""select *  from objects where image = :id"""
        data = self.con.execute(query, {'id': image_id}).fetchall()
        return data
