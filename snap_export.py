  
bl_info = {
    "name": "SNaP Import-Export",
    "author": "Ryan Montes",
    "version": (1, 0, 0),
    "blender": (2, 7, 8),
    "location": "Tools Shelf",
    "description": "SNaP Import-Export",
    "warning": "",
    "wiki_url": "",
    "category": "SNaP"
}

import bpy
import math
import os
from mv import unit, utils, fd_types
from bpy.types import Operator
import xml.etree.ElementTree as ET
import csv
import sqlite3
from sqlite3 import Error
from . import snap_xml
import snap_db
from snap_db import utils as snap_utils
from pprint import pprint

try:
    from .developer_utils import debug_xml_export
except ImportError:
    pass
else:
    pass


BL_DIR = os.path.dirname(bpy.app.binary_path)
CSV_PATH = os.path.join(BL_DIR, "data", "CCItems.csv")
DIR_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', "snap_db")
ITEMS_TABLE_NAME = "CCItems"


def get_project_dir():
    project_dir = bpy.context.user_preferences.addons['fd_projects'].preferences.project_dir

    if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    return project_dir

def get_slide_size(slide_type, assembly):
    closet_props = assembly.obj_bp.lm_closets

    if closet_props.is_drawer_box_bp:
        drawer_depth = unit.meter_to_inch(assembly.obj_y.location.y)

    if closet_props.is_drawer_side_bp:
        drawer_box_assembly = fd_types.Assembly(assembly.obj_bp.parent)
        drawer_depth = unit.meter_to_inch(drawer_box_assembly.obj_y.location.y)

    mat_props = bpy.context.scene.db_materials
    sizes = []
    slide_type = mat_props.get_drawer_slide_type()

    for size in slide_type.sizes:
        sizes.append(size)

    sizes.reverse()

    for size in sizes:
        if drawer_depth >= float(size.slide_length_inch):
            return size

def get_hardware_sku(obj_bp, assembly, item_name):
    conn = snap_db.connect_db()
    cursor = conn.cursor()
    sku = "Unknown"
    #print(obj_bp, assembly.obj_bp, item_name)

    #Pull
    if assembly.obj_bp.lm_closets.is_handle:
        pull_cat = bpy.context.scene.lm_closets.closet_options.pull_category
        pull_name = bpy.context.scene.lm_closets.closet_options.pull_name
        vendor_id = item_name[:10] # use vendor code in item name for lookup (123.45.678)

        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                VendorItemNum ='{}'\
            ;".format(vendor_id))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND PULL SKU: ", sku)
        
        conn.close()

        return sku

    #Hinge
    if obj_bp.lm_closets.is_hinge:
        hinge_name = bpy.context.scene.lm_closets.closet_options.hinge_name

        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'HW' AND\
                Name LIKE'{}'\
            ;".format("%" + hinge_name + "%"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND HINGE SKU: ", sku)
        
        conn.close()

        return sku

    #Hinge Plate
    if "Mounting Plate" in item_name:
        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'HW' AND\
                Name LIKE'{}'\
            ;".format("%" + item_name + "%"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND MOUNTING PLATE SKU: ", sku)
        
        conn.close()

        return sku        
    

    #Slide
    if "Drawer Slide" in item_name:
        mat_props = bpy.context.scene.db_materials
        slide_type = mat_props.get_drawer_slide_type()
        slide_name = slide_type.name
        slide_size = get_slide_size(slide_type, assembly)
        slide_len = slide_size.slide_length_inch

        if slide_len % 1 == 0:
            slide_len = int(slide_len)

        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'HW' AND\
                Name LIKE '{}' AND\
                Name LIKE '{}'\
            ;".format("%" + slide_name + "%",
                "%" + str(slide_len) + "%",))    

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND SLIDE SKU: ", sku)
        
        conn.close()
        return sku        

    #Hamper Basket
    if assembly.obj_bp.lm_closets.is_hamper_bp:
        mat_props = bpy.context.scene.db_materials
        hamper_insert_bp = assembly.obj_bp.parent
        basket_color = mat_props.wire_basket_colors
        basket_width = unit.meter_to_inch(assembly.obj_x.location.x)
        basket_depth = unit.meter_to_inch(assembly.obj_y.location.y)

        #'547.42.231',#Chrome 18x14
        #'547.42.232',#Chrome 24x14
        #'547.42.241',#Chrome 18x16
        #'547.42.242',#Chrome 24x16
        #'547.42.731',#White 18x14
        #'547.42.732',#White 24x14
        #'547.42.741',#White 18x16
        #'547.42.742',#White 24x16

        color_id = 2 if basket_color == 'CHROME' else 7
        width_id = 1 if basket_width == 18.0 else 2
        depth_id = 3 if basket_depth == 14.0 else 4
        vendor_id = '547.42.{}{}{}'.format(color_id,depth_id,width_id)

        cursor.execute("SELECT\
            sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                VendorItemNum ='{}'\
            ;".format(vendor_id))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND HAMPER BASKET SKU: ", sku)
        
        conn.close()

        return sku        

    #Hamper Brake Flaps
    if "Hamper Brake Flap Left" in item_name or "Hamper Brake Flap Right" in item_name:
        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                Name LIKE'{}'\
            ;".format("%" + item_name + "%"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND BRAKE FLAP SKU: ", sku)
        
        conn.close()

        return sku

    #Hamper Rack
    if "Hamper Rack" in item_name:
        mat_props = bpy.context.scene.db_materials        
        basket_color = mat_props.wire_basket_colors

        if basket_color == 'CHROME':
            rack_name = "Hamper Rack Chrome"

        elif basket_color == 'WHITE':
            rack_name = "Hamper Rack White"

        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                Name LIKE'{}'\
            ;".format("%" + rack_name + "%"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND HAMPER RACK SKU: ", sku)
        
        conn.close()

        return sku        

    #Hamper Laundry Bag
    if "Cloth Laundry Bag" in item_name:
        basket_width = unit.meter_to_inch(assembly.obj_x.location.x)

        if basket_width > 18.0:
            bag_name = item_name + " 24"
        else:
            bag_name = item_name + " 18"

        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                Name LIKE'{}'\
            ;".format("%" + bag_name + "%"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND LAUNDRY BAG SKU: ", sku)
        
        conn.close()

        return sku

    #Rod
    if assembly.obj_bp.lm_closets.is_hanging_rod:
        item_name = bpy.context.scene.lm_closets.closet_options.rods_name
        vendor_id = item_name[-10:]

        cursor.execute("SELECT\
            sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                VendorItemNum ='{}'\
            ;".format(vendor_id))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND HANGING ROD SKU: ", sku)
        
        conn.close()

        return sku

    #Rod Cup
    if "Pole Cup" in item_name:
        sku = bpy.context.scene.lm_closets.closet_options.pole_cup_name

        #print("FOUND POLE CUP SKU:", sku)

        return sku    

    #KD Fitting
    if "KD Fitting" in item_name:
        mat_props = bpy.context.scene.db_materials
        sku = mat_props.kd_fitting_color
        #print("FOUND KD FITTING SKU:", sku)

        return sku

    #Pegs
    if "Peg Chrome" in item_name:
        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'HW' AND\
                Name LIKE'{}'\
            ;".format("%peg%chrome%"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            #print("FOUND CHROME PEG SKU: ", sku)

        conn.close()

        return sku

    #Door lock
    if item_name == "Door Lock":
        print("DOOR LOCK")
        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                VendorItemNum =='{}'\
            ;".format("C8055-14A"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            print("FOUND DOOR LOCK SKU:", sku)

        conn.close()

        return sku

    #Door lock cam
    if item_name == "Door Lock Cam":
        print("DOOR LOCK CAM")

        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                VendorItemNum =='{}'\
            ;".format("C7004-2C"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            print("FOUND LOCK CAM SKU:", sku)

        conn.close()

        return sku

    #Door lock latch finger
    if item_name == "Door Lock Latch":
        print("DOOR LOCK LATCH")

        cursor.execute("SELECT\
                sku\
            FROM\
                CCItems\
            WHERE\
                ProductType == 'AC' AND\
                VendorItemNum =='{}'\
            ;".format("245.74.200"))

        rows = cursor.fetchall()

        for row in rows:
            sku = row[0]
            print("FOUND LATCH SKU:", sku)

        conn.close()

        return sku

    #----------Closet Accessories
    #Valet Rod
    if item_name == "Valet Rod":
        print(item_name)
        sku = "AC-0000177"

        return sku

    #Valet Rod 2
    if item_name == "Valet Rod 2":
        print(item_name)
        sku = "AC-0000176"

        return sku

    #Wire Basket
    if item_name == "Wire Basket":
        print(item_name)
        sku = "AC-0000001"

        return sku

    #Tie Rack
    if item_name == "Tie Rack":
        print(item_name)
        sku = "AC-0000153"

        return sku

    #Belt Rack
    if item_name == "Belt Rack":
        print(item_name)
        sku = "AC-0000143"

        return sku

    #Robe Hook
    if item_name == "Robe Hook":
        print(item_name)
        sku = "AC-0000188"

        return sku

    return sku

def get_export_prompts(obj_bp):
    """ Used in create_fluid_project_xml
        this collects all of the needed product prompts for the 121 product match
    """
    
    prompts = {}
    
    def add_prompt(prompt):
        if prompt.Type == 'NUMBER':
            prompts[prompt.name] = str(prompt.NumberValue)
        if prompt.Type == 'QUANTITY':
            prompts[prompt.name] = str(prompt.QuantityValue)
        if prompt.Type == 'COMBOBOX':
            prompts[prompt.name] = str(prompt.COL_EnumItem[prompt.EnumIndex].name)
        if prompt.Type == 'CHECKBOX':
            prompts[prompt.name] = str(prompt.CheckBoxValue)
        if prompt.Type == 'TEXT':
            prompts[prompt.name] = str(prompt.TextValue)
        if prompt.Type == 'DISTANCE':
            prompts[prompt.name] = str(round(unit.meter_to_active_unit(prompt.DistanceValue),2))
        if prompt.Type == 'ANGLE':
            prompts[prompt.name] = str(prompt.AngleValue)
        if prompt.Type == 'PERCENTAGE':
            prompts[prompt.name] = str(prompt.PercentageValue)
        if prompt.Type == 'PRICE':
            prompts[prompt.name] = str(prompt.PriceValue)
    
    def add_child_prompts(obj):
        for child in obj.children:
            if child.mv.type == 'BPASSEMBLY':
                add_prompts(child)
            if len(child.children) > 0:
                add_child_prompts(child)
        
    def add_prompts(obj):
        for prompt in obj.mv.PromptPage.COL_Prompt:
            if prompt.export:
                add_prompt(prompt)
                
    add_prompts(obj_bp)
    add_child_prompts(obj_bp)

    return prompts


class OPS_Export_XML(Operator):
    bl_idname = "snap_db.export_xml"
    bl_label = "Export XML File"
    bl_description = "This will export an XML file. The file must be saved first."
    
    walls = []
    products = []
    buyout_products = []

    cover_cleat_lengths = []
    cover_cleat_bp = None

    single_exposed_flat_crown = []
    top_edgebanded_flat_crown = []
    flat_crown_heights = []
    flat_crown_lengths = []
    flat_crown_bp = None

    crown_molding_lengths = []
    crown_molding_bp = None

    inverted_base_lengths = []
    inverted_base_bp = None

    base_molding_lengths = []
    base_molding_bp = None

    tk_skin_heights = []
    tk_skin_lengths = []
    tk_skin_bp = None
    
    buyout_materials = []
    edgeband_materials = {}
    solid_stock_materials = {}

    op_groups = []
    labels = []

    mfg_node = None

    job_number = 0

    job_count = 0 #Does not currently increment
    item_count = 0 
    assembly_count = 0 
    part_count = 0
    mfg_count = 0 #Does not currently increment
    label_count = 0
    mat_count = 0
    op_count = 0
    or_count = 0

    xml = None
    xml_path = bpy.props.StringProperty(name="XML Path", subtype='DIR_PATH')

    debug_mode = False
    debugger = None

    top_shelf_sizes = (60.0, 72.0, 84.0, 96.0)
    top_shelf_offset = 2.0    

    @classmethod
    def poll(cls, context):
        if bpy.data.filepath != "":
            return True
        else:
            return False

    def distance(self,distance):
        return str(math.fabs(round(unit.meter_to_active_unit(distance),2)))
    
    def location(self,location):
        return str(round(unit.meter_to_active_unit(location),2))
    
    def angle(self,angle):
        return str(round(math.degrees(angle),2))
    
    def clear_and_collect_data(self,context):
        for product in self.products:
            self.products.remove(product)
        
        for wall in self.walls:
            self.walls.remove(wall)

        #bpy.ops.fd_material.get_materials()

        for scene in bpy.data.scenes:
            if not scene.mv.plan_view_scene and not scene.mv.elevation_scene:
                for obj in scene.objects:
                    if not obj.mv.dont_export:
                        if obj.mv.type == 'BPWALL':
                            self.walls.append(obj)
                        if obj.mv.type == 'BPASSEMBLY':
                            if obj.mv.type_group == 'PRODUCT':
                                self.products.append(obj)

    def get_var_sec_length(self, x):
        increment = 3
        offset = unit.inch(2.5)
        max_len = 97

        for length in range(increment, max_len, increment):
            length = unit.inch(length)
            if x < length:
                if length - x <= offset:
                    return length + unit.inch(increment)
                else:
                    return length    
            
        return length    

    def is_variable_section(self, assembly):
        opening_name = assembly.obj_bp.mv.opening_name
        if opening_name:
            carcass_bp = utils.get_parent_assembly_bp(assembly.obj_bp)
            carcass_assembly = fd_types.Assembly(carcass_bp)
            variable_section = carcass_assembly.get_prompt("CTF Opening {}".format(opening_name)).value()
            
            return variable_section

        else:
            return False

    def is_var_width_toe_kick(self,assembly):
        p_assembly = fd_types.Assembly(assembly.obj_bp.parent)

        if p_assembly.obj_bp.lm_closets.is_toe_kick_insert_bp:
            var_width = p_assembly.get_prompt("Variable Width")
            if var_width:
                if var_width.value():
                    return True
        return False

    def is_var_height_toe_kick(self,assembly):
        p_assembly = fd_types.Assembly(assembly.obj_bp.parent)

        if p_assembly.obj_bp.lm_closets.is_toe_kick_insert_bp:
            var_height = p_assembly.get_prompt("Variable Height")
            if var_height:
                if var_height.value():
                    return True
        return False


    def get_product_z_location(self,product):
        #Height Above Floor
        if product.obj_bp.location.z > 0:
            return product.obj_bp.location.z - math.fabs(product.obj_z.location.z)
        else:
            return product.obj_bp.location.z
    
    def get_part_qty(self,assembly):
        qty = 1
        z_quantity = assembly.get_prompt("Z Quantity")
        x_quantity = assembly.get_prompt("X Quantity")
        if z_quantity:
            qty += z_quantity.value() - 1
        
        if x_quantity:
            qty += x_quantity.value() - 1
            
        return str(qty)
        
    def get_part_width(self,assembly):
        width = math.fabs(assembly.obj_y.location.y)
        oversize_width = assembly.get_prompt("Oversize Width")
        if oversize_width:
            width += oversize_width.value()
        if assembly.obj_bp.lm_closets.is_filler_bp:
            width += unit.inch(2)
            if width < unit.inch(4):
                    width = unit.inch(4)

        if self.is_var_height_toe_kick(assembly):
            #Exclude stringer parts and tk skins
            if not assembly.obj_bp.lm_closets.is_toe_kick_stringer_bp and not assembly.obj_bp.lm_closets.is_toe_kick_skin_bp:
                width += unit.inch(3.0)

        if assembly.obj_bp.lm_closets.is_bottom_capping_bp:
            against_left_wall = assembly.get_prompt("Against Left Wall")
            against_right_wall = assembly.get_prompt("Against Right Wall")
            if(against_left_wall and against_right_wall):
                if(against_left_wall.value()):
                    width += unit.inch(3.0)
                if(against_right_wall.value()):
                    width += unit.inch(3.0)

        return self.distance(width)
    
    def get_part_length(self,assembly):
        length = math.fabs(assembly.obj_x.location.x)
        props = assembly.obj_bp.lm_closets
        parent_bp = assembly.obj_bp.parent

        if self.is_variable_section(assembly):
    
            if props.is_cleat_bp or props.is_shelf_bp:
                if not props.is_door_bp:
                    length = self.get_var_sec_length(length)

        if self.is_var_width_toe_kick(assembly):
            #Exclude end cap parts
            if not assembly.obj_bp.lm_closets.is_toe_kick_end_cap_bp:
                length += unit.inch(3.0)

        if parent_bp.lm_closets.is_closet_top_bp:
            top_shelf_assembly = fd_types.Assembly(parent_bp)
            Exposed_Left = top_shelf_assembly.get_prompt("Exposed Left")
            Exposed_Right = top_shelf_assembly.get_prompt("Exposed Right")

            if Exposed_Left.value() == False or Exposed_Right.value() == False:
                print("Oversizing top shelf - length:",unit.meter_to_inch(length))
                length = self.get_os_top_shelf_length(length)
                length = unit.inch(length)
                print("Top shelf oversize length",length)
        
        if parent_bp.lm_closets.is_closet_bottom_bp:
            capping_bottom_assembly = fd_types.Assembly(parent_bp)
            against_left_wall = capping_bottom_assembly.get_prompt("Against Left Wall")
            against_right_wall = capping_bottom_assembly.get_prompt("Against Right Wall")
            if against_left_wall:
                if against_left_wall.value():
                    length += unit.inch(3)
            if against_right_wall:
                if against_right_wall.value():
                    length += unit.inch(3)
        return self.distance(length)

    def get_os_top_shelf_length(self, x):
        for i,length in enumerate(self.top_shelf_sizes):
            if unit.meter_to_inch(x) + self.top_shelf_offset >= self.top_shelf_sizes[-1]:
                return self.top_shelf_sizes[-1]

            if unit.meter_to_inch(x) < length:
                if length - unit.meter_to_inch(x) <= self.top_shelf_offset:
                    return self.top_shelf_sizes[i + 1]
                else:
                    return self.top_shelf_sizes[i]  
        
    def get_part_x_location(self,obj,value):
        if obj.parent is None or obj.parent.mv.type_group == 'PRODUCT':
            return self.location(value)
        value += obj.parent.location.x
        return self.get_part_x_location(obj.parent,value)

    def get_part_y_location(self,obj,value):
        if obj.parent is None or obj.parent.mv.type_group == 'PRODUCT':
            return self.location(value)
        value += obj.parent.location.y
        return self.get_part_y_location(obj.parent,value)

    def get_part_z_location(self,obj,value):
        if obj.parent is None or obj.parent.mv.type_group == 'PRODUCT':
            return self.location(value)
        value += obj.parent.location.z
        return self.get_part_z_location(obj.parent,value)

    def get_part_comment(self,obj):
        if not obj.mv.comment_2 == "":
            return obj.mv.comment_2
        else:
            return ""

    def get_part_base_point(self,assembly):
        mx = False
        my = False
        mz = False
        
        if assembly.obj_x.location.x < 0:
            mx = True
        if assembly.obj_y.location.y < 0:
            my = True
        if assembly.obj_z.location.z < 0:
            mz = True
            
        if (mx == False) and (my == False) and (mz == False):
            return "1"
        if (mx == False) and (my == False) and (mz == True):
            return "2"        
        if (mx == False) and (my == True) and (mz == False):
            return "3"
        if (mx == False) and (my == True) and (mz == True):
            return "4"
        if (mx == True) and (my == True) and (mz == False):
            return "5"
        if (mx == True) and (my == True) and (mz == True):
            return "6"        
        if (mx == True) and (my == False) and (mz == False):
            return "7"
        if (mx == True) and (my == False) and (mz == True):
            return "8"   
             
        return "1"

    def get_edgebanding_name(self,obj,edge,spec_group):
        if obj.mv.edgeband_material_name != "" and edge != "":
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = obj.mv.edgeband_material_name
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness
            return edge_mat_name
        else:
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = utils.get_edgebanding_name_from_pointer_name(edge,spec_group)
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness                
            return edge_mat_name
    
    def get_edgebanding_name_w1(self,obj,edge,spec_group):
        if obj.mv.edgeband_material_name_w1 != "" and edge != "":
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = obj.mv.edgeband_material_name_w1
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness
            return edge_mat_name
        else:
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = utils.get_edgebanding_name_from_pointer_name(edge,spec_group)
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness                
            return edge_mat_name    
    
    def get_edgebanding_name_w2(self,obj,edge,spec_group):
        if obj.mv.edgeband_material_name_w2 != "" and edge != "":
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = obj.mv.edgeband_material_name_w2
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness
            return edge_mat_name
        else:
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = utils.get_edgebanding_name_from_pointer_name(edge,spec_group)
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness                
            return edge_mat_name        
    
    def get_edgebanding_name_l1(self,obj,edge,spec_group):
        if obj.mv.edgeband_material_name_l1 != "" and edge != "":
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = obj.mv.edgeband_material_name_l1
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness
            return edge_mat_name
        else:
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = utils.get_edgebanding_name_from_pointer_name(edge,spec_group)
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness                
            return edge_mat_name          
    
    def get_edgebanding_name_l2(self,obj,edge,spec_group):
        if obj.mv.edgeband_material_name_l2 != "" and edge != "":
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = obj.mv.edgeband_material_name_l2
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness
            return edge_mat_name
        else:
            thickness = utils.get_edgebanding_thickness_from_pointer_name(edge,spec_group)
            edge_mat_name = utils.get_edgebanding_name_from_pointer_name(edge,spec_group)
            if edge_mat_name not in self.edgeband_materials and edge_mat_name != "":
                self.edgeband_materials[edge_mat_name] = thickness                
            return edge_mat_name

    def get_pull_drilling(self, assembly, token, circles):
        normal_z = 1
        org_displacement = 0

        if token.face == '6':
            normal_z = -1
            org_displacement = self.distance(snap_utils.get_part_thickness(assembly.obj_bp))

        param_dict = token.create_parameter_dictionary()  
        dim_in_x = float(param_dict['Par1'])
        dim_in_y = float(param_dict['Par2'])
        dim_in_z = float(param_dict['Par3'])
        bore_dia_meter = unit.millimeter(float(param_dict['Par4']))
        bore_dia = unit.meter_to_inch(bore_dia_meter)
        end_dim_in_x = float(param_dict['Par5'])
        end_dim_in_y = float(param_dict['Par6'])
        #distance_between_holes = float(param_dict['Par7'])

        #Hole 1
        cir_dict = {}
        cir_dict['cen_x'] = dim_in_x
        cir_dict['cen_y'] = dim_in_y
        cir_dict['cen_z'] = dim_in_z
        cir_dict['diameter'] = bore_dia
        cir_dict['normal_z'] = normal_z
        cir_dict['org_displacement'] = 0
        circles.append(cir_dict)

        #Hole 2
        cir_dict = {}
        cir_dict['cen_x'] = end_dim_in_x
        cir_dict['cen_y'] = end_dim_in_y
        cir_dict['cen_z'] = dim_in_z
        cir_dict['diameter'] = bore_dia
        cir_dict['normal_z'] = normal_z
        cir_dict['org_displacement'] = 0
        circles.append(cir_dict)

        return circles

    def get_door_hinge_drilling(self, assembly, token, circles):
        door_swing = assembly.get_prompt("Door Swing").value()
        door_x_dim = unit.meter_to_inch(assembly.obj_x.location.x)
        door_y_dim = abs(unit.meter_to_inch(assembly.obj_y.location.y))
        normal_z = -1
        org_displacement = self.distance(snap_utils.get_part_thickness(assembly.obj_bp))
        bore_dia = unit.meter_to_inch(unit.millimeter(35))
        dim_in_x = unit.meter_to_inch(unit.millimeter(78))
        dim_in_y = unit.meter_to_inch(unit.millimeter(21))
        bore_depth = unit.meter_to_inch(unit.millimeter(14))
        screw_hole_y_dim = unit.meter_to_inch(unit.millimeter(10))
        screw_hole_dia = unit.meter_to_inch(unit.millimeter(2))
        distance_between_holes = unit.meter_to_inch(unit.millimeter(45))
        mid_hole_offset = unit.meter_to_inch(unit.millimeter(16))
        screw_hole_depth = unit.meter_to_inch(unit.millimeter(4))

        if door_swing == "Bottom":
            print("Bottom swing hamper door")

        #Bottom
        #Add Main hole
        cir = {}
        cir['cen_x'] = -dim_in_x
        cir['cen_y'] = dim_in_y
        cir['cen_z'] = bore_depth
        cir['diameter'] = bore_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)                                        

        #Add screw hole left
        cir = {}
        cir['cen_x'] = -(dim_in_x - distance_between_holes * 0.5)
        cir['cen_y'] = dim_in_y + screw_hole_y_dim
        cir['cen_z'] = screw_hole_depth
        cir['diameter'] = screw_hole_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)                                        

        #add screw hole right
        cir = {}
        cir['cen_x'] = -(dim_in_x + distance_between_holes * 0.5)
        cir['cen_y'] = dim_in_y + screw_hole_y_dim
        cir['cen_z'] = screw_hole_depth
        cir['diameter'] = screw_hole_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)

        dim_in_x = door_x_dim - dim_in_x

        #Top
        #Add Main hole
        cir = {}
        cir['cen_x'] = -dim_in_x
        cir['cen_y'] = dim_in_y
        cir['cen_z'] = bore_depth
        cir['diameter'] = bore_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)                                        

        #Add screw hole left
        cir = {}
        cir['cen_x'] = -(dim_in_x - distance_between_holes * 0.5)
        cir['cen_y'] = dim_in_y + screw_hole_y_dim
        cir['cen_z'] = screw_hole_depth
        cir['diameter'] = screw_hole_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)                                        

        #add screw hole right
        cir = {}
        cir['cen_x'] = -(dim_in_x + distance_between_holes * 0.5)
        cir['cen_y'] = dim_in_y + screw_hole_y_dim
        cir['cen_z'] = screw_hole_depth
        cir['diameter'] = screw_hole_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)

        #Mid hinge drilling for doors longer than 39H Count
        if door_x_dim > 50:
            if(round(unit.meter_to_millimeter(door_x_dim) / 32) % 2 == 0):
                if door_swing == "Left":
                    dim_in_x = door_x_dim * 0.5 + mid_hole_offset
                else:
                    dim_in_x = door_x_dim * 0.5 - mid_hole_offset
            else:
                dim_in_x = door_x_dim * 0.5            

            #Add Main hole
            cir = {}
            cir['cen_x'] = -dim_in_x
            cir['cen_y'] = dim_in_y
            cir['cen_z'] = bore_depth
            cir['diameter'] = bore_dia 
            cir['normal_z'] = normal_z
            cir['org_displacement'] = org_displacement
            circles.append(cir)                                        

            #Add screw hole left
            cir = {}
            cir['cen_x'] = -(dim_in_x - distance_between_holes * 0.5)
            cir['cen_y'] = dim_in_y + screw_hole_y_dim
            cir['cen_z'] = screw_hole_depth
            cir['diameter'] = screw_hole_dia 
            cir['normal_z'] = normal_z
            cir['org_displacement'] = org_displacement
            circles.append(cir)                                        

            #add screw hole right
            cir = {}
            cir['cen_x'] = -(dim_in_x + distance_between_holes * 0.5)
            cir['cen_y'] = dim_in_y + screw_hole_y_dim
            cir['cen_z'] = screw_hole_depth
            cir['diameter'] = screw_hole_dia 
            cir['normal_z'] = normal_z
            cir['org_displacement'] = org_displacement
            circles.append(cir)

        return circles

    def get_hamper_door_hinge_drilling(self, assembly, token, circles):
        #door_x_dim = unit.meter_to_inch(assembly.obj_x.location.x)
        door_y_dim = abs(unit.meter_to_inch(assembly.obj_y.location.y))
        normal_z = -1
        org_displacement = self.distance(snap_utils.get_part_thickness(assembly.obj_bp))
        bore_dia = unit.meter_to_inch(unit.millimeter(35))
        dim_in_x = unit.meter_to_inch(unit.millimeter(21))
        dim_in_y = unit.meter_to_inch(unit.millimeter(78))                                   
        bore_depth = unit.meter_to_inch(unit.millimeter(11.5))
        screw_hole_x_dim = unit.meter_to_inch(unit.millimeter(9.5)) 
        screw_hole_dia = unit.meter_to_inch(unit.millimeter(0.5)) 
        distance_between_holes = unit.meter_to_inch(unit.millimeter(45))

        #Right
        cir = {}
        cir['cen_x'] = -dim_in_y  # -dim_in_x
        cir['cen_y'] = dim_in_x  # dim_in_y
        cir['cen_z'] = bore_depth
        cir['diameter'] = bore_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)                                        

        cir = {}
        cir['cen_x'] = -(dim_in_y + distance_between_holes * 0.5)
        cir['cen_y'] = dim_in_x + screw_hole_x_dim
        cir['cen_z'] = bore_depth
        cir['diameter'] = screw_hole_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)                                        

        cir = {}
        cir['cen_x'] = -(dim_in_y - distance_between_holes * 0.5)
        cir['cen_y'] = dim_in_x + screw_hole_x_dim
        cir['cen_z'] = bore_depth
        cir['diameter'] = screw_hole_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)

        dim_in_y = door_y_dim - dim_in_y

        #Left
        cir = {}
        cir['cen_x'] = -dim_in_y  # -dim_in_x
        cir['cen_y'] = dim_in_x  # dim_in_y
        cir['cen_z'] = bore_depth
        cir['diameter'] = bore_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)                                        

        cir = {}
        cir['cen_x'] = -(dim_in_y + distance_between_holes * 0.5)
        cir['cen_y'] = dim_in_x + screw_hole_x_dim
        cir['cen_z'] = bore_depth
        cir['diameter'] = screw_hole_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)                                        

        cir = {}
        cir['cen_x'] = -(dim_in_y - distance_between_holes * 0.5)
        cir['cen_y'] = dim_in_x + screw_hole_x_dim
        cir['cen_z'] = bore_depth
        cir['diameter'] = screw_hole_dia 
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)

        return circles

    def get_shelf_kd_drilling(self, assembly, token, token_name, circles):
        #Two Left Holes For KD Shelf
        if token_name == 'Left Drilling':                                   
            normal_z = 1
            org_displacement = 0

            if token.face == '5':
                normal_z = -1
                org_displacement = self.distance(utils.get_part_thickness(assembly.obj_bp))

            param_dict = token.create_parameter_dictionary()
            dim_in_x_1,dim_in_x_2 = param_dict['Par1'].split(",")
            dim_in_y = param_dict['Par7']
            bore_depth,irrelevant = param_dict['Par6'].split(",")
            more_irrelevant,cam_hole_dia = param_dict['Par5'].split(",")                                  

            #Back Left Hole
            cir = {}
            cir['cen_x'] = -float(dim_in_x_2)
            cir['cen_y'] = float(dim_in_y)
            cir['cen_z'] = float(bore_depth)
            cir['diameter'] = unit.meter_to_inch(unit.millimeter(float(cam_hole_dia)))
            cir['normal_z'] = normal_z
            cir['org_displacement'] = org_displacement
            circles.append(cir)

            #Front Left Hole
            cir = {}
            cir['cen_x'] = -float(dim_in_x_1)
            cir['cen_y'] = float(dim_in_y)
            cir['cen_z'] = float(bore_depth)
            cir['diameter'] = unit.meter_to_inch(unit.millimeter(float(cam_hole_dia)))
            cir['normal_z'] = normal_z
            cir['org_displacement'] = org_displacement
            circles.append(cir)


        #Two Right Holes For KD Shelf
        if token_name == 'Right Drilling':                                   
            normal_z = 1
            org_displacement = 0
            if token.face == '5':
                normal_z = -1
                org_displacement = self.distance(utils.get_part_thickness(assembly.obj_bp))

            param_dict = token.create_parameter_dictionary()
            dim_in_x_1,dim_in_x_2 = param_dict['Par1'].split(",")
            dim_in_y = param_dict['Par7']                          
            bore_depth,irrelevant = param_dict['Par6'].split(",")
            more_irrelevant,cam_hole_dia = param_dict['Par5'].split(",")                                   

            #Back Right Hole
            cir = {}
            cir['cen_x'] = -float(dim_in_x_2)
            cir['cen_y'] = float(dim_in_y)
            cir['cen_z'] = float(bore_depth)
            cir['diameter'] = unit.meter_to_inch(unit.millimeter(float(cam_hole_dia)))
            cir['normal_z'] = normal_z
            cir['org_displacement'] = org_displacement
            circles.append(cir)
            
            #Front Right Hole
            cir = {}
            cir['cen_x'] = -float(dim_in_x_1)
            cir['cen_y'] = float(dim_in_y)
            cir['cen_z'] = float(bore_depth)
            cir['diameter'] = unit.meter_to_inch(unit.millimeter(float(cam_hole_dia)))
            cir['normal_z'] = normal_z
            cir['org_displacement'] = org_displacement
            circles.append(cir)


        return circles

    def get_system_hole_drilling(self, assembly, token, circles):
        param_dict = token.create_parameter_dictionary()
        start_dim_x = float(param_dict['Par1'])                                        
        start_dim_y = float(param_dict['Par2'])
        drill_depth = float(param_dict['Par3'])
        bore_dia = unit.meter_to_inch(float(param_dict['Par4']))#Convert to inches
        end_dim_x = float(param_dict['Par5'])
        #end_dim_in_y = float(param_dict['Par6'])
        distance_between_holes = float(param_dict['Par7'])

        normal_z = 1
        org_displacement = 0

        if token.face == '5':
            normal_z = -1
            org_displacement = self.distance(snap_utils.get_part_thickness(assembly.obj_bp))
            start_dim_x = -start_dim_x
            end_dim_x = -end_dim_x                                     

        #First Hole
        cir = {}
        cir['cen_x'] = start_dim_x
        cir['cen_y'] = start_dim_y
        cir['cen_z'] = drill_depth
        cir['diameter'] = bore_dia
        cir['normal_z'] = normal_z
        cir['org_displacement'] = org_displacement
        circles.append(cir)

        x = start_dim_x
    
        #All other holes
        if token.face == '6':
            while x > end_dim_x:
                x -= distance_between_holes
                if x < 0: break
                cir = {}
                cir['cen_x'] = x
                cir['cen_y'] = start_dim_y
                cir['cen_z'] = drill_depth
                cir['diameter'] = bore_dia
                cir['normal_z'] = normal_z
                cir['org_displacement'] = org_displacement
                circles.append(cir)

        if token.face == '5':
            while x < end_dim_x and x < 0:
                x += distance_between_holes
                if x > 0: break
                cir = {}
                cir['cen_x'] = x
                cir['cen_y'] = start_dim_y
                cir['cen_z'] = drill_depth
                cir['diameter'] = bore_dia
                cir['normal_z'] = normal_z
                cir['org_displacement'] = org_displacement
                circles.append(cir)

        return circles

    def get_slide_drilling(self, assembly, token, circles):
        closet_materials = bpy.context.scene.db_materials
        param_dict = token.create_parameter_dictionary()

        slide_type = closet_materials.get_drawer_slide_type()
        slide_size = get_slide_size(slide_type, assembly)
        front_hole_dim_m = unit.millimeter(slide_size.front_hole_dim_mm)
        front_hole_dim_inch = unit.meter_to_inch(front_hole_dim_m)
        back_hole_dim_m = unit.millimeter(slide_size.back_hole_dim_mm)
        back_hole_dim_inch = unit.meter_to_inch(back_hole_dim_m)
        
        dim_from_drawer_bottom = 0.5 # 0.5" should this be added to csv files?
        dim_to_first_hole = front_hole_dim_inch
        dim_to_second_hole = back_hole_dim_inch
        bore_depth_and_dia = param_dict['Par7']
        bore_depth, bore_dia = bore_depth_and_dia.split("|")
        bore_depth_f = float(bore_depth)
        bore_dia_meter = unit.millimeter(float(bore_dia))
        bore_dia_inch = unit.meter_to_inch(bore_dia_meter)

        #Front Hole
        cir = {}
        cir['cen_x'] = dim_to_first_hole
        cir['cen_y'] = dim_from_drawer_bottom
        cir['cen_z'] = bore_depth_f
        cir['diameter'] = bore_dia_inch 
        cir['normal_z'] = 1
        cir['org_displacement'] = 0
        circles.append(cir)

        #Back Hole
        cir = {}
        cir['cen_x'] = dim_to_second_hole
        cir['cen_y'] = dim_from_drawer_bottom
        cir['cen_z'] = bore_depth_f
        cir['diameter'] = bore_dia_inch 
        cir['normal_z'] = 1
        cir['org_displacement'] = 0
        circles.append(cir)

        return circles

    def get_drilling(self, assembly):
        circles = []
        sys_holes = ('System Holes Right Top Front',
            'System Holes Right Top Rear',
            'System Holes Right Bottom Front',
            'System Holes Right Bottom Rear',
            'System Holes Left Top Front',
            'System Holes Left Top Rear',
            'System Holes Left Bottom Front',
            'System Holes Left Bottom Rear',
            'System Holes Mid Left',
            'System Holes Mid Right')        

        for child in assembly.obj_bp.children:
            if child.type == 'MESH':
                tokens = child.mv.mp.machine_tokens
                if len(tokens) > 0:
                    for token in tokens:
                        if not token.is_disabled:
                            token_name = token.name if token.name != "" else "Unnamed"

                            if token_name == "Unnamed":
                                print("Unnamed machine token!")

                            if token.type_token == 'BORE':
                                if token_name in sys_holes:
                                    circles = self.get_system_hole_drilling(assembly, token, circles)

                                if token_name == 'Pull Drilling':
                                    circles = self.get_pull_drilling(assembly, token, circles)

                                if token_name == 'Door Hinge Drilling':
                                    circles = self.get_door_hinge_drilling(assembly, token, circles)                                            

                                if token_name == "Hamper Door Hinge Drilling":
                                    circles = self.get_hamper_door_hinge_drilling(assembly, token, circles)

                                if token_name == 'Shelf and Rod Holes':
                                    print("Found machine token:", token_name)

                            if token.type_token == 'SLIDE':
                                circles = self.get_slide_drilling(assembly, token, circles)

                            if token.type_token == 'CAMLOCK':
                                circles = self.get_shelf_kd_drilling(assembly, token, token_name, circles)

        return circles

    def set_job_number(self):
        dirname = os.path.dirname(bpy.data.filepath).split("\\")[-1]
        filname = "{}.ccp".format(dirname)
        tree = ET.parse(os.path.join(os.path.dirname(bpy.data.filepath), filname))
        root = tree.getroot()
        elm_pinfo = root.find("ProjectInfo")
        project_id = int(elm_pinfo.find("project_id").text)
        proj_user_prefs = bpy.context.user_preferences.addons["fd_projects"].preferences
        designer_id = proj_user_prefs.designer_id
        self.job_number = "{0:0=3d}.{1:0=4d}".format(designer_id, project_id)

    def write_oversize_top_shelf_part(self, node, obj, side=""):
        shelf_length_inch = 97 #96
        closet_materials = bpy.context.scene.db_materials

        for child in obj.children:
            if child.cabinetlib.type_mesh == 'CUTPART':
                obj = child

        if obj.mv.type == 'BPASSEMBLY':
            assembly = fd_types.Assembly(obj)
        else:
            assembly = fd_types.Assembly(obj.parent)

        if assembly.obj_bp.mv.type_group != "PRODUCT":
            elm_part = self.xml.add_element(node,
                'Part',
                {
                    'ID': "IDP-{}".format(self.part_count),
                    'MatID': "IDM-{}".format(self.mat_count),
                    'LabelID': "IDL-{}".format(self.label_count),
                    'OpID': "IDOP-{}".format(self.op_count)
                })

            part_name = assembly.obj_bp.mv.name_object if assembly.obj_bp.mv.name_object != "" else assembly.obj_bp.name
            self.xml.add_element_with_text(elm_part, 'Name', part_name + " Shelf")
            self.xml.add_element_with_text(elm_part,'Quantity', self.get_part_qty(assembly))
            self.xml.add_element_with_text(elm_part,'Width', self.get_part_width(assembly)) 
            self.xml.add_element_with_text(elm_part,'FinishedWidth', self.get_part_width(assembly))           
            self.xml.add_element_with_text(elm_part,'Length', self.distance(unit.inch(shelf_length_inch)))
            self.xml.add_element_with_text(elm_part,'FinishedLength', self.distance(unit.inch(shelf_length_inch)))
            self.xml.add_element_with_text(elm_part,'Thickness',self.distance(snap_utils.get_part_thickness(obj)))
            self.xml.add_element_with_text(elm_part,'FinishedThickness', self.distance(snap_utils.get_part_thickness(obj)))
            self.xml.add_element_with_text(elm_part,'Routing', "SK1")
            self.xml.add_element_with_text(elm_part,'Class', "make")
            self.xml.add_element_with_text(elm_part,'Type', "panel")

            elm_unit = self.xml.add_element(elm_part,'Unit')
            self.xml.add_element_with_text(elm_unit,'Name', "dimension")
            self.xml.add_element_with_text(elm_unit,'Measure', "inch")
            self.xml.add_element_with_text(elm_unit,'RoundFactor', "0")

            #Edgebanding
            carcass_bp = utils.get_parent_assembly_bp(obj)
            carcass_assembly = fd_types.Assembly(carcass_bp)
            l_end_cond = carcass_assembly.get_prompt("Left End Condition").value()
            r_end_cond = carcass_assembly.get_prompt("Right End Condition").value()

            edge_2 = ''
            edge_2_sku = ''

            edge_1 = 'EBF'
            edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)            

            if side == 'Left':
                if l_end_cond == 'EP':
                    edge_2 = 'EBL'
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
            
            if side == 'Right':
                if r_end_cond == 'EP':
                    edge_2 = 'EBR'
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            shelf_x_location = self.get_part_x_location(assembly.obj_bp,assembly.obj_bp.location.x)

            if side == "Right":
                shelf_x_location = str(float(shelf_x_location) + shelf_length_inch)                    

            #Create and add label
            lbl = [("IDL-{}".format(self.label_count), "IDJ-{}".format(self.job_count), "IDP-{}".format(self.part_count)),                
                ("dcname", "text", part_name + " Shelf"),
                ("name", "text", part_name + " Shelf"),
                ("x", "text", shelf_x_location),
                ("y", "text", self.get_part_y_location(assembly.obj_bp,assembly.obj_bp.location.y)),
                ("z", "text", self.get_part_z_location(assembly.obj_bp,assembly.obj_bp.location.z)),
                ("lenx", "text", self.distance(unit.inch(shelf_length_inch))),
                ("leny", "text", self.get_part_width(assembly)),
                ("lenz", "text", self.distance(snap_utils.get_part_thickness(obj))),
                ("rotx", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.x)))),
                ("roty", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.x)))),
                ("rotz", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.x)))),
                ("boml", "text", self.distance(unit.inch(shelf_length_inch))),
                ("bomt", "text",  self.distance(snap_utils.get_part_thickness(obj))),
                ("bomw", "text", self.get_part_width(assembly)),
                ("catnum", "text", self.get_part_comment(assembly.obj_bp)),
                ("sku", "text", closet_materials.get_mat_sku(obj, assembly, part_name)),
                ("cncmirror", "text", ""),
                ("cncrotation", "text", "180"),
                ("cutl", "text", self.distance(unit.inch(shelf_length_inch))),
                ("cutt", "text", self.distance(snap_utils.get_part_thickness(obj))),
                ("cutw", "text", self.get_part_width(assembly)),
                ("edgeband1", "text", edge_1),
                ("edgeband1sku", "text", edge_1_sku),
                ("edgeband2", "text", edge_2),
                ("edgeband2sku", "text", edge_2_sku),
                ("edgeband3", "text", ''),
                ("edgeband3sku", "text", ''),
                ("edgeband4", "text", ''),
                ("edgeband4sku", "text", '')]

            self.labels.append(lbl)
            self.label_count += 1

            #Create and add OperationGroup
            #Get info for segments
            X = self.distance(unit.inch(shelf_length_inch))
            Y = self.get_part_width(assembly)
            Z = self.distance(snap_utils.get_part_thickness(obj))
            W = 0

            upper_right = (X, Y, Z, W)
            upper_left = (0, Y, Z, W)
            lower_left = (0, 0, Z, W)
            lower_right = (X, 0, Z, W)
            circles = []

            op_grp = [("IDOP-{}".format(self.op_count), "IDMOR-{}".format(self.or_count)),
                upper_right,#Segment 1
                upper_left,#Segment 2
                lower_left,#Segment 3
                lower_right,#Segment 4
                circles]

            self.op_groups.append(op_grp)
            self.op_count += 1         
            
            #DEBUG
            if self.debugger:
                self.debugger.write_debug_part(self, assembly, obj, op_grp, lbl, self.part_count)

            self.part_count += 1

    def write_oversize_top_shelf(self, node, obj):
        self.write_oversize_top_shelf_part(node, obj, side="Left")
        self.write_oversize_top_shelf_part(node, obj, side="Right")

    def write_accessory(self, elm, obj_bp, spec_group):
        assembly = fd_types.Assembly(obj_bp)
        sub_name = assembly.obj_bp.mv.name_object if assembly.obj_bp.mv.name_object != "" else assembly.obj_bp.name
        elm_subassembly = self.xml.add_element(elm, "Assembly", {'ID': "IDA-{}".format(self.assembly_count)})
        self.xml.add_element_with_text(elm_subassembly, 'Name', sub_name)
        self.xml.add_element_with_text(elm_subassembly, 'Quantity', "1")

        for child in obj_bp.children:
            if child.cabinetlib.type_mesh in ('HARDWARE', 'BUYOUT'):
                qty = '1'

                try:
                    qty = child.modifiers['Quantity'].count
                except KeyError:
                    print("Writing Closet Accessory '{}'- 'Quantity' modifier not found.".format(obj_bp))

                self.write_hardware_node(elm_subassembly, child, name=child.mv.name_object, qty=str(qty))               

        self.write_parts_for_subassembly(elm_subassembly,assembly.obj_bp,spec_group)          
        self.assembly_count += 1

    def write_products(self,project_node):
        specgroups = bpy.context.scene.mv.spec_groups
        item_name, _ = bpy.path.basename(bpy.data.filepath).split('.')
        room_category_dict = {
            "Please Select":"No Category Found",
            "41110":"Closet",
            "41120":"Entertainment Center",
            "41130":"Garage",
            "41140":"Home Office",
            "41150":"Laundry",
            "41160":"Mud Room",
            "41170":"Pantry",
            "41210":"Kitchen",
            "41220":"Bathroom",
            "41230":"Reface",
            "41240":"Remodel",
            "41250":"Stone"
        }
        if("_" in item_name):
            room_category_num, room_name = item_name.split("_")
            room_category_name = room_category_dict[room_category_num]
        else:
            room_name = item_name 
            room_category_num = "No Category Found"
            room_category_name = "No Category Found"

        existing_items = project_node.findall("Item")

        if existing_items:
            idx = project_node.getchildren().index(existing_items[-1]) + 1
            elm_product = self.xml.insert_element(idx, project_node, 'Item', {'ID': "IDI-{}".format(self.item_count)})
        
        else:
            elm_product = self.xml.add_element(project_node, 'Item', {'ID': "IDI-{}".format(self.item_count)})

        item_number = "{0:0=2d}".format(self.item_count + 1)

        self.xml.add_element_with_text(elm_product,'Name', self.job_number + "." + item_number)
        self.xml.add_element_with_text(elm_product,'Description', room_name)
        #self.xml.add_element_with_text(elm_product,'Room Category',
        #room_category_name)
        #self.xml.add_element_with_text(elm_product,'GL ACCT NUM',
        #room_category_num)
        self.xml.add_element_with_text(elm_product,'Note', room_category_name + ":" + room_category_num)#Str literal OKAY

        for obj_product in self.products:
            spec_group = specgroups[obj_product.cabinetlib.spec_group_index]
            product = fd_types.Assembly(obj_product)

            if obj_product.lm_closets.is_accessory_bp:
                self.write_accessory(elm_product, obj_product, spec_group)
                continue

            #self.write_prompts_for_assembly(elm_product, product)
            self.write_parts_for_product(elm_product,obj_product,spec_group)
            self.write_subassemblies_for_product(elm_product,obj_product,spec_group)
        
        #Add Full Sized Products
        self.write_full_sized_cover_cleat(elm_product,spec_group)
        self.write_full_sized_flat_crown(elm_product,spec_group)
        self.write_full_sized_crown_molding(elm_product,spec_group)
        self.write_full_sized_inverted_base(elm_product,spec_group)
        self.write_full_sized_base_molding(elm_product,spec_group)
        self.write_full_sized_tk_skin(elm_product,spec_group)

        #Add DrawingNum and RoomName Vars
        info = [('DrawingNum', self.job_number + "." + item_number),
                ('RoomName', item_name),]

        for f in info:
            elm_var = self.xml.add_element(elm_product, 'Var')
            self.xml.add_element_with_text(elm_var, 'Name', f[0])
            self.xml.add_element_with_text(elm_var, 'Value', f[1])

        self.item_count += 1

    def write_full_sized_cover_cleat(self,elm_parts,spec_group):
        if self.cover_cleat_bp:
            closet_materials = bpy.context.scene.db_materials
            cover_cleat = fd_types.Assembly(self.cover_cleat_bp)
            mat_sku = closet_materials.get_mat_sku(self.cover_cleat_bp, cover_cleat)
            mat_inventory_name = closet_materials.get_mat_inventory_name(sku=mat_sku)
            total_cover_cleat = 0
            for length in self.cover_cleat_lengths:
                total_cover_cleat += float(length)
            needed_full_lengths = math.ceil((total_cover_cleat / 96) / 2) #96
            if(mat_inventory_name == "Oxford White" or mat_inventory_name == "Cabinet Almond" or mat_inventory_name == "Duraply Almond" or mat_inventory_name == "Duraply White"):
                needed_full_lengths = needed_full_lengths * 2
            if(needed_full_lengths < 3):
                needed_full_lengths += 1
            elif(needed_full_lengths < 6):
                needed_full_lengths += 2
            else:
                needed_full_lengths += 3

            for i in range(0,needed_full_lengths):
                cover_cleat = fd_types.Assembly(self.cover_cleat_bp)
                cover_cleat.obj_x.location.x = unit.inch(96)
                for child in cover_cleat.obj_bp.children:
                    if child.cabinetlib.type_mesh == 'CUTPART':
                        if not child.hide:
                            self.write_part_node(elm_parts, child, spec_group)    

    def write_full_sized_flat_crown(self,elm_parts,spec_group):
        if self.flat_crown_bp:
            flat_crown = fd_types.Assembly(self.flat_crown_bp)

            different_heights = []

            for height in self.flat_crown_heights:
                if not height in different_heights:
                    different_heights.append(height)

            
            for height in different_heights:
                total_flat_crown = 0
                for i in range(len(self.flat_crown_lengths)):
                    if(float(self.flat_crown_heights[i]) == float(height)):
                        total_flat_crown += float(self.flat_crown_lengths[i])

                if(len(self.flat_crown_lengths) == 1 and total_flat_crown < unit.inch(93)):
                    needed_full_lengths = 1
                else:
                    needed_full_lengths = math.ceil((total_flat_crown / 96)) #96
                    if(needed_full_lengths < 4):
                        needed_full_lengths += 1
                    elif(needed_full_lengths < 7):
                        needed_full_lengths += 2
                    else:
                        needed_full_lengths += 3

                for i in range(0,needed_full_lengths):
                    flat_crown.obj_y.location.y = float(unit.inch_to_millimeter(height) / 1000)
                    flat_crown.obj_x.location.x = unit.inch(96)
                    for child in flat_crown.obj_bp.children:
                        if child.cabinetlib.type_mesh == 'CUTPART':
                            if not child.hide:
                                self.write_part_node(elm_parts, child, spec_group)   

    def write_full_sized_crown_molding(self,elm_parts,spec_group):     
        if self.crown_molding_bp:
            crown_molding = fd_types.Assembly(self.crown_molding_bp)
            
            total_crown_molding = 0
            for length in self.crown_molding_lengths:
                total_crown_molding += float(length)

            if(len(self.crown_molding_lengths) == 1 and total_crown_molding < unit.inch(93)):
                needed_full_lengths = 1
            else:
                needed_full_lengths = math.ceil((total_crown_molding / 96)) #96
                if(needed_full_lengths < 4):
                    needed_full_lengths += 1
                elif(needed_full_lengths < 7):
                    needed_full_lengths += 2
                else:
                    needed_full_lengths += 3

            for i in range(0,needed_full_lengths):
                crown_molding = fd_types.Assembly(self.crown_molding_bp)
                crown_molding.obj_x.location.x = unit.inch(96)
                self.write_part_node(elm_parts, crown_molding.obj_bp, spec_group)

    def write_full_sized_inverted_base(self,elm_parts,spec_group):     
        if self.inverted_base_bp:
            inverted_base = fd_types.Assembly(self.inverted_base_bp)
            inverted_base.obj_bp.mv.name_object = "Inverted Base"
            inverted_base.obj_x.location.x = unit.inch(96)
            total_inverted_base = 0
            for length in self.inverted_base_lengths:
                total_inverted_base += float(length)
            if(len(self.inverted_base_lengths) == 1 and total_inverted_base < unit.inch(93)):
                needed_full_lengths = 1
            else:
                needed_full_lengths = math.ceil((total_inverted_base / 96)) #96
                if(needed_full_lengths < 4):
                    needed_full_lengths += 1
                elif(needed_full_lengths < 7):
                    needed_full_lengths += 2
                else:
                    needed_full_lengths += 3

            for i in range(0,needed_full_lengths):
                self.write_part_node(elm_parts, inverted_base.obj_bp, spec_group)

    def write_full_sized_base_molding(self,elm_parts,spec_group):       
        if self.base_molding_bp:
            base_molding = fd_types.Assembly(self.base_molding_bp)
            total_base_molding = 0
            for length in self.base_molding_lengths:
                total_base_molding += float(length)

            if(len(self.base_molding_lengths) == 1 and total_base_molding < unit.inch(93)):
                needed_full_lengths = 1
            else:
                needed_full_lengths = math.ceil((total_base_molding / 96)) #96
                if(needed_full_lengths < 4):
                    needed_full_lengths += 1
                elif(needed_full_lengths < 7):
                    needed_full_lengths += 2
                else:
                    needed_full_lengths += 3

            for i in range(0,needed_full_lengths):
                base_molding = fd_types.Assembly(self.base_molding_bp)
                base_molding.obj_x.location.x = unit.inch(96)
                self.write_part_node(elm_parts, base_molding.obj_bp, spec_group)   

    def write_full_sized_tk_skin(self,elm_parts,spec_group):
        if self.tk_skin_bp:
            tk_skin = fd_types.Assembly(self.tk_skin_bp)

            different_heights = []

            for height in self.tk_skin_heights:
                if not height in different_heights:
                    different_heights.append(height)

            
            for height in different_heights:
                total_tk_skin = 0
                for i in range (len(self.tk_skin_lengths)):
                    if(float(self.tk_skin_heights[i]) == float(height)):
                        total_tk_skin += float(self.tk_skin_lengths[i])
                if(len(self.tk_skin_lengths)==1 and total_tk_skin < 93):
                    needed_full_lengths = 1
                elif(total_tk_skin < 80):
                    needed_full_lengths = 1
                else:
                    needed_full_lengths = math.ceil((total_tk_skin/96)) #96
                    if(needed_full_lengths < 4):
                        needed_full_lengths += 1
                    else:
                        needed_full_lengths += 2

                for i in range(0,needed_full_lengths):
                    tk_skin.obj_x.location.x = unit.inch(96)
                    tk_skin.obj_y.location.y = float(unit.inch_to_millimeter(float(height)) / 1000)+unit.inch(1)
                    tk_skin.obj_z.location.z = unit.inch(0.25)
                    for child in tk_skin.obj_bp.children:
                        if child.cabinetlib.type_mesh == 'CUTPART':
                            if not child.hide:
                                self.write_part_node(elm_parts, child, spec_group)   

    def write_parts_for_product(self,elm_parts,obj_bp,spec_group,recursive=False):
        for child in obj_bp.children:
            #Write part nodes for cleat and append cover cleat length to
            #cover_cleat_lengths
            if child.lm_closets.is_cleat_bp:
                for nchild in child.children:
                    if nchild.cabinetlib.type_mesh == 'CUTPART':
                        if not nchild.hide:
                            self.write_part_node(elm_parts, nchild, spec_group)

                    if nchild.lm_closets.is_cleat_bp:
                        for nnchild in nchild.children:
                            if nnchild.cabinetlib.type_mesh == 'CUTPART':
                                if not nnchild.hide:
                                    #If it is an unhidden cover cleat cutpart,
                                    #add it's length to cover_cleat_lengths
                                    cover_cleat_assembly = fd_types.Assembly(nnchild.parent)
                                    self.cover_cleat_bp = cover_cleat_assembly.obj_bp
                                    self.cover_cleat_lengths.append(self.get_part_length(cover_cleat_assembly))
                continue
            if child.lm_closets.is_crown_molding or child.lm_closets.is_base_molding:
                if(child.lm_closets.is_empty_molding):
                    if(child.lm_closets.is_crown_molding):
                        crown_molding_assembly = fd_types.Assembly(child)
                        length = self.get_part_length(crown_molding_assembly)
                        crown_to_ceiling = crown_molding_assembly.get_prompt("Crown To Ceiling").value()
                        self.crown_molding_bp = crown_molding_assembly.obj_bp
                        self.crown_molding_lengths.append(length)
                        if(crown_to_ceiling):
                            self.inverted_base_bp = crown_molding_assembly.obj_bp
                            self.inverted_base_lengths.append(length)
                    elif(child.lm_closets.is_base_molding):
                        base_molding_assembly = fd_types.Assembly(child)
                        self.base_molding_bp = child
                        self.base_molding_lengths.append(self.get_part_length(base_molding_assembly))
                else:
                    for nchild in child.children:
                        for nnchild in nchild.children:
                            if nnchild.cabinetlib.type_mesh == 'CUTPART':
                                if not nnchild.hide:
                                    if(nchild.lm_closets.is_flat_crown_bp):
                                        flat_crown_assembly = fd_types.Assembly(nnchild.parent)
                                        p_flat_crown_assembly = fd_types.Assembly(flat_crown_assembly.obj_bp.parent)
                                        EL = flat_crown_assembly.get_prompt("Exposed Left").value()
                                        ER = flat_crown_assembly.get_prompt("Exposed Right").value()
                                        EB = flat_crown_assembly.get_prompt("Exposed Back").value()
                                        var_height = p_flat_crown_assembly.get_prompt("Extend To Ceiling")
                                        length = self.get_part_length(flat_crown_assembly)
                                        height = float(self.get_part_width(flat_crown_assembly))
                                        if var_height:
                                            if var_height.value():
                                                height = height + 2
                                        if(not EL and not ER):
                                            self.flat_crown_heights.append(height)
                                        if(EL and ER):
                                            if(float(length) > 96):
                                                flat_crown_assembly.get_prompt("Exposed Left").set_value(False)
                                                flat_crown_assembly.get_prompt("Exposed Right").set_value(False)
                                                if(flat_crown_assembly.obj_bp.mv.name_object != "Right" and flat_crown_assembly.obj_bp.mv.name_object != "Left"):
                                                    self.flat_crown_bp = flat_crown_assembly.obj_bp
                                                number_of_lengths = math.ceil(length / 96)
                                                if(number_of_lengths == 2):
                                                    self.single_exposed_flat_crown.append(True)
                                                    self.single_exposed_flat_crown.append(True)
                                                    if(EB):
                                                        self.top_edgebanded_flat_crown.append(True)
                                                        self.top_edgebanded_flat_crown.append(True)
                                                    self.flat_crown_lengths.append(unit.inch(96))
                                                    self.flat_crown_lengths.append(unit.inch(96))
                                                    self.flat_crown_heights.append(height)
                                                else:
                                                    self.single_exposed_flat_crown.append(True)
                                                    self.single_exposed_flat_crown.append(True)
                                                    if(EB):
                                                        self.top_edgebanded_flat_crown.append(True)
                                                        self.top_edgebanded_flat_crown.append(True)
                                                    self.flat_crown_lengths.append(unit.inch(96))
                                                    self.flat_crown_lengths.append(unit.inch(96))
                                                    self.flat_crown_heights.append(height)
                                                    number_of_lengths = number_of_lengths - 2
                                                    for x in range(number_of_lengths):
                                                        if(EB):
                                                            self.top_edgebanded_flat_crown.append(True)
                                                        self.flat_crown_lengths.append(unit.inch(96))
                                                        self.flat_crown_heights.append(height)
                                            else:
                                                self.write_part_node(elm_parts, nnchild, spec_group)
                                        elif((EL and not ER) or (not EL and ER)):
                                            if(flat_crown_assembly.obj_bp.mv.name_object != "Right" and flat_crown_assembly.obj_bp.mv.name_object != "Left"):
                                                self.flat_crown_bp = flat_crown_assembly.obj_bp
                                            self.single_exposed_flat_crown.append(True)
                                            if(EB):
                                                self.top_edgebanded_flat_crown.append(True)
                                            self.flat_crown_lengths.append(self.get_part_length(flat_crown_assembly))
                                            self.flat_crown_heights.append(height)
                                        else:
                                            if(flat_crown_assembly.obj_bp.mv.name_object != "Right" and flat_crown_assembly.obj_bp.mv.name_object != "Left"):
                                                self.flat_crown_bp = flat_crown_assembly.obj_bp
                                            if(EB):
                                                self.top_edgebanded_flat_crown.append(True)
                                            self.flat_crown_lengths.append(self.get_part_length(flat_crown_assembly)) 
                    print()
                    continue

            if(child.lm_closets.is_toe_kick_skin_bp):
                for nchild in child.children:
                    if nchild.cabinetlib.type_mesh == 'CUTPART':
                        if not nchild.hide:
                            tk_skin_assembly = fd_types.Assembly(child)
                            if tk_skin_assembly.obj_bp.mv.name_object == "Toe Kick Skin":
                                self.tk_skin_bp = tk_skin_assembly.obj_bp
                            self.tk_skin_lengths.append(self.get_part_length(tk_skin_assembly))

                            height = float(self.get_part_width(tk_skin_assembly))
                            tk_assembly = fd_types.Assembly(child.parent)
                            var_height = tk_assembly.get_prompt("Variable Height")
                            if var_height:
                                if var_height.value():
                                    height += 2
                            self.tk_skin_heights.append(str(height)) 
                continue

            for nchild in child.children:

                if nchild.cabinetlib.type_mesh == 'HARDWARE':
                    if not nchild.hide:
                        self.write_hardware_node(elm_parts, nchild)

                if nchild.cabinetlib.type_mesh in {'CUTPART','SOLIDSTOCK','BUYOUT'}:
                    if not nchild.hide:
                        self.write_part_node(elm_parts, nchild, spec_group)

                        if nchild.cabinetlib.type_mesh == 'CUTPART':
                            #self.op_groups.append("IDOP-{}".format(self.op_count))
                            #self.op_count += 1
                            pass

                        if nchild.cabinetlib.type_mesh == 'SOLIDSTOCK':
                            #Solid Stock op_groups here
                            #print("TODO: SOLIDSTOCK OPERATION GROUPS")
                            pass

                        if nchild.cabinetlib.type_mesh == 'BUYOUT':
                            #Buyout op_groups here
                            print("write_parts_for_product BUYOUT", child)
                            pass                            

            if recursive:
                self.write_parts_for_product(elm_parts, child, spec_group, recursive=recursive)
            
    def get_subassemblies(self, obj_bp, subassemblies=None):
        if subassemblies is None:
            subassemblies = []

        for child in obj_bp.children:
            if child.mv.type == 'BPASSEMBLY' and child.mv.type_group == 'INSERT':
                assembly = fd_types.Assembly(child)

                if child.mv.export_as_subassembly:
                    assembly = fd_types.Assembly(child)
                    hide = assembly.get_prompt("Hide")
                    if hide:
                        if hide.value():
                            continue
                    subassemblies.append(assembly)

                self.get_subassemblies(assembly.obj_bp, subassemblies)

        return subassemblies

    def write_subassemblies_for_product(self, elm_product, obj_bp, spec_group, subassemblies=None):
        if subassemblies is None:
            subassemblies = self.get_subassemblies(obj_bp)
        
        for assembly in subassemblies:
            sub_name = assembly.obj_bp.mv.name_object if assembly.obj_bp.mv.name_object != "" else assembly.obj_bp.name
            elm_subassembly = self.xml.add_element(elm_product, "Assembly", {'ID': "IDA-{}".format(self.assembly_count)})
            self.xml.add_element_with_text(elm_subassembly, 'Name', sub_name)
            self.xml.add_element_with_text(elm_subassembly, 'Quantity', "1")

            if sub_name == "Top Shelf":
                for child in assembly.obj_bp.children:
                    if child.lm_closets.is_plant_on_top_bp:
                        top_shelf_assembly = fd_types.Assembly(child)
                        if top_shelf_assembly.obj_x.location.x > unit.inch(97):  
                            self.write_oversize_top_shelf(elm_subassembly, child)
                            self.assembly_count += 1
                            return

            self.write_parts_for_subassembly(elm_subassembly, assembly.obj_bp, spec_group)
            self.assembly_count += 1

            is_drawer_stack = assembly.obj_bp.lm_closets.is_drawer_stack_bp
            export_nested = assembly.obj_bp.lm_closets.export_nested_subassemblies

            if is_drawer_stack or export_nested:
                self.write_nested_subassemblies(elm_subassembly, assembly.obj_bp, spec_group)

            if assembly.obj_bp.lm_closets.is_hamper_insert_bp:
                hamper_type = assembly.get_prompt("Hamper Type").value()
                self.write_hardware_node(elm_subassembly, obj_bp, name="Hamper Brake Flap Left")
                self.write_hardware_node(elm_subassembly, obj_bp, name="Hamper Brake Flap Right")
                self.write_hardware_node(elm_subassembly, obj_bp, name="Hamper Rack")

                if hamper_type == 'Canvas':           
                    self.write_hardware_node(elm_subassembly, obj_bp, name="Cloth Laundry Bag")
            
    def write_nested_subassemblies(self,elm_subassembly, obj_bp, spec_group):
        for child in obj_bp.children:
            if child.mv.export_as_subassembly and child.lm_closets.is_drawer_box_bp:
                assembly = fd_types.Assembly(child)
                hide = assembly.get_prompt("Hide")
                if hide:
                    if hide.value():
                        continue
                sub_name = assembly.obj_bp.mv.name_object if assembly.obj_bp.mv.name_object != "" else assembly.obj_bp.name
                elm_item = self.xml.add_element(elm_subassembly, 'Assembly', {'ID': "IDA-{}".format(self.assembly_count)})
                self.xml.add_element_with_text(elm_item, 'Name', sub_name)
                self.xml.add_element_with_text(elm_item, 'Quantity', "1")
                self.write_parts_for_subassembly(elm_item, assembly.obj_bp, spec_group)
                self.assembly_count += 1

    def write_parts_for_subassembly(self, elm_parts, obj_bp, spec_group):
        #Slides
        if obj_bp.lm_closets.is_drawer_box_bp:
            self.write_hardware_node(elm_parts, obj_bp, name="Drawer Slide L")
            self.write_hardware_node(elm_parts, obj_bp, name="Drawer Slide R")

        #Locked shelf - add KD fittings (4)
        if obj_bp.lm_closets.is_shelf_bp:
            assembly = fd_types.Assembly(obj_bp)
            is_locked_shelf = assembly.get_prompt("Is Locked Shelf").value()

            if is_locked_shelf:
                self.write_hardware_node(elm_parts, obj_bp, name="KD Fitting",qty=4)

        #Door lock for doors
        if obj_bp.lm_closets.is_door_insert_bp:
            door_insert = fd_types.Assembly(obj_bp)
            lock_door = door_insert.get_prompt("Lock Door").value()
            double_door_auto_switch = door_insert.get_prompt("Double Door Auto Switch").value()
            double_door = door_insert.get_prompt("Force Double Doors").value()

            if lock_door:
                self.write_hardware_node(elm_parts, obj_bp, name="Door Lock")
                self.write_hardware_node(elm_parts, obj_bp, name="Door Lock Cam")

                #Double door
                if double_door or door_insert.obj_x.location.x > double_door_auto_switch:
                    self.write_hardware_node(elm_parts, obj_bp, name="Door Lock Latch")               

        for child in obj_bp.children:
            if(child.lm_closets.is_toe_kick_skin_bp):
                for nchild in child.children:
                    if nchild.cabinetlib.type_mesh == 'CUTPART':
                        if not nchild.hide:
                            tk_skin_assembly = fd_types.Assembly(child)
                            if tk_skin_assembly.obj_bp.mv.name_object == "Toe Kick Skin":
                                self.tk_skin_bp = tk_skin_assembly.obj_bp
                            self.tk_skin_lengths.append(self.get_part_length(tk_skin_assembly))

                            height = float(self.get_part_width(tk_skin_assembly))
                            tk_assembly = fd_types.Assembly(child.parent)
                            var_height = tk_assembly.get_prompt("Variable Height")
                            if var_height:
                                if var_height.value():
                                    height += 2
                            self.tk_skin_heights.append(str(height))
                    
                continue
            if child.lm_closets.is_hanging_rod:
                for nchild in child.children:
                    if not nchild.hide:
                        self.write_hardware_node(elm_parts, obj_bp, name="Pole Cup")
                        self.write_hardware_node(elm_parts, obj_bp, name="Pole Cup")  

            for nchild in child.children:

                if nchild.cabinetlib.type_mesh == 'HARDWARE':
                    if not nchild.hide:
                        self.write_hardware_node(elm_parts, nchild)

                if nchild.cabinetlib.type_mesh in {'CUTPART','SOLIDSTOCK','BUYOUT'}:
                    if not nchild.hide:
                        self.write_part_node(elm_parts, nchild, spec_group)

                        if nchild.cabinetlib.type_mesh == 'CUTPART':
                            #self.op_groups.append("IDOP-{}".format(self.op_count))
                            #self.op_count += 1
                            pass                 

                        if nchild.cabinetlib.type_mesh == 'SOLIDSTOCK':
                            #Solid Stock op_groups here
                            #print("TODO: SOLIDSTOCK OPERATION GROUPS")
                            pass

                        if nchild.cabinetlib.type_mesh == 'BUYOUT':
                            #Buyout op_groups here
                            print("write_parts_for_subassembly BUYOUT", child)
                            pass                                   

    def write_parts_for_nested_subassembly(self,elm_parts,obj_bp,spec_group):
        for child in obj_bp.children:

            if child.cabinetlib.type_mesh == 'HARDWARE':
                if not child.hide:
                    self.write_hardware_node(elm_parts, child)

            if child.cabinetlib.type_mesh in {'CUTPART','SOLIDSTOCK','BUYOUT'}:
                if not child.hide:
                    self.write_part_node(elm_parts, child, spec_group)

                    if child.cabinetlib.type_mesh == 'CUTPART':
                        #self.op_groups.append("IDOP-{}".format(self.op_count))
                        #self.op_count += 1
                        pass                    

                    if child.cabinetlib.type_mesh == 'SOLIDSTOCK':
                        #Solid Stock op_groups here
                        #print("TODO: SOLIDSTOCK OPERATION GROUPS")
                        pass

                    if child.cabinetlib.type_mesh == 'BUYOUT':
                        #Buyout op_groups here
                        print("write_parts_for_subassembly BUYOUT", child)

                        pass                        

    def write_prompts_for_assembly(self,elm_prompts,assembly):
        prompts_dict = get_export_prompts(assembly.obj_bp)
        for prompt in prompts_dict:
            elm_prompt = self.xml.add_element(elm_prompts,'Prompt',{'Name': prompt})
            prompt_value = prompts_dict[prompt]
            if prompt_value == 'True':
                prompt_value = str(1)
            if prompt_value == 'False':
                prompt_value = str(0)
            self.xml.add_element_with_text(elm_prompt,'Value',prompt_value)

        #HEIGHT ABOVE FLOOR FOR PRODUCT IS OVERRIDDEN BY THE Z ORIGIN
        if assembly.obj_bp.mv.type_group == 'PRODUCT':
            if assembly.obj_bp.location.z > 0:
                elm_prompt = self.xml.add_element(elm_prompts,'Prompt',"HeightAboveFloor")
                self.xml.add_element_with_text(elm_prompt,'Value',"0")                  
    
    def write_hardware_node(self, elm_product, obj_bp, name="", qty=1):
        if obj_bp.mv.type == 'BPASSEMBLY':
            assembly = fd_types.Assembly(obj_bp)
        else:
            assembly = fd_types.Assembly(obj_bp.parent)

        if name != "":
            hardware_name = name
        
        else:
            hardware_name = obj_bp.mv.name_object if obj_bp.mv.name_object != "" else obj_bp.name
        
        elm_hdw_part = self.xml.add_element(elm_product,
                                        'Part',
                                        {'ID': "IDP-{}".format(self.part_count),
                                        'LabelID': "IDL-{}".format(self.label_count)                          
                                        })
        
        self.xml.add_element_with_text(elm_hdw_part, 'Name', hardware_name)
        self.xml.add_element_with_text(elm_hdw_part, 'Quantity', str(qty))
        self.xml.add_element_with_text(elm_hdw_part, 'Routing', "HDSTK")#Str literal OKAY
        self.xml.add_element_with_text(elm_hdw_part, 'Type', "hardware")#Str literal OKAY

        lbl = [("IDL-{}".format(self.label_count), "IDJ-{}".format(self.job_count), "IDP-{}".format(self.part_count)),
            ("name", "text", hardware_name),
            ("x", "text", "0"),
            ("y", "text", "0"),
            ("z", "text", "0"),
            ("lenx", "text", "0"),
            ("leny", "text", "0"),
            ("lenz", "text", "0"),
            ("rotx", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.x)))),
            ("roty", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.y)))),
            ("rotz", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.z)))),
            ("material", "text", ""),#Str literal OKAY
            ("copies", "text", ""),#Str literal OKAY
            ("sku", "text", get_hardware_sku(obj_bp, assembly, hardware_name)),#Get sku value from Database
            ("color", "text", ""),#Str literal OKAY
            ("type", "text", "hardware")#Str literal OKAY
        ]

        self.labels.append(lbl)
        self.label_count += 1
        self.part_count += 1

    def write_part_node(self,node,obj,spec_group):
        if obj.mv.type == 'BPASSEMBLY':
            assembly = fd_types.Assembly(obj)
        else:
            assembly = fd_types.Assembly(obj.parent)
        if assembly.obj_bp.mv.type_group != "PRODUCT":

            obj_props = assembly.obj_bp.lm_closets
            closet_materials = bpy.context.scene.db_materials

            if obj_props.is_shelf_bp or obj_props.is_glass_shelf_bp:
                    is_locked_shelf = assembly.get_prompt("Is Locked Shelf")
                    shelf_qty = 1

                    for child in assembly.obj_bp.children:
                        if child.cabinetlib.type_mesh in ('CUTPART', 'BUYOUT'):
                            try:
                                shelf_qty = child.modifiers['ZQuantity'].count
                            except KeyError:
                                print("Writing Shelf Part - 'ZQuantity' modifier not found.")            

                    for _ in range(shelf_qty):
                        if is_locked_shelf and is_locked_shelf.value() == True:
                            self.write_hardware_node(node, assembly.obj_bp, name="KD Fitting", qty=4)

                        else:
                            self.write_hardware_node(node, assembly.obj_bp, name="Peg Chrome", qty=4)

            #----------Add part name
            if obj.type == 'CURVE':
                part_name = obj.mv.name_object if obj.mv.name_object != "" else obj.name
            else:
                part_name = assembly.obj_bp.mv.name_object if assembly.obj_bp.mv.name_object != "" else assembly.obj_bp.name

                is_locked_shelf = assembly.get_prompt("Is Locked Shelf")                

                #TODO: This is for old lib data, correct part names now set on
                #assembly creation
                if part_name == "Panel":
                    part_name = "Partition"
                if part_name == "Top":
                    part_name = "Top Shelf"
                if is_locked_shelf and is_locked_shelf.value() == True:
                    part_name = "KD Shelf"
                if part_name == "Shelf" :
                    part_name = "Adj Shelf"                    
            
            mat_sku = closet_materials.get_mat_sku(obj, assembly)
            mat_inventory_name = closet_materials.get_mat_inventory_name(sku=mat_sku)
            if part_name == "Cover Cleat":
                if mat_inventory_name == "Oxford White" or mat_inventory_name == "Duraply White":
                    mat_sku = "PM-0000001"
                elif mat_inventory_name == "Cabinet Almond" or mat_inventory_name == "Duraply Almond":
                    mat_sku = "PM-0000002"
            if(part_name == "File Rail"):
                    mat_inventory_name = "White Paper 12310"
                    mat_sku = "PM-0000004"
            if obj_props.is_countertop_bp:
                l_assembly_end_cond = assembly.get_prompt("Exposed Left")
                r_assembly_end_cond = assembly.get_prompt("Exposed Right")

                if l_assembly_end_cond and l_assembly_end_cond.value != True:
                        assembly.obj_x.location.x += unit.inch(3)
                if r_assembly_end_cond and r_assembly_end_cond.value() != True:
                    assembly.obj_x.location.x += unit.inch(3)
            if(part_name == "Inverted Base"):
                mat_inventory_name = "BASE ALDER 3 1/4X1/2 WM633"
                mat_sku = "MD-0000025"

            mat_id = self.write_material(mat_inventory_name, mat_sku)

            elm_part = self.xml.add_element(node,
                'Part',
                {
                    'ID': "IDP-{}".format(self.part_count),
                    'MatID': "IDM-{}".format(mat_id),
                    'LabelID': "IDL-{}".format(self.label_count),
                    'OpID': "IDOP-{}".format(self.op_count)
                })

            self.xml.add_element_with_text(elm_part, 'Name', part_name)

            if(obj_props.is_door_bp or obj_props.is_drawer_front_bp):
                if(assembly.get_prompt("Door Style")):
                    door_style = assembly.get_prompt("Door Style").value()
                    glaze_color = closet_materials.get_glaze_color().name
                    glaze_style = closet_materials.get_glaze_style().name

                    parent_assembly = fd_types.Assembly(obj.parent.parent)
                    has_center_rail = parent_assembly.get_prompt("Has Center Rail")
                    center_rail_distance_from_center = parent_assembly.get_prompt("Center Rail Distance From Center")                    
                    prompts = [door_style,has_center_rail,center_rail_distance_from_center]
                    
                    if(door_style != "Slab Door"):
                        self.xml.add_element_with_text(elm_part,'Style', door_style)
                        self.xml.add_element_with_text(elm_part,'GlazeColor', str(glaze_color))
                        self.xml.add_element_with_text(elm_part,'GlazeStyle', str(glaze_style))
                        if all(prompts) and (has_center_rail.value()):
                            self.xml.add_element_with_text(elm_part,'CenterRail', 'Yes')
                            self.xml.add_element_with_text(elm_part,'CenterRailDistanceFromCenter', str(unit.meter_to_inch(center_rail_distance_from_center.value())))
                        else:
                            self.xml.add_element_with_text(elm_part,'CenterRail', 'No')

            self.xml.add_element_with_text(elm_part,'Quantity', self.get_part_qty(assembly))
            self.xml.add_element_with_text(elm_part,'Width', self.get_part_width(assembly)) 
            self.xml.add_element_with_text(elm_part,'FinishedWidth', self.get_part_width(assembly))           
            self.xml.add_element_with_text(elm_part,'Length', self.get_part_length(assembly))
            self.xml.add_element_with_text(elm_part,'FinishedLength', self.get_part_length(assembly))
            self.xml.add_element_with_text(elm_part,'Thickness',self.distance(snap_utils.get_part_thickness(obj)))
            self.xml.add_element_with_text(elm_part,'FinishedThickness', self.distance(snap_utils.get_part_thickness(obj)))
            self.xml.add_element_with_text(elm_part,'Routing', "SK1")#Str literal okay
            if(part_name == "Cover Cleat"):
                if(mat_inventory_name == "Oxford White" or mat_inventory_name == "Cabinet Almond" or mat_inventory_name == "Duraply Almond" or mat_inventory_name == "Duraply White"):
                    self.xml.add_element_with_text(elm_part,'Class', "draw")#Str literal okay
                else:
                    self.xml.add_element_with_text(elm_part,'Class', "make")#Str literal okay
            else:
                self.xml.add_element_with_text(elm_part,'Class', "make")#Str literal okay
            self.xml.add_element_with_text(elm_part,'Type', "panel")#"panel" for part "unknown" for solid stock

            elm_unit = self.xml.add_element(elm_part,'Unit')
            self.xml.add_element_with_text(elm_unit,'Name', "dimension")#Str literal okay
            self.xml.add_element_with_text(elm_unit,'Measure', "inch")#Str literal okay
            self.xml.add_element_with_text(elm_unit,'RoundFactor', "0")#Str literal okay

            obj_props = assembly.obj_bp.lm_closets
            closet_materials = bpy.context.scene.db_materials

            #EDGEBANDING
            edge_1 = ''
            edge_2 = ''
            edge_3 = ''
            edge_4 = ''
            edge_1_sku = ''
            edge_2_sku = ''
            edge_3_sku = ''
            edge_4_sku = ''

            edge_color = closet_materials.edges.get_edge_color()
            secondary_edge_color = closet_materials.secondary_edges.get_edge_color()
            door_drawer_edge_color = closet_materials.door_drawer_edges.get_edge_color()

            if obj_props.is_cleat_bp:
                edge_1_color_name = secondary_edge_color.name
                edge_2_color_name = secondary_edge_color.name
                edge_3_color_name = secondary_edge_color.name
                edge_4_color_name = secondary_edge_color.name
            elif obj_props.is_door_bp or obj_props.is_drawer_front_bp:
                edge_1_color_name = door_drawer_edge_color.name
                edge_2_color_name = door_drawer_edge_color.name
                edge_3_color_name = door_drawer_edge_color.name
                edge_4_color_name = door_drawer_edge_color.name
            else:
                edge_1_color_name = edge_color.name
                edge_2_color_name = edge_color.name
                edge_3_color_name = edge_color.name
                edge_4_color_name = edge_color.name

            #Doors
            if obj_props.is_door_bp or obj_props.is_hamper_front_bp:
                if(abs(assembly.obj_x.location.x) < abs(assembly.obj_y.location.y)):
                    edge_1 = "L1"
                    edge_2 = "S1"
                    edge_3 = "L2"
                    edge_4 = "S2"
                else:
                    edge_1 = "S1"
                    edge_2 = "L1"
                    edge_3 = "S2"
                    edge_4 = "L2"
                edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            #Panel, Shelf
            if obj_props.is_panel_bp or obj_props.is_shelf_bp:
                #If the Panels/Shelves are attached to an Island
                if(obj.parent.parent and obj.parent.parent.lm_closets.is_island and fd_types.Assembly(obj.parent.parent).get_prompt("Depth 2")):
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_2 = "L1"
                        edge_4 = "L2"
                    else:
                        edge_2 = "S1"
                        edge_4 = "S2"
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                else:
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_2 = "L1"
                    else:
                        edge_2 = "S1"
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    exposed_bottom = assembly.get_prompt("Exposed Bottom")
                    if exposed_bottom:
                        if exposed_bottom.value() or assembly.obj_x.location.x <= unit.inch(46.10):
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_1 = "S1"
                                edge_3 = "S2"
                            else:
                                edge_1 = "L1"
                                edge_3 = "L2"
                            edge_1_sku = closet_materials.get_secondary_edge_sku(obj, assembly, part_name)
                            edge_3_sku = closet_materials.get_secondary_edge_sku(obj, assembly, part_name)
                            edge_1_color_name = secondary_edge_color.name
                            edge_3_color_name = secondary_edge_color.name

            #Blind Corner Panels
            if obj_props.is_blind_corner_panel_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_1 = "S1"
                    edge_2 = "L1"
                    edge_3 = "S2"
                else:
                    edge_1 = "L1"
                    edge_2 = "S1"
                    edge_3 = "L2"
                edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)    
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            #Drawers
            if obj_props.is_drawer_front_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_1 = "L1"
                    edge_2 = "S1"
                    edge_3 = "L2"
                    edge_4 = "S2"
                else:
                    edge_1 = "S1"
                    edge_2 = "L1"
                    edge_3 = "S2"
                    edge_4 = "L2"
                edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)    
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)                            

            if obj_props.is_drawer_sub_front_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_2 = "L1"
                else:
                    edge_2 = "S1"
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name) 

            if obj_props.is_drawer_side_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_2 = "S1"
                else:
                    edge_2 = "L1"
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name) 

            if obj_props.is_drawer_back_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_2 = "L1"
                else:
                    edge_2 = "S1"
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name) 
            
            if obj_props.is_file_rail_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_2 = "S1"
                else:
                    edge_2 = "L1"
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            #Cleats
            if obj_props.is_cleat_bp:
                if obj_props.is_cover_cleat_bp:                                    
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_2 = "L1"
                    else:
                        edge_2 = "S1"
                    if(mat_inventory_name == "Oxford White" or mat_inventory_name == "Duraply White"):
                        edge_2_sku = "EB-0000314"
                    elif(mat_inventory_name == "Cabinet Almond" or mat_inventory_name == "Duraply Almond"):
                        edge_2_sku = "EB-0000315"
                    else:
                        edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                elif obj_props.is_wall_cleat_bp:
                    #Wall Cleat
                    exposed_left = assembly.get_prompt('Exposed Left')
                    exposed_top = assembly.get_prompt('Exposed Top')
                    exposed_right = assembly.get_prompt('Exposed Right')
                    exposed_bottom = assembly.get_prompt('Exposed Bottom')
                    edgebanding_prompts = [exposed_left,exposed_top,exposed_right,exposed_bottom]
                    if all(edgebanding_prompts):
                        if(abs(assembly.obj_x.location.x)<abs(assembly.obj_y.location.y)):
                            if exposed_left.value():
                                edge_1 ="L1"
                                edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                                if exposed_right.value():
                                    edge_3 ="L2"
                                    edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                            elif exposed_right.value():
                                edge_3 ="L1"
                                edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name) 
                            
                            if exposed_top.value():
                                edge_2 ="S1"
                                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                                if exposed_bottom.value():
                                    edge_4 ="S2"
                                    edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                            elif exposed_bottom.value():
                                edge_4 ="S1"        
                        else:
                            if exposed_left.value():
                                edge_1 ="S1"
                                edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                                if exposed_right.value():
                                    edge_3 ="S2"
                                    edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                            elif exposed_right.value():
                                edge_3 ="S1"
                                edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name) 
                            
                            if exposed_top.value():
                                edge_2 ="L1"
                                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                                if exposed_bottom.value():
                                    edge_4 ="L2"
                                    edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                            elif exposed_bottom.value():
                                edge_4 ="L1"        
    
                    else:   
                        if(abs(assembly.obj_x.location.x)<abs(assembly.obj_y.location.y)):
                            edge_1 = "L1"
                            edge_2 = "S1"
                            edge_3 = "L2"
                            edge_4 = "S2"
                        else:
                            edge_1 = "S1"
                            edge_2 = "L1"
                            edge_3 = "S2"
                            edge_4 = "L2"
                        edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                else:
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_2 = "L1"
                    else:
                        edge_2 = "S1"
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            #Door striker
            if  obj_props.is_door_striker_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_2 = "L1"
                else:
                    edge_2 = "S1"
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)                

            #L Shelf
            if obj_props.is_l_shelf_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_1 = "L1"
                    edge_2 = "L1"
                else:
                    edge_2 = "S1"
                    edge_2 = "S1"
                edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)                
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)                

            #Shelf lip
            if obj_props.is_shelf_lip_bp:
                if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                    edge_2 = "L1"
                else:
                    edge_2 = "S1"
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name) 

            #Top shelf
            if obj_props.is_plant_on_top_bp:
                if(assembly.get_prompt("Is Counter Top").value() == False):
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_2 = "L1"
                    else:
                        edge_2 = "S1"
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    
                    carcass_bp = utils.get_parent_assembly_bp(obj)
                    carcass_assembly = fd_types.Assembly(carcass_bp)
                    l_carcass_end_cond = carcass_assembly.get_prompt("Left End Condition").value()
                    r_carcass_end_cond = carcass_assembly.get_prompt("Right End Condition").value()
                    l_assembly_end_cond = assembly.get_prompt("Exposed Left").value()
                    r_assembly_end_cond = assembly.get_prompt("Exposed Right").value()
                    b_assembly_end_cond = assembly.get_prompt("Exposed Back").value()
                    if (l_carcass_end_cond == 'EP' and r_carcass_end_cond != 'EP') or (l_assembly_end_cond == True and r_assembly_end_cond != True):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_1 = "S1"
                        else:
                            edge_1 = "L1"
                        edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)                  

                    if (l_carcass_end_cond != 'EP' and r_carcass_end_cond == 'EP') or (l_assembly_end_cond != True and r_assembly_end_cond == True):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_3 = "S2"
                        else:
                            edge_3 = "L2"
                        edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

                    if (l_carcass_end_cond == 'EP' and r_carcass_end_cond == 'EP') or (l_assembly_end_cond == True and r_assembly_end_cond == True):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_1 = "S1"
                            edge_3 = "S2"
                        else:
                            edge_1 = "L1"
                            edge_3 = "L2"
                        edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    
                    if(b_assembly_end_cond):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_4 = "L2"
                        else:
                            edge_4 = "S2"
                        edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            #Edge Bottom Of Filler
            if obj_props.is_filler_bp:
                carcass_bp = utils.get_parent_assembly_bp(obj)
                carcass_assembly = fd_types.Assembly(carcass_bp)
                edge_bottom_of_left_filler = carcass_assembly.get_prompt("Edge Bottom of Left Filler")
                edge_bottom_of_right_filler = carcass_assembly.get_prompt("Edge Bottom of Right Filler")
                if  part_name == "Left Filler":
                    if edge_bottom_of_left_filler:
                        if edge_bottom_of_left_filler.value():
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_3 = "S1"
                            else:
                                edge_3 = ""
                            edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                if  part_name == "Right Filler":
                    if edge_bottom_of_right_filler:
                        if edge_bottom_of_right_filler.value():
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_3 = "S1"
                            else:
                                edge_3 = ""
                            edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                #Left Capping Filler
                if  part_name == "Left Capping Filler":
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_1 = "S1"
                        edge_2 = "L1"
                        edge_3 = "S2"
                    else:
                        edge_1 = "L1"
                        edge_2 = "S1"
                        edge_3 = "L2"
                    edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                #Left Capping Filler
                if  part_name == "Right Capping Filler":
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_1 = "S1"
                        edge_2 = "L1"
                        edge_3 = "S2"
                    else:
                        edge_1 = "L1"
                        edge_2 = "S1"
                        edge_3 = "L2"
                    edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
            #Bottom Capping
            if obj_props.is_bottom_capping_bp:
                if(assembly.get_prompt("Is Counter Top").value() == False):
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_2 = "L1"
                    else:
                        edge_2 = "S1"
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    
                    carcass_bp = utils.get_parent_assembly_bp(obj)
                    carcass_assembly = fd_types.Assembly(carcass_bp)
                    l_carcass_end_cond = carcass_assembly.get_prompt("Left End Condition").value()
                    r_carcass_end_cond = carcass_assembly.get_prompt("Right End Condition").value()
                    l_assembly_end_cond = assembly.get_prompt("Exposed Left").value()
                    r_assembly_end_cond = assembly.get_prompt("Exposed Right").value()
                    b_assembly_end_cond = assembly.get_prompt("Exposed Back").value()
                    if (l_carcass_end_cond == 'EP' and r_carcass_end_cond != 'EP') or (l_assembly_end_cond == True and r_assembly_end_cond != True):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_1 = "S1"
                        else:
                            edge_1 = "L1"
                        edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)                  

                    if (l_carcass_end_cond != 'EP' and r_carcass_end_cond == 'EP') or (l_assembly_end_cond != True and r_assembly_end_cond == True):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_3 = "S2"
                        else:
                            edge_3 = "L2"
                        edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

                    if (l_carcass_end_cond == 'EP' and r_carcass_end_cond == 'EP') or (l_assembly_end_cond == True and r_assembly_end_cond == True):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_1 = "S1"
                            edge_3 = "S2"
                        else:
                            edge_1 = "L1"
                            edge_3 = "L2"
                        edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    
                    if(b_assembly_end_cond):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_4 = "L2"
                        else:
                            edge_4 = "S2"
                        edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)


        
            #Toe Kick
            if obj_props.is_toe_kick_end_cap_bp:
                #If the Toe Kick is Attached to an Island
                if(obj.parent.parent and obj.parent.parent.lm_closets.is_island):
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_1 = "S1"
                        edge_3 = "S2"
                    else:
                        edge_1 = "L1"
                        edge_3 = "L2"
                    edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            #Counter Top
            if obj_props.is_countertop_bp:
                if assembly.obj_bp.parent and assembly.obj_bp.parent.lm_closets.is_island:
                    l_assembly_end_cond = assembly.get_prompt("Exposed Left").value()
                    r_assembly_end_cond = assembly.get_prompt("Exposed Right").value()
                    if(l_assembly_end_cond and r_assembly_end_cond):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_1 = "S1"
                            edge_2 = "L1"
                            edge_3 = "S2"
                            edge_4 = "L2"
                        else:
                            edge_1 = "L1"
                            edge_2 = "S1"
                            edge_3 = "L2"
                            edge_4 = "S2"
                        edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    elif(l_assembly_end_cond == False and r_assembly_end_cond):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_2 = "L1"
                            edge_3 = "S2"
                            edge_4 = "L2"
                        else:
                            edge_2 = "S1"
                            edge_3 = "L2"
                            edge_4 = "S2"
                        edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    elif(l_assembly_end_cond and r_assembly_end_cond == False):
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_1 = "S1"
                            edge_2 = "L1"
                            edge_4 = "L2"
                        else:
                            edge_1 = "L1"
                            edge_2 = "S1"
                            edge_4 = "S2"
                        edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    else:
                        if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                            edge_2 = "L1"
                            edge_4 = "L2"
                        else:
                            edge_2 = "S1"
                            edge_4 = "S2"
                        edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                else:
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_2 = "L1"
                    else:
                        edge_2 = "S1"
                    edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    
                    carcass_bp = utils.get_parent_assembly_bp(obj)
                    carcass_assembly = fd_types.Assembly(carcass_bp)
                    parent_assembly = fd_types.Assembly(assembly.obj_bp.parent)
                    Countertop_Type = parent_assembly.get_prompt("Countertop Type")

                    if Countertop_Type and Countertop_Type.value() != 'Granite':
                        l_carcass_end_cond = carcass_assembly.get_prompt("Left End Condition").value()
                        r_carcass_end_cond = carcass_assembly.get_prompt("Right End Condition").value()
                        l_assembly_end_cond = assembly.get_prompt("Exposed Left").value()
                        r_assembly_end_cond = assembly.get_prompt("Exposed Right").value()
                        b_assembly_end_cond = assembly.get_prompt("Exposed Back").value()

                        if (l_carcass_end_cond == 'EP' and r_carcass_end_cond != 'EP') or (l_assembly_end_cond == True and r_assembly_end_cond != True):
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_1 = "S1"
                            else:
                                edge_1 = "L1"
                            edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)                  

                        if (l_carcass_end_cond != 'EP' and r_carcass_end_cond == 'EP') or (l_assembly_end_cond != True and r_assembly_end_cond == True):
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_3 = "S2"
                            else:
                                edge_3 = "L2"
                            edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

                        if (l_carcass_end_cond == 'EP' and r_carcass_end_cond == 'EP') or (l_assembly_end_cond == True and r_assembly_end_cond == True):
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_1 = "S1"
                                edge_3 = "S2"
                            else:
                                edge_1 = "L1"
                                edge_3 = "L2"
                            edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                            edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        
                        if b_assembly_end_cond:
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_4 = "L2"
                            else:
                                edge_4 = "S2"
                            edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            if obj_props.is_back_bp:
                if(obj.parent.parent and obj.parent.parent.lm_closets.is_island):
                    island_assembly = fd_types.Assembly(obj.parent.parent)
                    l_assembly_end_cond = island_assembly.get_prompt("Left Against Wall").value()
                    r_assembly_end_cond = island_assembly.get_prompt("Right Against Wall").value()
                    is_double = island_assembly.get_prompt("Depth 2")
                    if(is_double == None):
                        if(l_assembly_end_cond == False and r_assembly_end_cond == False):
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_2 = "S1"
                                edge_4 = "S2"
                            else:
                                edge_2 = "L1"
                                edge_4 = "L2"
                            edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                            edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        elif(l_assembly_end_cond == False and r_assembly_end_cond):
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_2 = "S1"
                            else:
                                edge_2 = "L1"
                            edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                        elif(l_assembly_end_cond and r_assembly_end_cond == False):
                            if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                                edge_2 = "S1"
                            else:
                                edge_2 = "L1"
                            edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
        
            #Toe Kick
            if obj_props.is_toe_kick_end_cap_bp:
                #If the Toe Kick is Attached to an Island
                if(obj.parent.parent.parent and obj.parent.parent.parent.lm_closets.is_island):
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_1 = "S1"
                        edge_3 = "S2"
                    else:
                        edge_1 = "L1"
                        edge_3 = "L2"
                    edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                else:
                    if(abs(assembly.obj_x.location.x) > abs(assembly.obj_y.location.y)):
                        edge_1 = "S1"
                    else:
                        edge_1 = "L1"
                    edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)

            #Flat Crown
            if obj_props.is_flat_crown_bp:
                EL = assembly.get_prompt("Exposed Left").value()
                ER = assembly.get_prompt("Exposed Right").value()
                EB = assembly.get_prompt("Exposed Back").value()
                edge_2 = "L1"
                edge_2_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                if((EL and ER) and assembly.obj_y.location.y < unit.inch(96)):
                    edge_1 = "S1"
                    edge_3 = "S2"
                    edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    edge_3_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                    if(EB):
                        edge_4 = "L2"
                        edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                else:
                    if(len(self.single_exposed_flat_crown) > 0):
                        if(self.single_exposed_flat_crown[0]):
                            edge_1 = "S1"
                            edge_1_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                            self.single_exposed_flat_crown.pop()
                    if(len(self.top_edgebanded_flat_crown) > 0):
                        if(self.top_edgebanded_flat_crown[0]):
                            edge_4 = "L2"
                            edge_4_sku = closet_materials.get_edge_sku(obj, assembly, part_name)
                            self.top_edgebanded_flat_crown.pop()

            len_x = self.get_part_length(assembly)
            len_y = self.get_part_width(assembly)

            if obj_props.is_hamper_front_bp:
                len_x = self.get_part_width(assembly)
                len_y = self.get_part_length(assembly)

            #Create and add label
            lbl = [("IDL-{}".format(self.label_count), "IDJ-{}".format(self.job_count), "IDP-{}".format(self.part_count)),                
                ("dcname", "text", part_name),
                ("name", "text", part_name),
                ("variablesection", "text", str(self.is_variable_section(assembly))),
                ("x", "text", self.get_part_x_location(assembly.obj_bp,assembly.obj_bp.location.x)),
                ("y", "text", self.get_part_y_location(assembly.obj_bp,assembly.obj_bp.location.y)),
                ("z", "text", self.get_part_z_location(assembly.obj_bp,assembly.obj_bp.location.z)),
                ("lenx", "text", len_x),
                ("leny", "text", len_y),
                ("lenz", "text", self.distance(snap_utils.get_part_thickness(obj))),
                ("rotx", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.x)))),
                ("roty", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.x)))),
                ("rotz", "text", str(int(math.degrees(assembly.obj_bp.rotation_euler.x)))),
                ("boml", "text", self.get_part_length(assembly)),
                ("bomt", "text",  self.distance(snap_utils.get_part_thickness(obj))),
                ("bomw", "text", self.get_part_width(assembly)),
                ("catnum", "text", self.get_part_comment(assembly.obj_bp)),#Part Comments2
                ("sku", "text", mat_sku),
                ("cncmirror", "text", ""),#Str literal OKAY
                ("cncrotation", "text", "180"),#Str literal OKAY
                ("cutl", "text", self.get_part_length(assembly)),#Part.AdjustedCutPartLength
                ("cutt", "text", self.distance(snap_utils.get_part_thickness(obj))),
                ("cutw", "text", self.get_part_width(assembly)),#Part.AdjustedCutPartWidth
                ("edgeband1", "text", edge_1),
                ("edgeband1sku", "text", edge_1_sku),
                ("edgeband1name", "text", edge_1_color_name if edge_1 != '' else ''),
                ("edgeband2", "text", edge_2),
                ("edgeband2sku", "text", edge_2_sku),
                ("edgeband2name", "text", edge_2_color_name if edge_2 != '' else ''),
                ("edgeband3", "text", edge_3),
                ("edgeband3sku", "text", edge_3_sku),
                ("edgeband3name", "text", edge_3_color_name if edge_3 != '' else ''),
                ("edgeband4", "text", edge_4),
                ("edgeband4sku", "text", edge_4_sku),
                ("edgeband4name", "text", edge_4_color_name if edge_4 != '' else '')]

            self.labels.append(lbl)
            self.label_count += 1

            #Create and add OperationGroup
            #Get info for segments
            X = self.get_part_length(assembly)
            Y = self.get_part_width(assembly)
            Z = self.distance(snap_utils.get_part_thickness(obj))
            W = 0

            if obj_props.is_hamper_front_bp:
                X = self.get_part_width(assembly)
                Y = self.get_part_length(assembly)

            upper_right = (X, Y, Z, W)
            upper_left = (0, Y, Z, W)
            lower_left = (0, 0, Z, W)
            lower_right = (X, 0, Z, W)

            drilling = self.get_drilling(assembly)

            op_grp = [("IDOP-{}".format(self.op_count), "IDMOR-{}".format(self.or_count)),
                upper_right,#Segment 1
                upper_left,#Segment 2
                lower_left,#Segment 3
                lower_right,#Segment 4
                drilling]

            #Create and operation group for every part
            self.op_groups.append(op_grp)
            self.op_count += 1

            #get token info for writing to op group later
            #self.write_machine_tokens(elm_part, obj)

            if self.debugger:
                self.debugger.write_debug_part(self, assembly, obj, op_grp, lbl, self.part_count)

            self.part_count += 1
    
    def write_material(self,mat_name,mat_sku):
        elm_job = self.xml.tree.findall("Job")[0]
        existing_mats = elm_job.findall("Material")
        mat_exists = self.material_node_exists(mat_sku)

        if not mat_exists:
            mat_id = self.mat_count

            if existing_mats:
                idx = elm_job.getchildren().index(existing_mats[-1]) + 1
                elm_material = self.xml.insert_element(idx, elm_job, 'Material', {'ID': "IDM-{}".format(mat_id)})

            else:
                elm_material = self.xml.add_element(elm_job, 'Material', {'ID': "IDM-{}".format(mat_id)})

            self.xml.add_element_with_text(elm_material, 'Name', mat_name)
            self.xml.add_element_with_text(elm_material, 'Type', "sheet")
            self.xml.add_element_with_text(elm_material, 'SKU', mat_sku)

            self.mat_count += 1
        
        else:
            mat_id = self.get_mat_id(mat_sku) 

        return mat_id

    def get_mat_id(self,sku):
        elm_job = self.xml.tree.findall("Job")[0]
        existing_mats = elm_job.findall("Material")

        for mat in existing_mats:
            if mat.find("SKU").text == sku:
                mat_id = mat.attrib['ID']
                mat_id_num = mat_id.replace('IDM-',"")
        
        return mat_id_num

    def material_node_exists(self,sku):
        elm_job = self.xml.tree.findall("Job")[0]
        existing_mats = elm_job.findall("Material")
        mat_exists = False

        for mat in existing_mats:
            if mat.find("SKU").text == sku:
                mat_exists = True

        return mat_exists

    def write_edgebanding(self,project_node):
        elm_edgebanding = self.xml.add_element(project_node,"Edgebanding")
        for edgeband in self.edgeband_materials:
            elm_edge = self.xml.add_element(elm_edgebanding,'Edgeband',edgeband)
            self.xml.add_element_with_text(elm_edge,'Type',"3")
            self.xml.add_element_with_text(elm_edge,'Thickness',str(self.edgeband_materials[edgeband]))

    def write_buyout_materials(self,project_node):
        elm_buyouts = self.xml.add_element(project_node,"Buyouts")
        for buyout in self.buyout_materials:
            buyout_name = buyout if buyout != "" else "Unnamed"
            self.xml.add_element(elm_buyouts,'Buyout',buyout_name)
    
    def write_solid_stock_material(self,project_node):
        elm_solid_stocks = self.xml.add_element(project_node,"SolidStocks")
        for solid_stock in self.solid_stock_materials:
            solid_stock_name = solid_stock if solid_stock != "" else "Unnamed"
            elm_solid_stock = self.xml.add_element(elm_solid_stocks,'SolidStock',solid_stock_name)
            self.xml.add_element_with_text(elm_solid_stock,'Thickness',str(unit.meter_to_active_unit(self.solid_stock_materials[solid_stock])))
        
    def write_spec_groups(self,project_node):
        #Currently not being used but we might need to export spec groups at
        #some point
        elm_spec_groups = self.xml.add_element(project_node,"SpecGroups")
        
        for spec_group in bpy.context.scene.mv.spec_groups:
            spec_group_name = spec_group.name if spec_group.name != "" else "Unnamed"
            elm_spec_group = self.xml.add_element(elm_spec_groups,'SpecGroup',spec_group_name)
            elm_cutparts = self.xml.add_element(elm_spec_group,'CutParts')
            for cutpart in spec_group.cutparts:
                elm_cutpart_name = cutpart.mv_pointer_name if cutpart.mv_pointer_name != "" else "Unnamed"
                elm_cutpart = self.xml.add_element(elm_cutparts,'PointerName',elm_cutpart_name)
                mat_name = utils.get_material_name_from_pointer(cutpart,spec_group)
                material_name = mat_name if mat_name != "" else "Unnamed"
                self.xml.add_element_with_text(elm_cutpart,'MaterialName',material_name)
                 
            elm_edgeparts = self.xml.add_element(elm_spec_group,'EdgeParts')
            for edgepart in spec_group.edgeparts:
                elm_edgepart_name = edgepart.mv_pointer_name if edgepart.mv_pointer_name != "" else "Unnamed"
                elm_edgepart = self.xml.add_element(elm_edgeparts,'PointerName',elm_edgepart_name)
                mat_name = utils.get_edgebanding_name_from_pointer_name(edgepart.name,spec_group)
                edge_material_name = mat_name if mat_name != "" else "Unnamed"
                self.xml.add_element_with_text(elm_edgepart,'MaterialName',edge_material_name)

    def write_machine_tokens(self,elm_part,obj_part):
        #print("WRITING machine token for:")
        #print(obj_part)
        pass
        #NO MachineTokens XML ELEMENT NEEDED
        # elm_tokens = self.xml.add_element(elm_part,"MachineTokens")

        #LOOP TOKENS ON THIS PART
        for token in obj_part.mv.mp.machine_tokens:
            if not token.is_disabled:
                token_name = token.name if token.name != "" else "Unnamed"

                #NO MachineTokens XML ELEMENT NEEDED
                #elm_token =
                #self.xml.add_element(elm_tokens,'MachineToken',token_name)
                param_dict = token.create_parameter_dictionary()

                #Only type_token used in (CORNERNOTCH, CHAMFER, SLIDE, BORE)
                if token.type_token in {'CORNERNOTCH','CHAMFER','3SIDEDNOTCH'}:
                    #print("token.type_token:
                    #'CORNERNOTCH','CHAMFER','3SIDEDNOTCH'")
                    instructions = token.type_token + token.face + " " + token.edge
                    #print("instructions:", instructions)

                elif token.type_token == 'SLIDE':
                    #print("token.type_token: 'SLIDE'")
                    instructions = token.type_token
                    #print("instructions:", instructions)
                    
                else:
                    #print("token.type_token: ALL OTHERS")
                    instructions = token.type_token + token.face
                    #print("instructions:", instructions)

                #BORE info from token
                # if self.type_token == 'BORE':
                #     param_dict['Par1'] =
                #     str(unit.meter_to_exact_unit(self.dim_in_x))
                #     param_dict['Par2'] =
                #     str(unit.meter_to_exact_unit(self.dim_in_y))
                #     param_dict['Par3'] =
                #     str(unit.meter_to_exact_unit(self.dim_in_z))
                #     param_dict['Par4'] = str(self.face_bore_dia)
                #     param_dict['Par5'] =
                #     str(unit.meter_to_exact_unit(self.end_dim_in_x))
                #     param_dict['Par6'] =
                #     str(unit.meter_to_exact_unit(self.end_dim_in_y))
                #     param_dict['Par7'] =
                #     str(unit.meter_to_exact_unit(self.distance_between_holes))
                #     param_dict['Par8'] = str(self.associative_dia)
                #     param_dict['Par9'] =
                #     str(unit.meter_to_exact_unit(self.associative_depth))

                #print("Attempting to add Element:")
                #self.xml.add_element_with_text(elm_token,'Instruction',instructions)
                #print("\t", instructions)

                #self.xml.add_element_with_text(elm_token,'Par1',param_dict['Par1'])
                #print("\t par1", param_dict['Par1'])

                #self.xml.add_element_with_text(elm_token,'Par2',param_dict['Par2'])
                #print("\t par2", param_dict['Par2'])

                #self.xml.add_element_with_text(elm_token,'Par3',param_dict['Par3'])
                #print("\t par3", param_dict['Par3'])

                #self.xml.add_element_with_text(elm_token,'Par4',param_dict['Par4'])
                #print("\t par4", param_dict['Par4'])

                #self.xml.add_element_with_text(elm_token,'Par5',param_dict['Par5'])
                #print("\t par5", param_dict['Par5'])

                #self.xml.add_element_with_text(elm_token,'Par6',param_dict['Par6'])
                #print("\t par6", param_dict['Par6'])

                #self.xml.add_element_with_text(elm_token,'Par7',param_dict['Par7'])
                #print("\t par7", param_dict['Par7'])

                #self.xml.add_element_with_text(elm_token,'Par8',param_dict['Par8'])
                #print("\t par8", param_dict['Par8'])

                #self.xml.add_element_with_text(elm_token,'Par9',param_dict['Par9'])
                #print("\t par9", param_dict['Par9'])
 
    def write_job_info(self, elm_job):
        dirname = os.path.dirname(bpy.data.filepath).split("\\")[-1]
        filname = "{}.ccp".format(dirname)
        tree = ET.parse(os.path.join(os.path.dirname(bpy.data.filepath), filname))
        root = tree.getroot()
        elm_pinfo = root.find("ProjectInfo")
        elm_rooms = root.find("Rooms")
        rooms = elm_rooms.getchildren()

        customer_name = elm_pinfo.find("customer_name").text
        client_id = elm_pinfo.find("client_id").text
        proj_address = elm_pinfo.find("project_address").text
        city = elm_pinfo.find("city").text
        state = elm_pinfo.find("state").text
        zip_code = elm_pinfo.find("zip_code").text
        cphone_1 = elm_pinfo.find("customer_phone_1").text
        cphone_2 = elm_pinfo.find("customer_phone_2").text
        c_email = elm_pinfo.find("customer_email").text
        proj_notes = elm_pinfo.find("project_notes").text
        designer = elm_pinfo.find("designer").text
        total_room_count = str(len(rooms))
        design_date = elm_pinfo.find("design_date").text

        info = [('jobnumber', self.job_number),
                ('customername', customer_name),
                ('clientid', client_id),
                ('projectaddress', proj_address),
                ('city', city),
                ('state', state),
                ('zipcode', zip_code),
                ('customerphone1', cphone_1),
                ('customerphone2', cphone_2),
                ('customeremail', c_email),
                ('projectnotes', proj_notes),
                ('designer', designer),
                ('totalroomcount', total_room_count),
                ('designdate', design_date)]

        for f in info:
            elm_var = self.xml.add_element(elm_job, 'Var')
            self.xml.add_element_with_text(elm_var, 'Name', f[0])
            self.xml.add_element_with_text(elm_var, 'Value', f[1])

    def write_manufacturing_info(self, context, project_node, create_mfg_node=False):
        if create_mfg_node:
            elm_mfg = self.xml.add_element(project_node, 'Manufacturing', {'ID': "IDMFG-{}".format(self.or_count)})
            elm_or = self.xml.add_element(elm_mfg, 'Orientation', {'ID': "IDMOR-{}".format(self.or_count)})
        else:
            elm_mfg = self.xml.root.find("Manufacturing")

            #Get index of last existing orientation
            existing_or = elm_mfg.findall("Orientation")
            idx = elm_mfg.getchildren().index(existing_or[-1]) + 1           
            elm_or = self.xml.insert_element(idx, elm_mfg, 'Orientation', {'ID': "IDMOR-{}".format(self.or_count)})            

        #Write Orientation TODO determine mirror_x and rotation angle
        self.xml.add_element_with_text(elm_or, "Mirror", "none")#TODO determine mirror_x or none
        self.xml.add_element_with_text(elm_or, "Rotation", "0")#TODO determine rotation angle

        self.write_operation_groups(elm_mfg)
        self.write_labels(elm_mfg)

    def update_mfg_node(self):
        """Resets manufacturing node position above materials if needed
        """
        job_node = self.xml.tree.findall("Job")[0]
        mfg_node = job_node.find("Manufacturing")
        mat_node_1 = job_node.findall("Material")[0]
        mat_node_pos = list(job_node).index(mat_node_1)
        mfg_node_position = list(job_node).index(mfg_node)

        if mat_node_pos < mfg_node_position:
            job_node.remove(mfg_node)
            job_node.insert(mat_node_pos, mfg_node)

    def write_operation_groups(self, elm_mfg):
        for op_grp in self.op_groups:

            #Get index of last existing opgrp
            existing_or = elm_mfg.findall("OperationGroups")

            if existing_or:
                idx = elm_mfg.getchildren().index(existing_or[-1]) + 1           
                elm_op = self.xml.insert_element(idx, 
                                                elm_mfg,
                                                'OperationGroups',
                                                {'ID': op_grp[0][0],
                                                'MfgOrientationID': op_grp[0][1]#ToDo: create counter for mfg_orientation and match up
                                                })             

            else:
                elm_op = self.xml.add_element(elm_mfg,
                                             'OperationGroups',
                                             {'ID': op_grp[0][0],
                                             'MfgOrientationID': op_grp[0][1]#ToDo: create counter for mfg_orientation and match up
                                             })

            segment_coords = [op_grp[1], op_grp[2], op_grp[3], op_grp[4]]
            
            #Segments
            self.add_panel_segment(elm_op, segment_coords)

            #Circles
            circles = op_grp[5]

            if len(circles) > 0:
                for circle in circles:
                    self.add_panel_circle(elm_op, circle)

    def add_panel_circle(self, elm_parent, circle):
        cen_x = circle['cen_x']
        cen_y = circle['cen_y']
        cen_z = circle['cen_z']
        diameter = circle['diameter']
        normal_z = circle['normal_z']
        org_displacement = circle['org_displacement']

        self.xml.add_element_with_text(elm_parent, "Type", "drilled_hole")
        elm_circle = self.xml.add_element(elm_parent, "Circle")

        self.xml.add_element(elm_circle,
            "Center",
            {
                'x': str(cen_x),
                'y': str(cen_y),
                'z': "-{}".format(str(round(cen_z,2)))
            })

        self.xml.add_element_with_text(elm_circle, "Diameter", str(diameter))

        self.xml.add_element(elm_circle,
            "Normal",
            {
                'x': "0",
                'y': "0",
                'z': str(normal_z)
            })     

        self.xml.add_element_with_text(elm_circle, "OrgDisplacement", str(org_displacement))
        self.xml.add_element_with_text(elm_parent, "Comment", "")      

    def add_panel_segment(self, elm_parent, coords):
        self.xml.add_element_with_text(elm_parent, "Type", "panel")#Str literal okay

        for idx, i in enumerate(coords):
            if idx != len(coords) - 1:
                next_coord = coords[idx + 1]

            elif idx == len(coords) - 1:
                next_coord = coords[0]

            elm_seg = self.xml.add_element(elm_parent, 'Segment')

            self.xml.add_element(elm_seg, 'StartCoor', {'x': str(i[0]),#X
                                                        'y': str(i[1]),#Y
                                                        'z': '-{}'.format(str(i[2])),#Z
                                                        'w': "0"})#Appears to be 0, MM uses Vector.Bulge

            self.xml.add_element(elm_seg, 'StartNormal', {'x': "0",#Str literal OKAY
                                                          'y': "0",#Str literal OKAY
                                                          'z': "1"})#Str literal OKAY

            self.xml.add_element_with_text(elm_seg, 'StartOrgDisplacement', "0")#Str literal OKAY

            self.xml.add_element(elm_seg, 'EndCoor', {'x': str(next_coord[0]),#Next coordinate X
                                                      'y': str(next_coord[1]),#Next coordinate Y
                                                      'z': '-{}'.format(str(next_coord[2])),#Next coordinate Z
                                                      'w': "0"})#Str literal OKAY

            self.xml.add_element(elm_seg, 'EndNormal', {'x': "0",#Str literal OKAY
                                                        'y': "0",#Str literal OKAY
                                                        'z': "1"})#Str literal OKAY

            self.xml.add_element_with_text(elm_seg, 'EndOrgDisplacement', "0")#Str literal OKAY

    def write_labels(self, elm_mfg):
        for lbl in self.labels:
            elm_label = self.xml.add_element(elm_mfg,
                                            'Label',
                                            {'ID': lbl[0][0],
                                            'JobID': lbl[0][1],
                                            'PartID': lbl[0][2]})

            for idx, item in enumerate(lbl):
                if idx > 0:
                    self.add_label_item(elm_label, item)

    def add_label_item(self, lbl_node, item):
        self.xml.add_element_with_text(lbl_node, "Name", item[0])
        self.xml.add_element_with_text(lbl_node, "Type", item[1])
        self.xml.add_element_with_text(lbl_node, "Value", item[2])

    def execute(self, context):
        debug_mode = context.user_preferences.addons["snap_db"].preferences.debug_mode
        self.debug_mode = debug_mode

        if snap_db.DEV_TOOLS_AVAILABLE and debug_mode:
            self.debugger = debug_xml_export.Debug()

        self.clear_and_collect_data(context)

        #Replaces project name (filname)
        job_id = "IDJ-{}".format(self.job_count)
        self.set_job_number()

        job_name = self.job_number
        job_source = "SNaP"

        proj_props = bpy.context.window_manager.fd_project
        path = os.path.join(self.xml_path, snap_xml.Snap_XML.filename)

        self.xml = snap_xml.Snap_XML(path=path)

        #If XML does not already exist do initial setup,
        if not os.path.exists(path):
            #Add job
            elm_job = self.xml.add_element(self.xml.root, 'Job', {'ID':job_id, })
            self.xml.add_element_with_text(elm_job, 'Name', job_name)
            self.xml.add_element_with_text(elm_job, 'Source', job_source)
            elm_unit = self.xml.add_element(elm_job, 'Unit')
            self.xml.add_element_with_text(elm_unit, 'Name', 'dimension')
            self.xml.add_element_with_text(elm_unit, 'Measure', 'inch')            

            #Write Item
            self.write_products(elm_job)
            self.write_manufacturing_info(context, elm_job, create_mfg_node=True)
            self.write_job_info(elm_job)
            self.update_mfg_node()

        #If XML already exists, set counts
        else:
            self.xml.set_counts()
            self.item_count = self.xml.item_count
            self.assembly_count = self.xml.assembly_count
            self.part_count = self.xml.part_count
            self.label_count = self.xml.label_count
            self.mat_count = self.xml.mat_count
            self.op_count = self.xml.op_count
            self.or_count = self.xml.or_count       

            #Write item
            self.write_products(self.xml.root)
            self.write_manufacturing_info(context, self.xml.root)

        #self.write_edgebanding(elm_project)
        #self.write_buyout_materials(elm_project)
        #self.write_solid_stock_material(elm_project)

        self.xml.write(self.xml_path)

        if self.debugger:
            self.debugger.create_drilling_preview()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(OPS_Export_XML)


def unregister():
    bpy.utils.unregister_class(OPS_Export_XML)    
