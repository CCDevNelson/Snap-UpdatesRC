import bpy
import os
import csv
import sqlite3
from sqlite3 import Error
import pathlib
import time
import operator
from . import snap_csv
import snap_db
from mv import utils

class OPERATOR_DB_Import_Csv(bpy.types.Operator):
    """Import CSV.
    """    
    bl_idname = "snap_db.import_csv"
    bl_label = "Import CSV"
    bl_description = "Import CSV"

    filename = bpy.props.StringProperty(name="CSV File Name", description="CSV file name to import")
    filepath = bpy.props.StringProperty(name="CSV Path", description="CSV path to import", subtype="FILE_PATH")
    directory =  bpy.props.StringProperty(name="CSV File Directory Name", description="CSV file directory name")
    rebuild_db = bpy.props.BoolProperty(name="Rebuild Database", default=False)    

    props = None
    debug_mode = False
    missing_render_mats = []


    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def start_progress():
        root = Tk()
        self.progress_bar = ttk.Progressbar(root, orient = HORIZONTAL, length = 120)
        self.progress_bar.pack()
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()        

        # to step progress bar up
        # progress.config(mode=‘determinate’, maximum=100, value=5)
        # progress.step(5)

    def stop_progress():
        self.progress_bar.stop()

    def render_material_exists(self, material_name):
        search_dirs = []
        materials_dir = utils.get_library_dir("materials")
        main_mat_dir = os.path.join(materials_dir, "Cabinet Materials", "Classy Closets")
        search_dirs.append(main_mat_dir)
        snap_db_mat_dir = snap_db.MATERIALS_DIR
        search_dirs.append(snap_db_mat_dir)

        mat_exists = False

        for search_directory in search_dirs:
            if os.path.isdir(search_directory):
                files = os.listdir(search_directory)

                if material_name + ".blend" in files:
                    mat_exists =  True

        return mat_exists

    def create_edge_color_collection(self, edge_type):
        props = bpy.context.scene.db_materials
        rows = snap_db.query_db(
            "SELECT\
                ColorCode,\
                DisplayName,\
                Description\
            FROM\
                CCItems\
            WHERE\
                ProductType = 'EB' AND TypeCode IN ('{type_code}')\
            ORDER BY\
                DisplayName ASC\
            ;\
            ".format(type_code=edge_type.type_code)
        )

        if len(rows) == 0:
            color = edge_type.colors.add()
            color.name = "None"
            color.color_code = 0
            color.description = "None"                 

        for row in rows:
            type_code = int(row[0])
            display_name = row[1]
            description = row[2]

            if display_name not in edge_type.colors:
                if self.render_material_exists(display_name):
                    color = edge_type.colors.add()
                    color.name = display_name
                    color.color_code = int(type_code)
                    color.description = description
                    color.check_render_material()

                elif display_name not in self.missing_render_mats:
                    self.missing_render_mats.append(display_name)

    def create_edge_type_collection(self):
        edges = self.props.edges
        door_drawer_edges = self.props.door_drawer_edges
        secondary_edges = self.props.secondary_edges

        edges.edge_types.clear()
        door_drawer_edges.edge_types.clear()
        secondary_edges.edge_types.clear()

        #Get Edge Types
        rows = snap_db.query_db(
            "SELECT\
                *\
            FROM\
                {}\
            ;".format(snap_db.EDGE_TYPE_TABLE_NAME)
        )       

        for row in rows:
            type_code = int(row[0])
            display_name = row[1]
            description = row[2]

            edge_type = edges.edge_types.add()
            edge_type.name = display_name
            edge_type.type_code = type_code
            edge_type.description = description

            #Custom edges
            door_drawer_edge_type = door_drawer_edges.edge_types.add()
            door_drawer_edge_type.name = display_name
            door_drawer_edge_type.type_code = type_code
            door_drawer_edge_type.description = description

            #Secondary edges
            edge2_type = secondary_edges.edge_types.add()
            edge2_type.name = display_name
            edge2_type.type_code = type_code
            edge2_type.description = description

        #Edge Colors
        for edge_type in self.props.edges.edge_types:
            self.create_edge_color_collection(edge_type)

        for edge_type in self.props.door_drawer_edges.edge_types:
            self.create_edge_color_collection(edge_type)      

        for edge_type in self.props.secondary_edges.edge_types:
            self.create_edge_color_collection(edge_type)
            
    def create_oversize_mat_color_collection(self, mat_type):
        os_colors = {}

        with open(snap_db.OS_MAT_COLORS_CSV_PATH) as os_mat_colors_file:
            reader = csv.reader(os_mat_colors_file, delimiter=',')
            next(reader)

            for row in reader:
                default = row[0]
                os_colors[row[0]] = row[1]

        rows = snap_db.query_db(
            "SELECT\
                ColorCode,\
                DisplayName,\
                Description\
            FROM\
                CCItems\
            WHERE\
                ProductType IN ('PM','VN') AND\
                Thickness == 0.75\
            ORDER BY\
                DisplayName ASC\
                    ;\
            ".format(type_code=mat_type.type_code)
        )        

        if len(rows) == 0:
            color = mat_type.colors.add()
            color.name = "None"
            color.color_code = 0
            color.description = "None"            

        for row in rows:
            type_code = int(row[0])
            display_name = row[1]
            description = row[2]

            if display_name not in mat_type.colors:
                if self.render_material_exists(display_name):
                    if display_name in os_colors:
                        color = mat_type.colors.add()
                        color.name = display_name
                        color.color_code = int(type_code)
                        color.oversize_max_len = int(os_colors[display_name])
                        color.description = description
                        color.check_render_material()                   

    def create_mat_color_collection(self, mat_type):
        props = bpy.context.scene.db_materials
        os_colors = {}

        with open(snap_db.OS_MAT_COLORS_CSV_PATH) as os_mat_colors_file:
            reader = csv.reader(os_mat_colors_file, delimiter=',')
            next(reader)

            for row in reader:
                default = row[0]
                os_colors[row[0]] = row[1]            

        rows = snap_db.query_db(
            "SELECT\
                ColorCode,\
                DisplayName,\
                Description\
            FROM\
                CCItems\
            WHERE\
                ProductType IN ('PM','VN') AND\
                TypeCode IN ('{type_code}')\
            ORDER BY\
                DisplayName ASC\
                    ;\
            ".format(type_code=mat_type.type_code)
        )        

        if len(rows) == 0:
            color = mat_type.colors.add()
            color.name = "None"
            color.color_code = 0
            color.description = "None"            

        for row in rows:
            type_code = int(row[0])
            display_name = row[1]
            description = row[2]

            if display_name not in mat_type.colors:
                if self.render_material_exists(display_name):
                    color = mat_type.colors.add()
                    color.name = display_name
                    color.color_code = int(type_code)
                    color.description = description
                    color.check_render_material()

                elif display_name not in self.missing_render_mats:
                    self.missing_render_mats.append(display_name)

    def create_mat_type_collection(self):
        materials = self.props.materials
        door_drawer_materials = self.props.door_drawer_materials

        materials.mat_types.clear()
        door_drawer_materials.mat_types.clear()
        
        #Get Material Types
        rows = snap_db.query_db(
            "SELECT\
                *\
            FROM\
                {}\
            ;".format(snap_db.MAT_TYPE_TABLE_NAME)
        )       

        for row in rows:
            type_code = int(row[0])
            display_name = row[1]
            description = row[2]

            mat_type = materials.mat_types.add()
            mat_type.name = display_name
            mat_type.type_code = type_code
            mat_type.description = description

            custom_mat_type = door_drawer_materials.mat_types.add()
            custom_mat_type.name = display_name
            custom_mat_type.type_code = type_code
            custom_mat_type.description = description    

        for i,mat_type in enumerate(self.props.materials.mat_types):
            if mat_type.type_code == 1:
                self.create_oversize_mat_color_collection(mat_type)
                continue
            self.create_mat_color_collection(mat_type)

        for mat_type in self.props.door_drawer_materials.mat_types:
            self.create_mat_color_collection(mat_type)

    def create_coutertop_collection(self):
        props = bpy.context.scene.db_materials
        items = []

        countertops = bpy.context.scene.db_materials.countertops
        countertops.countertop_types.clear()

        melamine = countertops.countertop_types.add()
        melamine.name = "Melamine - Same as Material Selection"
        
        for fname in os.listdir(snap_db.CT_DIR):
            type_path = os.path.join(snap_db.CT_DIR, fname)

            if os.path.isdir(type_path):
                ct_type = countertops.countertop_types.add()
                ct_type.name = fname

                for fname in os.listdir(type_path):
                    n_path = os.path.join(type_path, fname)

                    #IF CSV CREATE COLORS
                    if pathlib.Path(n_path).suffix == ".csv":
                        
                        with open(n_path) as colors_file:
                            reader = csv.reader(colors_file, delimiter=',')
                            next(reader)

                            for row in reader:
                                items.append((row[0], row[1], row[2]))

                        items.sort(key=operator.itemgetter(0))

                        for i in items:
                            display_name = i[0]
                            chip_code = i[1]
                            vendor = i[2]

                            color = ct_type.colors.add()
                            color.name = display_name
                            color.chip_code = chip_code
                            color.vendor = vendor
                            color.check_render_material()

                        items.clear()                       

                    #IF DIR ADD MFGS
                    if os.path.isdir(n_path):
                        ct_mfg = ct_type.manufactuers.add()
                        ct_mfg.name = fname

                        for fname in os.listdir(n_path):
                            nn_path = os.path.join(n_path, fname)

                            #IF CSV CREATE COLORS
                            if pathlib.Path(nn_path).suffix == ".csv":
                                #HPL and Quartz
                                with open(nn_path) as colors_file:
                                    reader = csv.reader(colors_file, delimiter=',')
                                    next(reader)

                                    for row in reader:
                                        items.append((row[0], row[1], row[2]))

                                items.sort(key=operator.itemgetter(0))

                                for i in items:
                                    display_name = i[0]
                                    chip_code = i[1]
                                    vendor = i[2]

                                    color = ct_mfg.colors.add()
                                    color.name = display_name
                                    color.chip_code = chip_code
                                    color.vendor = vendor
                                    color.check_render_material()

                                items.clear()

    def create_stain_color_collection(self):
        props = bpy.context.scene.db_materials
        props.stain_colors.clear()

        rows = snap_db.query_db(
            "SELECT\
                SKU,\
                DisplayName,\
                Description\
            FROM\
                CCItems\
            WHERE\
                ProductType = 'S'\
            ORDER BY\
                DisplayName ASC\
                    ;\
            "
        )        

        color = props.stain_colors.add()
        color.name = "None"
        color.color_code = 0
        color.description = "None"            

        for row in rows:
            sku = row[0]
            display_name = row[1]
            description = row[2]

            if display_name not in props.stain_colors:
                if self.render_material_exists(display_name):
                    color = props.stain_colors.add()
                    color.name = display_name.strip()
                    color.sku = sku
                    color.description = description

                elif display_name not in self.missing_render_mats:
                    self.missing_render_mats.append(display_name)

    def create_glaze_color_collection(self):
        props = bpy.context.scene.db_materials
        props.glaze_colors.clear()
        items = []

        with open(snap_db.GLAZE_COLORS_CSV_PATH) as glaze_colors_file:
            reader = csv.reader(glaze_colors_file, delimiter=',')
            next(reader)

            for row in reader:
                items.append((row[0], row[1], row[2]))

        items.sort(key=operator.itemgetter(1))

        color = props.glaze_colors.add()
        color.name = "None"
        color.sku = "0"
        color.description = "None"         

        for i in items:
            type_code = i[0]
            display_name = i[1]
            description = i[2]

            color = props.glaze_colors.add()
            color.name = display_name
            color.sku = type_code
            color.description = description

    def create_glaze_style_collection(self):
        props = bpy.context.scene.db_materials
        props.glaze_styles.clear()
        items = []

        with open(snap_db.GLAZE_STYLES_CSV_PATH) as glaze_styles_file:
            reader = csv.reader(glaze_styles_file, delimiter=',')
            next(reader)

            for row in reader:
                items.append((row[0], row[1], row[2]))

        items.sort(key=operator.itemgetter(1))

        color = props.glaze_styles.add()
        color.name = "None"
        color.sku = "0"
        color.description = "None" 

        for i in items:
            type_code = i[0]
            display_name = i[1]
            description = i[2]

            color = props.glaze_styles.add()
            color.name = display_name
            color.sku = type_code
            color.description = description               

    def create_door_color_collection(self):
        props = bpy.context.scene.db_materials
        props.moderno_colors.clear()
        items = []

        with open(snap_db.DOOR_COLORS_CSV_PATH) as door_colors_file:
            reader = csv.reader(door_colors_file, delimiter=',')
            next(reader)

            for row in reader:
                items.append((row[0], row[1], row[2]))

        items.sort(key=operator.itemgetter(1))

        for i in items:
            type_code = i[0]
            display_name = i[1]
            description = i[2]

            color = props.moderno_colors.add()
            color.name = display_name
            color.sku = type_code
            color.description = description               

    def create_glass_color_collection(self):
        props = bpy.context.scene.db_materials
        props.glass_colors.clear()
        items = []

        with open(snap_db.GLASS_COLORS_CSV_PATH) as glass_colors_file:
            reader = csv.reader(glass_colors_file, delimiter=',')
            next(reader)

            for row in reader:
                items.append((row[0], row[1], row[2]))

        items.sort(key=operator.itemgetter(1))

        color = props.glass_colors.add()
        color.name = "None"
        color.sku = "0"
        color.description = "None" 

        for i in items:
            type_code = i[0]
            display_name = i[1]
            description = i[2]

            color = props.glass_colors.add()
            color.name = display_name
            color.sku = type_code
            color.description = description 

    def create_drawer_slide_collection(self):
        props = bpy.context.scene.db_materials
        props.drawer_slides.clear()
        items = []

        for file in os.scandir(snap_db.DRAWER_SLIDE_DIR):
            slide_name = file.name.replace(".csv", '')
            slide_type = props.drawer_slides.add()
            slide_type.name = slide_name
            slide_type.db_name = ''

            with open(file.path) as sizes_file:
                reader = csv.reader(sizes_file, delimiter=',')
                next(reader)

                for row in reader:
                    items.append((row[0], row[1], row[2]))

            items.sort(key=operator.itemgetter(1))

            for i in items:
                length = i[0]
                front_hole_dim = i[1]
                back_hole_dim = i[2]

                size = slide_type.sizes.add()
                size.name = str(length) + " inch"
                size.slide_length_inch = float(length)
                size.front_hole_dim_mm = float(front_hole_dim)
                size.back_hole_dim_mm = float(back_hole_dim)

    def create_backing_veneer_color_collection(self):
        props = bpy.context.scene.db_materials
        props.backing_veneer_color.clear()

        rows = snap_db.query_db(
            "SELECT\
                *\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'VN' AND\
                Thickness = 0.25\
            ORDER BY\
                DisplayName ASC\
            ;"
        )        

        if len(rows) == 0:
            color = props.backing_veneer_color.add()
            color.name = "None"
            color.description = "None"            

        for row in rows:
            display_name = row[1]
            description = row[2]

            color = props.backing_veneer_color.add()
            color.name = display_name
            color.description = description

    def create_collections(self):
        props = bpy.context.scene.db_materials

        self.create_edge_type_collection()
        self.create_mat_type_collection()
        self.create_coutertop_collection()
        self.create_stain_color_collection()
        self.create_glaze_color_collection()
        self.create_glaze_style_collection()
        self.create_door_color_collection()
        self.create_glass_color_collection()
        self.create_drawer_slide_collection()
        self.create_backing_veneer_color_collection()
        self.props.collections_loaded = True
        props.materials.create_color_lists()

    def create_edge_type_table(self):
        edge_types = []

        with open(snap_db.EDGE_TYPES_CSV_PATH) as edge_types_file:
            reader = csv.reader(edge_types_file, delimiter=',')
            next(reader)

            for row in reader:
                edge_types.append(row)

        conn = snap_db.connect_db()
        cur = conn.cursor()

        #Create edge type table
        cur.execute("DROP TABLE IF EXISTS {};".format(snap_db.EDGE_TYPE_TABLE_NAME))

        cur.execute("CREATE TABLE {}\
                    (\
                    TypeCode,\
                    Name,\
                    Description\
                    );".format(snap_db.EDGE_TYPE_TABLE_NAME))

        #Populate edge types table
        for row in edge_types:
            cur.execute("INSERT INTO {table} (\
                            TypeCode,\
                            Name,\
                            Description\
                            )\
                        VALUES (\
                            '{type_code}',\
                            '{name}',\
                            '{desc}'\
                            )".format(table=snap_db.EDGE_TYPE_TABLE_NAME,
                                      type_code=int(row[0]),
                                      name=str(row[1]),
                                      desc=str(row[1])
                                      )
                        )

        conn.commit()
        conn.close()

    def create_slide_type_table(self):
        slide_types = []

        with open(snap_db.SLIDE_TYPES_CSV_PATH) as slide_types_file:
            reader = csv.reader(slide_types_file, delimiter=',')
            next(reader)

            for row in reader:
                slide_types.append(row)

        conn = snap_db.connect_db()
        cur = conn.cursor()

        #Create slide type table
        cur.execute("DROP TABLE IF EXISTS {};".format(snap_db.SLIDE_TYPE_TABLE_NAME))

        cur.execute("CREATE TABLE {}\
                    (\
                    TypeCode,\
                    Name,\
                    Description,\
                    DimFromDrawerBottom,\
                    DimToFirstHole,\
                    DimToSecondHole,\
                    DimToThirdHole,\
                    DimToFourthHole,\
                    DimToFifthHole);".format(snap_db.SLIDE_TYPE_TABLE_NAME))

        #Populate slide types table
        for row in slide_types:
            cur.execute("INSERT INTO {table} (\
                            TypeCode,\
                            Name,\
                            Description,\
                            DimFromDrawerBottom,\
                            DimToFirstHole,\
                            DimToSecondHole,\
                            DimToThirdHole,\
                            DimToFourthHole,\
                            DimToFifthHole\
                            )\
                        VALUES (\
                            '{type_code}',\
                            '{name}',\
                            '{desc}',\
                            '{dim_from_drawer_bottom}',\
                            '{dim_hole_1}',\
                            '{dim_hole_2}',\
                            '{dim_hole_3}',\
                            '{dim_hole_4}',\
                            '{dim_hole_5}'\
                            )".format(table=snap_db.SLIDE_TYPE_TABLE_NAME,
                                      type_code=int(row[0]),
                                      name=str(row[1]),
                                      desc=str(row[2]),
                                      dim_from_drawer_bottom=str(row[3]),
                                      dim_hole_1=str(row[4]),
                                      dim_hole_2=str(row[5]),
                                      dim_hole_3=str(row[6]),
                                      dim_hole_4=str(row[7]),
                                      dim_hole_5=str(row[8]),
                                      )
                        )

        conn.commit()
        conn.close()

    def create_material_type_table(self):
        #READ TYPE CODE DISPLAY NAMES FROM CSV
        mat_type_names = {}
        default = None

        with open(snap_db.MAT_TYPES_CSV_PATH) as mat_types_file:
            reader = csv.reader(mat_types_file, delimiter=',')
            next(reader)

            for row in reader:
                if default == None: default = row[0]
                mat_type_names[row[0]] = row[1]

        conn = snap_db.connect_db()
        cur = conn.cursor()

        #Create material type table
        cur.execute("DROP TABLE IF EXISTS {};".format(snap_db.MAT_TYPE_TABLE_NAME))

        cur.execute("CREATE TABLE {}\
                    (\
                    TypeCode,\
                    Name,\
                    Description\
                    );".format(snap_db.MAT_TYPE_TABLE_NAME))

        #READ MAT TYPES FROM DB
        rows = snap_db.query_db(
            "SELECT\
                TypeCode\
            FROM\
                CCItems\
            WHERE\
                ProductType in ('PM', 'WD', 'VN') AND\
                Thickness = 0.75\
            GROUP BY\
                TypeCode\
            ;"
        )

        mat_types = []

        for row in rows:
            type_code_str = str(row[0])
            if type_code_str in mat_type_names:
                name = mat_type_names[type_code_str]
                display_name = name.replace("3/4", "").strip()
                mat_types.append((type_code_str, display_name, display_name))
            else:
                if self.debug_mode:
                    print("Debug:{} - DISPLAY NAME FOR MATERIAL TYPE CODE NOT FOUND: {}".format(self.bl_idname, str(row[0])))

        default_in_list = None

        for mat_type in mat_types:
            if mat_type[0] == default:
                default_in_list = mat_type
                mat_types.remove(mat_type)
        
        mat_types.insert(0, default_in_list)

        #Oversize material type
        if '1' in mat_type_names:
            mat_types.insert(-1, (str(1), mat_type_names['1'], mat_type_names['1']))
        
        for row in mat_types:
            cur.execute("INSERT INTO {table} (\
                            TypeCode,\
                            Name,\
                            Description\
                            )\
                        VALUES (\
                            '{type_code}',\
                            '{name}',\
                            '{desc}'\
                            );".format(table=snap_db.MAT_TYPE_TABLE_NAME,
                                        type_code=row[0],
                                        name=row[1],
                                        desc=row[2]
                                        )
                        )

        conn.commit()
        conn.close()        

    def import_items_csv(self):
        if pathlib.Path(self.filename).suffix == ".csv":
            conn = snap_db.connect_db()
            defaults = snap_csv.CsvOptions()
            total_rows_inserted = 0
            start_time = time.clock()
            file = self.filepath.strip()
            info = snap_csv.CsvFileInfo(file, defaults)

            try:
                print("Processing " + file)
                info.process_file()
                total_rows_inserted += info.save_to_db(conn)
            except Exception as exc:
                print("Error on table {0}: \n {1}".format(info.get_table_name(), exc))

            print("Written {0} rows in {1:.3f} seconds".format(total_rows_inserted, time.clock() - start_time))

            conn.commit()
            conn.close()

        else:
            self.report({'WARNING'}, "The selected file is not a CSV file!")        

    def create_tables(self):
        self.create_edge_type_table()
        self.create_material_type_table()
        self.create_slide_type_table()

    def execute(self, context):
        self.props = bpy.context.scene.db_materials
        self.debug_mode = context.user_preferences.addons["snap_db"].preferences.debug_mode

        if self.rebuild_db:
            os.remove(snap_db.DB_PATH)       

        if not os.path.exists(snap_db.DB_PATH):
            self.import_items_csv()
            self.create_tables()

        self.create_collections()

        if self.debug_mode and len(self.missing_render_mats) > 0:
            print(
                "\nThe following closet material colors are missing render materials!:\n",
                sorted(self.missing_render_mats),
                "\n"
                )

        return {'FINISHED'}


def register():
    bpy.utils.register_class(OPERATOR_DB_Import_Csv)

def unregister():
    bpy.utils.unregister_class(OPERATOR_DB_Import_Csv)        