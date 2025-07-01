import logging

from qtpy.QtWidgets import QApplication

import qtpynodeeditor as nodeeditor
from qtpynodeeditor import (Connection, NodeData, NodeDataModel, NodeDataType,
                            NodeValidationState, Port, PortType)
from qtpynodeeditor.style import LayoutDirection, SplineType, StyleCollection


class BlankNodeData(NodeData):
    """
    Node data with no caption.  We don't actually pass data between nodes,
    so there's no need to label the ports
    """
    # port caption defaults to node data type if there's no caption provided
    # add some spaces to help with spacing
    data_type = NodeDataType("n/a", "  ")


class RootNodeModel(NodeDataModel):
    """
    Root node model.  Simply holds one child
    Is valid if it has a child
    """
    caption_visible = True
    num_ports = {"input": 0, "output": 1}
    port_caption_visible = {
        "input": {},
        "output": {0: False},
    }
    data_type = BlankNodeData.data_type
    name = "Root"

    def set_out_data(self, node_data: BlankNodeData, port: Port):
        # only validating that the output node exists
        # self._parent_node = node_data.parent_node
        try:
            self._child_node = port.connections[0].output_node
            self._validation_state = NodeValidationState.valid
            self._validation_message = "Connected"
        except IndexError:
            self._validation_state = NodeValidationState.warning
            self._validation_message = "Uninitialized"


class MultiChildNodeModel(NodeDataModel):
    """
    Mixin class holding logic to enable dynamic number of children.
    This requires making .num_ports, .data_type, and .port_caption_visible
    react to the number of connections.

    num_ports is a property to avoid the validation performed by NodeDataModel

    Takes a variable number of children, and is valid if it has a parent
    """
    def __init__(self, style=None, parent=None, max_children: int = 0):
        super().__init__(style=style, parent=parent)
        self.caption_visible = True
        self.max_children = max_children
        # initial ports
        self._num_ports = {"input": 1, "output": 1}
        self._port_caption_visible = {
            "input": {0: False},
            "output": {0: False},
        }
        # for multiple ouptuts, must provide a dictionary
        # NodeDataModel tries to fill sensible default dictionaries, but gives up
        # if num_ports is a property (if dynamically defined)
        self._data_type = {
            "input": {0: BlankNodeData.data_type},
            "output": {0: BlankNodeData.data_type},
        }

        self._parent_node = None
        self._validation_state = NodeValidationState.warning
        self._validation_message = "Uninitialized"

        self.output_connections = []

    def validation_state(self) -> NodeValidationState:
        return self._validation_state

    def validation_message(self) -> str:
        return self._validation_message

    def set_in_data(self, node_data: BlankNodeData, port: Port):
        # only validating that the parent node is a valid predecessor
        # self._parent_node = node_data.parent_node
        try:
            self._parent_node = port.connections[0].input_node
            self._validation_state = NodeValidationState.valid
            self._validation_message = "Connected"
        except IndexError:
            self._validation_state = NodeValidationState.warning
            self._validation_message = "Uninitialized"

    @property
    def num_ports(self):
        return self._num_ports

    @property
    def data_type(self):
        return self._data_type

    @property
    def port_caption_visible(self):
        return self._port_caption_visible

    def output_connection_created(self, connection: Connection):
        if connection in self.output_connections:
            return
        self.output_connections.append(connection)
        self._update_output_info()

    def output_connection_deleted(self, connection):
        if connection not in self.output_connections:
            return
        self.output_connections.remove(connection)
        self._update_output_info()

    def _update_output_info(self):
        if self.max_children > 0:
            num_new_conn = min(len(self.output_connections) + 1,
                               self.max_children)
        else:
            num_new_conn = len(self.output_connections) + 1

        self._num_ports["output"] = num_new_conn
        self._port_caption_visible["output"] = {
            i: False for i in range(num_new_conn)
        }
        self._data_type["output"] = {
            i: BlankNodeData.data_type for i in range(num_new_conn)
        }


class LeafNodeModel(NodeDataModel):
    """
    NodeModel mixin for leaf nodes (action nodes)
    Takes no children, and is valid if it has a parent
    """
    caption_visible = True
    num_ports = {"input": 1, "output": 0}
    port_caption_visible = {
        "input": {0: False},
        "output": {}
    }
    data_type = BlankNodeData.data_type

    def __init__(self, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self._parent_node = None
        self._validation_state = NodeValidationState.warning
        self._validation_message = "Uninitialized"

    def __init_subclass__(cls, verify=True, **kwargs):
        return super().__init_subclass__(verify, **kwargs)

    @property
    def caption(self):
        return self.name

    def set_in_data(self, node_data: BlankNodeData, port: Port):
        # only validating that the parent node is a valid predecessor
        # self._parent_node = node_data.parent_node
        try:
            self._parent_node = port.connections[0].input_node
            self._validation_state = NodeValidationState.valid
            self._validation_message = "Connected"
        except IndexError:
            self._validation_state = NodeValidationState.warning
            self._validation_message = "Uninitialized"

    def validation_state(self) -> NodeValidationState:
        return self._validation_state

    def validation_message(self) -> str:
        return self._validation_message


def main(app):
    registry = nodeeditor.DataModelRegistry()

    my_style = StyleCollection()
    my_style.node.layout_direction = LayoutDirection.VERTICAL
    my_style.connection.spline_type = SplineType.LINEAR

    models = (LeafNodeModel, MultiChildNodeModel, RootNodeModel,)

    for model in models:
        registry.register_model(model, category='Nodes',
                                style=my_style)

    scene = nodeeditor.FlowScene(style=my_style, registry=registry)

    view = nodeeditor.FlowView(scene)
    view.setWindowTitle("Tree example")
    view.resize(800, 600)
    view.show()

    root = scene.create_node(RootNodeModel)
    parent_1 = scene.create_node(MultiChildNodeModel)
    parent_2 = scene.create_node(MultiChildNodeModel)
    parent_3 = scene.create_node(MultiChildNodeModel)
    parent_3.model.name = "parent"
    leaf_1 = scene.create_node(LeafNodeModel)
    leaf_1.model.name = "action"
    leaf_2 = scene.create_node(LeafNodeModel)

    scene.create_connection(root[PortType.output][0],
                            parent_1[PortType.input][0])
    scene.create_connection(parent_1[PortType.output][0],
                            parent_2[PortType.input][0])
    scene.create_connection(parent_1[PortType.output][1],
                            parent_3[PortType.input][0])
    scene.create_connection(parent_3[PortType.output][0],
                            leaf_1[PortType.input][0])
    scene.create_connection(parent_3[PortType.output][1],
                            leaf_2[PortType.input][0])

    try:
        scene.auto_arrange(layout="pygraphviz", prog="dot")
    except ImportError:
        ...

    return scene, view


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    app = QApplication([])
    scene, view = main(app)
    view.show()
    app.exec_()
