import bpy
from bpy.types import (Panel, Operator, PropertyGroup)
from bpy.props import (EnumProperty, PointerProperty, FloatProperty)
import pathlib
import os

from . import normal_to_height
if "bpy" in locals():
    import importlib
    importlib.reload(normal_to_height)

bl_info = {
    'name': 'NormalHeight',
    'description': 'Generate height from normal maps',
    'author': 'Hugo Tini',
    'version': (0, 1, 0),
    'blender': (2, 82, 0),
    'location': 'Node Editor > NormalHeight',
    'category': 'Material'
}

# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------


class NormalHeightProperties(PropertyGroup):

    height_type_enum: EnumProperty(
        name='Height map variants',
        description='If input normal map is seamless, select seamless.',
        items=[('SEAMLESS', 'Seamless',
                'if input is seamless, generates a seamless height map'),
               ('NON_SEAMLESS', 'Non-seamless',
                'non-seamless, takes more RAM to compute')]
    )

# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------


class WM_OT_NormalHeightOperator(Operator):
    '''Generate a height map from a normal map. Settings in NormalHeight tab (Node Editor)'''

    bl_label = 'NormalHeight'
    bl_idname = 'wm.normal_height'

    @classmethod
    def poll(self, context):
        if context.active_node == None:
            return False
        selected_node_type = context.active_node.bl_idname
        return (context.area.type == 'NODE_EDITOR') and (selected_node_type == 'ShaderNodeTexImage')

    def execute(self, context):
        # make sure numpy is installed
        try:
            import numpy as np
        except ImportError as e:
            self.report({'WARNING'}, 'Numpy dependency missing.')
            print(e)
            return {'CANCELLED'}

        # get input image from selected node
        input_node = context.active_node
        input_img = input_node.image
        if input_img == None:
            self.report(
                {'WARNING'}, 'Selected image node must have an image assigned to it.')
            return {'CANCELLED'}

        # progress report
        wm = bpy.context.window_manager
        wm.progress_begin(0, 6)

        # convert to C,H,W numpy array
        width = input_img.size[0]
        height = input_img.size[1]
        channels = input_img.channels
        img = np.array(input_img.pixels)
        img = np.reshape(img, (channels, width, height), order='F')
        img = np.transpose(img, (0, 2, 1))

        wm.progress_update(1)

        # get gradients from normal map
        grad_x, grad_y = normal_to_height.normal_to_grad(img)
        grad_x = np.flip(grad_x, axis=0)
        grad_y = np.flip(grad_y, axis=0)

        # if non-seamless chosen, expand gradients
        HEIGHT_TYPE = context.scene.normal_height_tool.height_type_enum
        if HEIGHT_TYPE == 'NON_SEAMLESS':
            grad_x, grad_y = normal_to_height.copy_flip(grad_x, grad_y)

        wm.progress_update(2)

        # compute height map
        pred_img = normal_to_height.frankot_chellappa(
            -grad_x, grad_y)
        if HEIGHT_TYPE != 'SEAMLESS':
            # cut to valid part if gradients were expanded
            pred_img = pred_img[:height, :width]
        pred_img = np.stack([pred_img, pred_img, pred_img])

        wm.progress_update(3)

        # create new image datablock
        img_name = os.path.splitext(input_img.name)
        height_name = img_name[0] + '_height' + img_name[1]
        height_img = bpy.data.images.new(
            height_name, width=width, height=height)
        height_img.colorspace_settings.name = 'Non-Color'

        wm.progress_update(4)

        # flip height
        pred_img = np.flip(pred_img, axis=1)
        # add alpha channel
        pred_img = np.concatenate(
            [pred_img, np.ones((1, height, width))], axis=0)
        # flatten to array
        pred_img = np.transpose(pred_img, (0, 2, 1)).flatten('F')
        # write to image block
        height_img.pixels = pred_img

        wm.progress_update(5)

        # create new node for height map
        height_node = context.material.node_tree.nodes.new(
            type='ShaderNodeTexImage')
        height_node.location = input_node.location
        height_node.location[1] -= height_node.width*1.2
        height_node.image = height_img

        wm.progress_update(6)

        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

class OBJECT_PT_NormalHeightPanel(Panel):
    bl_label = 'NormalHeight'
    bl_idname = 'OBJECT_PT_NormalHeightPanel'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'NormalHeight'
    bl_context = 'objectmode'

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        normal_height_tool = context.scene.normal_height_tool

        layout.label(text='Height map type : ')
        layout.prop(normal_height_tool, 'height_type_enum', text='')

        layout.separator()
        layout.operator('wm.normal_height', text='Generate Height Map')
        layout.separator()

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------


classes = (
    NormalHeightProperties,
    WM_OT_NormalHeightOperator,
    OBJECT_PT_NormalHeightPanel
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.normal_height_tool = PointerProperty(
        type=NormalHeightProperties)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.normal_height_tool


if __name__ == '__main__':
    register()
