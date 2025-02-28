  
'''
Created on May 6, 2020
@author: Ryan Montes
'''
import bpy
from mv import fd_types, unit, utils
from . import mv_closet_defaults as props_closet
from . import common_parts
from . import common_prompts
from os import path
import math
from . import mv_closet_defaults as props_closet
import operator

class Top(fd_types.Assembly):
    """ Closet Top Shelf
    """

    property_id = props_closet.LIBRARY_NAME_SPACE + ".top"
    drop_id = props_closet.LIBRARY_NAME_SPACE + ".top_shelf_drop"
    
    type_assembly = "INSERT"
    placement_type = "SPLITTER"
    mirror_y = True

    def add_oversize_prompts(self):
        for i in range(10):
            #self.add_prompt(name="Section {} Depth".format(str(i)),prompt_type='DISTANCE',value=True,tab_index=0)
            empty = self.add_empty()
            empty.set_name("Oversize Cut {}".format(str(i+1)))
            
    
    def draw(self):
        self.create_assembly()
        self.obj_bp.mv.export_as_subassembly = True
        props = props_closet.get_object_props(self.obj_bp)
        props.is_closet_top_bp = True
        
        self.add_tab(name='Top Options',tab_type='VISIBLE')#0
        self.add_prompt(name="Extend To Left Panel",prompt_type='CHECKBOX',value=True,tab_index=0)
        self.add_prompt(name="Extend To Right Panel",prompt_type='CHECKBOX',value=True,tab_index=0)
        self.add_prompt(name="Exposed Left",prompt_type='CHECKBOX',value=False,tab_index=0)
        self.add_prompt(name="Exposed Right",prompt_type='CHECKBOX',value=False,tab_index=0)
        self.add_prompt(name="Exposed Back",prompt_type='CHECKBOX',value=False,tab_index=0)
        self.add_prompt(name="Extend Left Amount",prompt_type='DISTANCE',value=unit.inch(0),tab_index=0)
        self.add_prompt(name="Extend Right Amount",prompt_type='DISTANCE',value=unit.inch(0),tab_index=0)
        self.add_prompt(name="Front Overhang",prompt_type='DISTANCE',value=unit.inch(.5),tab_index=0)
        self.add_prompt(name="Max Panel Depth",prompt_type='DISTANCE',value=0,tab_index=0)
        self.add_prompt(name="Max Panel Front Chamfer",prompt_type='DISTANCE',value=0,tab_index=0)
        self.add_prompt(name="Max Rear Chamfer",prompt_type='DISTANCE',value=0,tab_index=0)
        self.add_prompt(name="On Left Most Panel",prompt_type='CHECKBOX',value=False,tab_index=0)
        self.add_prompt(name="On Right Most Panel",prompt_type='CHECKBOX',value=False,tab_index=0)
        self.add_prompt(name="Hang Height",prompt_type='DISTANCE',value=0,tab_index=0)

        self.add_oversize_prompts()
        common_prompts.add_thickness_prompts(self)
        
        Width = self.get_var('dim_x','Width')
        Depth = self.get_var('dim_y','Depth')
        Extend_Left = self.get_var('Extend To Left Panel','Extend_Left')        
        Extend_Right = self.get_var('Extend To Right Panel','Extend_Right')      
        Panel_Thickness = self.get_var('Panel Thickness')
        Extend_Left_Amount = self.get_var('Extend Left Amount')
        Extend_Right_Amount = self.get_var('Extend Right Amount')
        Front_Overhang = self.get_var('Front Overhang')
        Exposed_Left = self.get_var('Exposed Left')
        Exposed_Right = self.get_var('Exposed Right')
        Exposed_Back = self.get_var('Exposed Back')
        Hang_Height = self.get_var('Hang Height')
        top = common_parts.add_plant_on_top(self)
        constraint = top.obj_x.constraints.new(type='LIMIT_LOCATION')
        constraint.use_max_x = True
        constraint.max_x = unit.inch(96)
        constraint.owner_space = 'LOCAL'
        top.obj_bp.mv.comment_2 = "1024"
        top.set_name("Topshelf")
        top.x_loc('IF(Extend_Left,0,Panel_Thickness/2)-Extend_Left_Amount',[Extend_Left,Extend_Left_Amount,Panel_Thickness])

        top.z_loc(value=0)
        top.x_rot(value = 180)
        top.y_rot(value = 0)
        top.z_rot(value = 0)
        top.x_dim('Width-IF(Extend_Left,0,Panel_Thickness/2)-IF(Extend_Right,0,Panel_Thickness/2)+Extend_Left_Amount+Extend_Right_Amount',
                  [Width,Extend_Left,Extend_Right,Panel_Thickness,Extend_Right_Amount,Extend_Left_Amount])
        top.y_dim('Depth+Front_Overhang',[Depth,Front_Overhang])
        top.z_dim('-Panel_Thickness',[Panel_Thickness])
        top.prompt('Exposed Left','Exposed_Left',[Exposed_Left])
        top.prompt('Exposed Right','Exposed_Right',[Exposed_Right])
        top.prompt('Exposed Back','Exposed_Back',[Exposed_Back])
        
        self.update()
        
class PROMPTS_Prompts_Bottom_Support(fd_types.Prompts_Interface):
    bl_idname = props_closet.LIBRARY_NAME_SPACE + ".top"
    bl_label = "Top Prompts"
    bl_options = {'UNDO'}
    
    object_name = bpy.props.StringProperty(name="Object Name",
                                           description="Stores the Base Point Object Name \
                                           so the object can be retrieved from the database.")
    
    width = bpy.props.FloatProperty(name="Width",unit='LENGTH',precision=4)
    height = bpy.props.FloatProperty(name="Height",unit='LENGTH',precision=4)
    depth = bpy.props.FloatProperty(name="Depth",unit='LENGTH',precision=4)    
    
    insert = None

    def check(self, context):
        """ This is called everytime a change is made in the UI """
        props_closet.update_render_materials(self, context)
        return True

    def execute(self, context):
        """ This is called when the OK button is clicked """
        return {'FINISHED'}

    def invoke(self,context,event):
        """ This is called before the interface is displayed """
        self.insert = self.get_insert()
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=utils.get_prop_dialog_width(400))
        
    def draw(self, context):
        """ This is where you draw the interface """
        layout = self.layout
        layout.label(self.insert.obj_bp.mv.name_object)
        box = layout.box()
        
        extend_left = self.insert.get_prompt("Extend To Left Panel")
        extend_right = self.insert.get_prompt("Extend To Right Panel")
        exposed_left = self.insert.get_prompt("Exposed Left")
        exposed_right = self.insert.get_prompt("Exposed Right")      
        exposed_back = self.insert.get_prompt("Exposed Back")      
        extend_left_amount = self.insert.get_prompt("Extend Left Amount")
        extend_right_amount = self.insert.get_prompt("Extend Right Amount")
        front_overhang = self.insert.get_prompt("Front Overhang")

        row = box.row()
        extend_left_amount.draw_prompt(row,text="Extend Left:",split_text=True)
        row = box.row()
        extend_right_amount.draw_prompt(row,text="Extend Right:",split_text=True)
        
        row = box.row()
        front_overhang.draw_prompt(row,text="Extend Front:",split_text=True)
        
        row = box.row()
        row.label("Exposed Edges:")
        exposed_left.draw_prompt(row,text="Left",split_text=False)
        exposed_right.draw_prompt(row,text="Right",split_text=False)       
        exposed_back.draw_prompt(row,text="Back",split_text=False)    

bpy.utils.register_class(PROMPTS_Prompts_Bottom_Support)

class DROP_OPERATOR_Place_Top(bpy.types.Operator):
    bl_idname = props_closet.LIBRARY_NAME_SPACE + ".top_shelf_drop"
    bl_label = "Place Top"
    bl_description = "This places the top."
    bl_options = {'UNDO'}
    
    #READONLY
    object_name = bpy.props.StringProperty(name="Object Name")
    
    top_shelf = None
    selected_panel_1 = None
    selected_panel_2 = None
    objects = []
    panels = []
    max_shelf_length = 96.0
    sel_product_bp = None
    header_text = "Place Top Shelf - Select Partitions (Left to Right)   (Esc, Right Click) = Cancel Command  :  (Left Click) = Select Panel"
    
    def __del__(self):
        bpy.context.area.header_text_set()

    def invoke(self, context, event):
        bp = bpy.data.objects[self.object_name]
        self.top_shelf = fd_types.Assembly(bp)
        context.scene.update() # THE SCENE MUST BE UPDATED FOR RAY CAST TO WORK
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.tag_redraw()
        context.area.header_text_set(text=self.header_text)

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self.cancel_drop(context,event)
            return {'FINISHED'}
        
        return self.insert_drop(context,event)  

    def cancel_drop(self,context,event):
        if self.top_shelf:
            utils.delete_object_and_children(self.top_shelf.obj_bp)
        return {'FINISHED'}

    def get_deepest_panel(self):
        depths = []
        for p in self.panels:
            depths.append(abs(p.obj_y.location.y))
        return max(depths)

    def get_closest_opening(self,x_loc):
        return lambda op : abs(op - x_loc)

    def get_panels(self):
        self.panel_bps.clear()

        for child in self.sel_product_bp.children:
            if child.lm_closets.is_panel_bp:
                self.panel_bps.append(child)
        
        self.panel_bps.sort(key=operator.attrgetter('location.x'))

        for i,bp in enumerate(self.panel_bps):
            print(i,unit.inch(bp.location.x))
            
    def is_first_panel(self, panel):
        if panel.obj_z.location.z < 0:
            return True
        else:
            return False

    def get_inculded_panels(self,panel_1,panel_2):
        self.panels.clear()
        p1_x_loc = panel_1.obj_bp.location.x
        p2_x_loc = panel_2.obj_bp.location.x

        for child in self.sel_product_bp.children:
            if child.lm_closets.is_panel_bp:
                if p1_x_loc <= child.location.x <= p2_x_loc:
                    self.panels.append(fd_types.Assembly(child))

    def insert_drop(self,context,event):
        selected_point, selected_obj = utils.get_selection_point(context,event,objects=self.objects)
        self.sel_product_bp = utils.get_bp(selected_obj,'PRODUCT')
        bpy.ops.object.select_all(action='DESELECT')
        sel_assembly_bp = utils.get_assembly_bp(selected_obj)
        product = fd_types.Assembly(self.sel_product_bp)

        if sel_assembly_bp:
            props = props_closet.get_object_props(sel_assembly_bp)

            if props.is_panel_bp:
                selected_obj.select = True
                hover_panel = fd_types.Assembly(selected_obj.parent)
                hp_x_loc = hover_panel.obj_bp.location.x

                if not self.selected_panel_1:
                    if hover_panel.obj_bp.location.x == product.obj_x.location.x:
                        selected_obj.select = False
                        return {'RUNNING_MODAL'}

                    self.top_shelf.obj_bp.parent = self.sel_product_bp
                    self.top_shelf.obj_bp.location = hover_panel.obj_bp.location

                    if hover_panel.obj_z.location.z > 0:
                        self.top_shelf.obj_bp.location.x = hp_x_loc - unit.inch(0.75)

                    self.top_shelf.obj_bp.location.z += hover_panel.obj_x.location.x
                    self.top_shelf.obj_x.location.x = unit.inch(18.0)
                    self.top_shelf.obj_y.location.y = -hover_panel.obj_y.location.y

                else:
                    self.get_inculded_panels(self.selected_panel_1,hover_panel)
                    sp1_x_loc = self.selected_panel_1.obj_bp.location.x
                    hp_x_loc = hover_panel.obj_bp.location.x
                    ts_length = hp_x_loc - sp1_x_loc
                    same_panel = self.selected_panel_1.obj_bp == hover_panel.obj_bp
                    same_product = self.selected_panel_1.obj_bp.parent == hover_panel.obj_bp.parent
                    hp_to_left = hp_x_loc < sp1_x_loc
                    hp_out_of_reach = unit.meter_to_inch(ts_length) > self.max_shelf_length

                    if same_panel or hp_to_left or not same_product or hp_out_of_reach:
                        selected_obj.select = False
                        return {'RUNNING_MODAL'}

                    if self.is_first_panel(self.selected_panel_1):
                        self.top_shelf.obj_x.location.x = ts_length
                    else:
                        if hp_x_loc < sp1_x_loc:
                            #Hover selection to left
                            pass
                        else:
                            self.top_shelf.obj_x.location.x = ts_length + unit.inch(0.75)

                    self.top_shelf.obj_y.location.y = self.get_deepest_panel()

                if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                    if not self.selected_panel_1:
                        self.selected_panel_1 = hover_panel
                        utils.set_wireframe(self.top_shelf.obj_bp,False)
                        bpy.ops.object.select_all(action='DESELECT')
                        context.scene.objects.active = self.top_shelf.obj_bp

                        self.top_shelf.obj_bp.parent = self.sel_product_bp
                        p1_z_loc = self.selected_panel_1.obj_bp.location.z
                        p1_z_dim = self.selected_panel_1.obj_x.location.x

                        if self.selected_panel_1.obj_z.location.z < 0:
                            self.top_shelf.obj_bp.location.x = self.selected_panel_1.obj_bp.location.x
                        else:
                            self.top_shelf.obj_bp.location.x = self.selected_panel_1.obj_bp.location.x - unit.inch(0.75)
                        self.top_shelf.obj_bp.location.z = p1_z_loc + p1_z_dim
                        self.top_shelf.obj_y.location.y = -self.selected_panel_1.obj_y.location.y

                        return {'RUNNING_MODAL'}

                    if not self.selected_panel_2:
                        self.selected_panel_2 = hover_panel
                        bpy.ops.object.select_all(action='DESELECT')
                        context.scene.objects.active = self.top_shelf.obj_bp
                        self.top_shelf.obj_bp.select = True

                        if self.selected_panel_1.obj_bp == self.selected_panel_2.obj_bp:
                            self.cancel_drop(context,event)
                            return {'FINISHED'}
                            
                        P1_X_Loc = self.selected_panel_1.get_var('loc_x','P1_X_Loc')
                        P2_X_Loc = self.selected_panel_2.get_var('loc_x','P2_X_Loc')
                        Panel_Thickness = product.get_var('Panel Thickness')

                        if self.is_first_panel(self.selected_panel_1):
                            self.top_shelf.x_loc('P1_X_Loc',[P1_X_Loc])
                            self.top_shelf.x_dim('P2_X_Loc-P1_X_Loc',[P1_X_Loc,P2_X_Loc])

                        else:
                            self.top_shelf.x_loc('P1_X_Loc-Panel_Thickness',[P1_X_Loc,Panel_Thickness])
                            self.top_shelf.x_dim('P2_X_Loc-P1_X_Loc+Panel_Thickness',[P1_X_Loc,P2_X_Loc,Panel_Thickness])

                        max_panel_formula = "max(("
                        max_panel_vars = []
                        max_panel_fc_formula = ""
                        max_panel_fc_vars = []
                        max_rc_formula = "max(("
                        max_rc_vars = []

                        MPD = self.top_shelf.get_var('Max Panel Depth','MPD')
                        Max_Rear_Chamfer = self.top_shelf.get_var('Max Rear Chamfer')
                        Max_Panel_Front_Chamfer = self.top_shelf.get_var('Max Panel Front Chamfer')

                        max_panel_fc_vars.append(MPD)
                        max_panel_fc_tail = "0"

                        for i,panel in enumerate(self.panels):
                            max_panel_formula += "abs(PD{}),".format(i+1)
                            max_panel_vars.append(panel.get_var('dim_y','PD{}'.format(i+1)))
                            max_panel_fc_formula += "IF(abs(PD{})==MPD,FCD{},".format(i+1,i+1)
                            max_panel_fc_tail += ")"
                            max_panel_fc_vars.append(panel.get_var('dim_y','PD{}'.format(i+1)))
                            max_panel_fc_vars.append(panel.get_var("Front Chamfer Depth","FCD{}".format(i+1)))
                            max_rc_formula += "RCD{},".format(i+1)
                            max_rc_vars.append(panel.get_var("Rear Chamfer Depth","RCD{}".format(i+1)))

                        max_panel_formula += "))"
                        max_panel_fc_formula += max_panel_fc_tail
                        max_rc_formula += "))"
                        self.top_shelf.prompt('Max Panel Depth',max_panel_formula,max_panel_vars)                                                                                                                                                                                     
                        self.top_shelf.prompt('Max Rear Chamfer',max_rc_formula,max_rc_vars)
                        self.top_shelf.prompt('Max Panel Front Chamfer',max_panel_fc_formula,max_panel_fc_vars)
                        self.top_shelf.y_loc("-Max_Rear_Chamfer",[Max_Rear_Chamfer])
                        self.top_shelf.y_dim("MPD-Max_Rear_Chamfer-Max_Panel_Front_Chamfer",[MPD,Max_Rear_Chamfer,Max_Panel_Front_Chamfer])

                        hang_height = self.top_shelf.get_prompt("Hang Height")
                        if hang_height:
                            hang_height.set_value(math.fabs(product.obj_z.location.z))

                        extend_left_amount = self.top_shelf.get_prompt("Extend Left Amount")
                        extend_right_amount = self.top_shelf.get_prompt("Extend Right Amount")
                        on_left_most_panel = self.top_shelf.get_prompt("On Left Most Panel")
                        on_right_most_panel = self.top_shelf.get_prompt("On Right Most Panel")

                        parent_bp =  self.top_shelf.obj_bp.parent
                        parent_assembly = fd_types.Assembly(parent_bp)
                        add_left_filler = parent_assembly.get_prompt("Add Left Filler")
                        left_filler_amount = parent_assembly.get_prompt("Left Side Wall Filler")
                        add_right_filler = parent_assembly.get_prompt("Add Right Filler")
                        right_filler_amount = parent_assembly.get_prompt("Right Side Wall Filler")
                        right_filler_setback_amount = parent_assembly.get_prompt("Right Filler Setback Amount")
                        left_filler_setback_amount = parent_assembly.get_prompt("Left Filler Setback Amount")

                        filler_prompts = [extend_left_amount,extend_right_amount,add_left_filler,left_filler_amount,add_right_filler,right_filler_amount,left_filler_setback_amount,right_filler_setback_amount]
                        left_props = props_closet.get_object_props(self.selected_panel_1.obj_bp)
                        right_props = props_closet.get_object_props(self.selected_panel_2.obj_bp)
                        if on_left_most_panel and on_right_most_panel:
                            on_left_most_panel.set_value(left_props.is_left_panel_bp)
                            on_right_most_panel.set_value(right_props.is_right_panel_bp)

                        if all(filler_prompts):
                            if add_left_filler.value() and left_props.is_left_panel_bp:
                                extend_left_amount.set_value(left_filler_amount.value())
                            if add_right_filler.value() and right_props.is_right_panel_bp:
                                extend_right_amount.set_value(right_filler_amount.value())
               
                        return {'FINISHED'}
            
        return {'RUNNING_MODAL'}
    

bpy.utils.register_class(DROP_OPERATOR_Place_Top)
