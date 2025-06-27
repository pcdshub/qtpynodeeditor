import typing

from qtpy.QtCore import QLineF, QPointF, QSize, Qt
from qtpy.QtGui import QIcon, QPainter, QPainterPath, QPainterPathStroker, QPen

from .connection_geometry import ConnectionGeometry
from .enums import PortType
from .style import ConnectionStyle, SplineType

if typing.TYPE_CHECKING:
    from .connection import Connection  # noqa


use_debug_drawing = False


def cubic_path(geom: ConnectionGeometry):
    source, sink = geom.source, geom.sink
    c1, c2 = geom.points_c1_c2()

    # cubic spline
    cubic = QPainterPath(source)

    cubic.cubicTo(c1, c2, sink)
    return cubic


def linear_path(geom: ConnectionGeometry):
    source, sink = geom.source, geom.sink
    linear = QPainterPath(source)

    linear.lineTo(sink)
    return linear


SPLINE_MAP: typing.Dict[
    SplineType, typing.Callable[[ConnectionGeometry], QPainterPath]
] = {
    SplineType.CUBIC: cubic_path,
    SplineType.LINEAR: linear_path,
}


def debug_drawing(painter, connection: 'Connection'):
    geom = connection.geometry
    source, sink = geom.source, geom.sink
    c1, c2 = geom.points_c1_c2()

    painter.setPen(Qt.red)
    painter.setBrush(Qt.red)

    painter.drawLine(QLineF(source, c1))
    painter.drawLine(QLineF(c1, c2))
    painter.drawLine(QLineF(c2, sink))
    painter.drawEllipse(c1, 3, 3)
    painter.drawEllipse(c2, 3, 3)

    painter.setBrush(Qt.NoBrush)

    path_fn = SPLINE_MAP[connection.style.connection.spline_type]
    painter.drawPath(path_fn(geom))
    painter.setPen(Qt.yellow)

    painter.drawRect(geom.bounding_rect)


def draw_sketch_line(
    painter: QPainter,
    connection: 'Connection',
    style: ConnectionStyle
):
    if not connection.requires_port:
        return

    p = QPen()
    p.setWidthF(style.construction_line_width)
    p.setColor(style.construction_color)
    p.setStyle(Qt.DashLine)

    painter.setPen(p)
    painter.setBrush(Qt.NoBrush)

    geom = connection.geometry

    path_fn = SPLINE_MAP[style.spline_type]
    path = path_fn(geom)
    painter.drawPath(path)


def draw_hovered_or_selected(
    painter: QPainter,
    connection: 'Connection',
    style: ConnectionStyle
):
    geom = connection.geometry
    hovered = geom.hovered

    graphics_object = connection.graphics_object
    selected = graphics_object.isSelected()

    # drawn as a fat background
    if hovered or selected:
        p = QPen()

        line_width = style.line_width

        p.setWidthF(2.0 * line_width)
        p.setColor(style.selected_halo_color if selected else style.hovered_color)

        painter.setPen(p)
        painter.setBrush(Qt.NoBrush)

        # cubic spline
        path_fn = SPLINE_MAP[style.spline_type]
        path = path_fn(geom)
        painter.drawPath(path)


def draw_normal_line(painter, connection, style):
    if connection.requires_port:
        return

    # colors
    normal_color_out = style.get_normal_color()
    normal_color_in = normal_color_out

    selected_color = style.selected_color

    gradient_color = False
    if style.use_data_defined_colors:
        data_type_out = connection.data_type(PortType.output)
        data_type_in = connection.data_type(PortType.input)

        gradient_color = data_type_out.id != data_type_in.id

        normal_color_out = style.get_normal_color(data_type_out.id)
        normal_color_in = style.get_normal_color(data_type_in.id)
        selected_color = normal_color_out.darker(200)

    # geometry
    geom = connection.geometry
    line_width = style.line_width

    # draw normal line
    p = QPen()
    p.setWidthF(line_width)

    graphics_object = connection.graphics_object
    selected = graphics_object.isSelected()

    path_fn = SPLINE_MAP[style.spline_type]
    path = path_fn(geom)
    if gradient_color:
        painter.setBrush(Qt.NoBrush)

        c = normal_color_out
        if selected:
            c = c.darker(200)

        p.setColor(c)
        painter.setPen(p)

        segments = 60

        for i in range(segments):
            ratio_prev = float(i) / segments
            ratio = float(i + 1) / segments

            if i == segments / 2:
                c = normal_color_in
                if selected:
                    c = c.darker(200)

                p.setColor(c)
                painter.setPen(p)

            painter.drawLine(path.pointAtPercent(ratio_prev), path.pointAtPercent(ratio))

        icon = QIcon(":convert.png")

        pixmap = icon.pixmap(QSize(22, 22))
        painter.drawPixmap(path.pointAtPercent(0.50) - QPointF(pixmap.width() / 2, pixmap.height() / 2), pixmap)
    else:
        p.setColor(normal_color_out)

        if selected:
            p.setColor(selected_color)

        painter.setPen(p)
        painter.setBrush(Qt.NoBrush)

        painter.drawPath(path)


class ConnectionPainter:
    @staticmethod
    def paint(painter: QPainter, connection: 'Connection',
              style: ConnectionStyle):
        """
        Paint

        Parameters
        ----------
        painter : QPainter
        connection : Connection
        style : ConnectionStyle
        """
        draw_hovered_or_selected(painter, connection, style)
        draw_sketch_line(painter, connection, style)
        draw_normal_line(painter, connection, style)
        if use_debug_drawing:
            debug_drawing(painter, connection)

        # draw end points
        geom = connection.geometry
        source, sink = geom.source, geom.sink

        point_diameter = style.point_diameter
        painter.setPen(style.construction_color)
        painter.setBrush(style.construction_color)
        point_radius = point_diameter / 2.0
        painter.drawEllipse(source, point_radius, point_radius)
        painter.drawEllipse(sink, point_radius, point_radius)

    @staticmethod
    def get_painter_stroke(geom: ConnectionGeometry) -> QPainterPath:
        """
        Get painter stroke

        Parameters
        ----------
        geom : ConnectionGeometry

        Returns
        -------
        value : QPainterPath
        """
        path_fn = SPLINE_MAP[geom._spline_type]
        path = path_fn(geom)
        source = geom.source
        result = QPainterPath(source)
        segments = 20

        for i in range(segments):
            ratio = float(i + 1) / segments
            result.lineTo(path.pointAtPercent(ratio))

        stroker = QPainterPathStroker()
        stroker.setWidth(10.0)
        return stroker.createStroke(result)
