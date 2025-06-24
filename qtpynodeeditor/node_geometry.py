import math
import typing

from qtpy.QtCore import QPointF, QRect, QRectF, QSizeF
from qtpy.QtGui import QFont, QFontMetrics, QTransform
from qtpy.QtWidgets import QSizePolicy

from qtpynodeeditor.style import LayoutDirection

from .enums import NodeValidationState, PortType
from .port import Port

if typing.TYPE_CHECKING:
    from .node import Node  # noqa


class NodeGeometry:
    def __init__(self, node: 'Node'):
        super().__init__()
        self._node = node
        self._model = node.model
        self._dragging_pos = QPointF(-1000, -1000)
        self._entry_width = 0
        self._entry_height = 20
        self._font_metrics = QFontMetrics(QFont())
        self._height = 150
        self._hovered = False
        self._input_port_width = 70
        self._output_port_width = 70
        self._spacing = 20
        self._style = node.style
        self._width = 100

        f = QFont()
        f.setBold(True)
        self._bold_font_metrics = QFontMetrics(f)

    @property
    def height(self) -> int:
        """
        Node height.

        Returns
        -------
        value : int
        """
        return self._height

    @height.setter
    def height(self, h: int):
        self._height = int(h)

    @property
    def width(self) -> int:
        """
        Node width.

        Returns
        -------
        value : int
        """
        return self._width

    @width.setter
    def width(self, width: int):
        self._width = int(width)

    @property
    def entry_height(self) -> int:
        """
        Entry height

        Returns
        -------
        value : int
        """
        return self._entry_height

    @entry_height.setter
    def entry_height(self, h: int):
        self._entry_height = int(h)

    @property
    def entry_width(self) -> int:
        """
        Entry width

        Returns
        -------
        value : int
        """
        return self._entry_width

    @entry_width.setter
    def entry_width(self, width: int):
        self._entry_width = int(width)

    @property
    def spacing(self) -> int:
        """
        Spacing

        Returns
        -------
        value : int
        """
        return self._spacing

    @spacing.setter
    def spacing(self, s: int):
        self._spacing = int(s)

    @property
    def hovered(self) -> bool:
        """
        Hovered

        Returns
        -------
        value : bool
        """
        return self._hovered

    @hovered.setter
    def hovered(self, h: int):
        self._hovered = bool(h)

    @property
    def num_sources(self) -> int:
        """
        Number of sources.

        Returns
        -------
        value : int
        """
        return self._model.num_ports[PortType.output]

    @property
    def num_sinks(self) -> int:
        """
        Number of sinks.

        Returns
        -------
        value : int
        """
        return self._model.num_ports[PortType.input]

    @property
    def dragging_position(self) -> QPointF:
        """
        Dragging pos

        Returns
        -------
        value : QPointF
        """
        return self._dragging_pos

    @dragging_position.setter
    def dragging_position(self, pos: QPointF):
        self._dragging_pos = QPointF(pos)

    # Back-compatibility
    dragging_pos = dragging_position

    def entry_bounding_rect(self, *, addon=0.0) -> QRectF:
        """
        Entry bounding rect

        Returns
        -------
        value : QRectF
        """
        return QRectF(0 - addon, 0 - addon,
                      self._entry_width + 2 * addon,
                      self._entry_height + 2 * addon)

    @property
    def bounding_rect(self) -> QRectF:
        """
        Bounding rect

        Returns
        -------
        value : QRectF
        """
        addon = 4 * self._style.connection_point_diameter
        return QRectF(0 - addon, 0 - addon,
                      self._width + 2 * addon, self._height + 2 * addon)

    def recalculate_size(self, font: typing.Optional[QFont] = None):
        """
        If font is unspecified,
            Updates size unconditionally
        Otherwise,
            Updates size if the QFontMetrics is changed
        """
        if font is not None:
            font_metrics = QFontMetrics(font)
            bold_font = QFont(font)
            bold_font.setBold(True)
            bold_font_metrics = QFontMetrics(bold_font)
            if self._bold_font_metrics == bold_font_metrics:
                return

            self._font_metrics = font_metrics
            self._bold_font_metrics = bold_font_metrics

        max_num_of_entries = max((self.num_sinks, self.num_sources))
        widget = self._model.embedded_widget()
        self._entry_height = self._font_metrics.height()
        port_height = self._entry_height + self._spacing
        self._input_port_width = self.port_width(PortType.input)
        self._output_port_width = self.port_width(PortType.output)

        if self._node.style.layout_direction == LayoutDirection.HORIZONTAL:
            # height based on number of ports
            height = port_height * max_num_of_entries

            # width based on input + output port width
            width = self._input_port_width + self._output_port_width
            width += 2 * self._spacing
        elif self._node.style.layout_direction == LayoutDirection.VERTICAL:
            # some minimum height setting
            height = port_height * 2

            # width based on the number of ports that exist
            max_port_width = max(self._input_port_width, self._output_port_width)
            width = max_port_width * max_num_of_entries + 2 * self._spacing

        if widget:
            height = max((height, widget.height()))
        height += self.caption_height

        if widget:
            width += widget.width()
        width = max((width, self.caption_width))

        if self._model.validation_state() != NodeValidationState.valid:
            width = max((width, self.validation_width))
            height += self.validation_height + self._spacing

        self._width = width
        self._height = height

    def _calc_horizontal_port_position(
        self,
        port_type: PortType,
        index: int
    ) -> typing.Tuple[float, float]:

        step = self._entry_height + self._spacing
        total_height = float(self.caption_height) + step * index
        # TODO_UPSTREAM: why?
        total_height += step / 2.0

        if port_type == PortType.output:
            x = self._width + self._style.connection_point_diameter
        elif port_type == PortType.input:
            x = -float(self._style.connection_point_diameter)
        else:
            raise ValueError(port_type)
        return x, total_height

    def _calc_vertical_port_position(
        self,
        port_type: PortType,
        index: int
    ) -> typing.Tuple[float, float]:
        total_num_ports = self._model.num_ports[port_type]
        x = self._width / (total_num_ports + 1) * (index + 1)
        if port_type == PortType.output:
            y = self._height + self._style.connection_point_diameter
        elif port_type == PortType.input:
            y = -float(self._style.connection_point_diameter)
        else:
            raise ValueError(port_type)
        return x, y

    def port_scene_position(self, port_type: PortType, index: int,
                            t: QTransform = None) -> QPointF:
        """
        Port scene position

        Parameters
        ----------
        port_type : PortType
        index : int
        t : QTransform

        Returns
        -------
        value : QPointF
        """
        if t is None:
            t = QTransform()

        if self._node.style.layout_direction == LayoutDirection.HORIZONTAL:
            x, y = self._calc_horizontal_port_position(port_type, index)
        elif self._node.style.layout_direction == LayoutDirection.VERTICAL:
            x, y = self._calc_vertical_port_position(port_type, index)

        result = QPointF(x, y)

        return t.map(result)

    def check_hit_scene_point(self, port_type: PortType, scene_point: QPointF,
                              scene_transform: QTransform) -> typing.Optional[Port]:
        """
        Check a scene point for a specific port type.

        Parameters
        ----------
        port_type : PortType
            The port type to check for.

        scene_point : QPointF
            The point in the scene.

        scene_transform : QTransform
            The scene transform.

        Returns
        -------
        port : Port or None
            The nearby port, if found.
        """
        if port_type == PortType.none:
            return None

        nearby_port = None

        tolerance = 2.0 * self._style.connection_point_diameter
        for idx, port in self._node.state[port_type].items():
            pos = port.get_mapped_scene_position(scene_transform) - scene_point
            distance = math.sqrt(QPointF.dotProduct(pos, pos))
            if distance < tolerance:
                nearby_port = port
                break

        return nearby_port

    @property
    def resize_rect(self) -> QRect:
        """
        Resize rect

        Returns
        -------
        value : QRect
        """
        rect_size = 7
        return QRect(self._width - rect_size,
                     self._height - rect_size,
                     rect_size,
                     rect_size)

    @property
    def widget_position(self) -> QPointF:
        """
        Returns the position of a widget on the Node surface

        Returns
        -------
        value : QPointF
        """
        widget = self._model.embedded_widget()
        if not widget:
            return QPointF()

        if (widget.sizePolicy().verticalPolicy() == QSizePolicy.MinimumExpanding or
                widget.sizePolicy().verticalPolicy() == QSizePolicy.Expanding):
            # If the widget wants to use as much vertical space as possible,
            # place it immediately after the caption.
            return QPointF(self._spacing + self.port_width(PortType.input),
                           self.caption_height)

        if self._model.validation_state() != NodeValidationState.valid:
            return QPointF(
                self._spacing + self.port_width(PortType.input),
                (self.caption_height + self._height - self.validation_height -
                 self._spacing - widget.height()) / 2.0,
            )

        return QPointF(
            self._spacing + self.port_width(PortType.input),
            (self.caption_height + self._height - widget.height()) / 2.0
        )

    def equivalent_widget_height(self) -> int:
        '''
        The maximum height a widget can be without causing the node to grow.

        Returns
        -------
        value : int
        '''
        base_height = self.height - self.caption_height

        if self._model.validation_state() != NodeValidationState.valid:
            return base_height + self.validation_height

        return base_height

    @property
    def validation_height(self) -> int:
        """
        Validation height

        Returns
        -------
        value : int
        """
        msg = self._model.validation_message()
        return self._bold_font_metrics.boundingRect(msg).height()

    @property
    def validation_width(self) -> int:
        """
        Validation width

        Returns
        -------
        value : int
        """
        msg = self._model.validation_message()
        return self._bold_font_metrics.boundingRect(msg).width()

    @staticmethod
    def calculate_node_position_between_node_ports(
            target_port_index: int,
            target_port: PortType,
            target_node: 'Node',
            source_port_index: int,
            source_port: PortType,
            source_node: 'Node',
            new_node: 'Node') -> QPointF:
        """
        calculate node position between node ports

        Calculating the nodes position in the scene. It'll be positioned half
        way between the two ports that it "connects".  The first line
        calculates the halfway point between the ports (node position + port
        position on the node for both nodes averaged).  The second line offsets
        self coordinate with the size of the new node, so that the new nodes
        center falls on the originally calculated coordinate, instead of it's
        upper left corner.

        Parameters
        ----------
        target_port_index : int
        target_port : PortType
        target_node : Node
        source_port_index : int
        source_port : PortType
        source_node : Node
        new_node : Node

        Returns
        -------
        value : QPointF
        """
        if (source_node.graphics_object is None
                or target_node.graphics_object is None):
            raise ValueError('Uninitialized node')
        converter_node_pos = (
            source_node.graphics_object.pos()
            + source_node.geometry.port_scene_position(source_port, source_port_index)
            + target_node.graphics_object.pos()
            + target_node.geometry.port_scene_position(target_port, target_port_index)
        ) / 2.0
        converter_node_pos.setX(converter_node_pos.x() - new_node.geometry.width / 2.0)
        converter_node_pos.setY(converter_node_pos.y() - new_node.geometry.height / 2.0)
        return converter_node_pos

    @property
    def caption_height(self) -> int:
        """
        Caption height

        Returns
        -------
        value : int
        """
        if not self._model.caption_visible:
            return 0
        name = self._model.caption
        return self._bold_font_metrics.boundingRect(name).height()

    @property
    def caption_width(self) -> int:
        """
        Caption width

        Returns
        -------
        value : int
        """
        if not self._model.caption_visible:
            return 0
        name = self._model.caption
        return self._bold_font_metrics.boundingRect(name).width()

    def port_width(self, port_type: PortType) -> int:
        """
        Port width

        Parameters
        ----------
        port_type : PortType

        Returns
        -------
        value : int
        """
        names = [port.display_text
                 for port in self._node[port_type].values()]
        if not names:
            return 0

        return max(self._font_metrics.horizontalAdvance(name)
                   for name in names)

    @property
    def size(self):
        """
        Get the node size

        Parameters
        ----------
        node : Node

        Returns
        -------
        value : QSizeF
        """
        return QSizeF(self.width, self.height)
