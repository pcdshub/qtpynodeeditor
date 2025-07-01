import typing
from collections import OrderedDict

from .enums import ReactToConnectionState
from .node_data import NodeDataType
from .port import Port, PortType

if typing.TYPE_CHECKING:
    from .connection import Connection  # noqa
    from .node import Node


class NodeState:
    def __init__(self, node: 'Node'):
        '''
        node_state

        Parameters
        ----------
        model : Node
        '''
        self._ports: typing.Dict[PortType, OrderedDict[int, Port]] = {
            PortType.input: OrderedDict(),
            PortType.output: OrderedDict()
        }

        self.node = node
        # setup initial nodes and ports
        for port_type in self._ports:
            num_ports = self.node.model.num_ports[port_type]
            self._ports[port_type] = OrderedDict(
                (i, Port(self.node, port_type=port_type, index=i))
                for i in range(num_ports)
            )

        self._reaction = ReactToConnectionState.not_reacting
        self._reacting_port_type = PortType.none
        self._reacting_data_type = None
        self._resizing = False

    def _update_ports(self):
        for port_type in self._ports:
            num_ports = self.node.model.num_ports[port_type]
            curr_num_ports = len(self._ports[port_type])
            if num_ports == curr_num_ports:
                continue

            if num_ports > curr_num_ports:
                # simply append ports, do not recreate old ones
                # (may break incoming connections)
                for i in range(num_ports):
                    if i not in self._ports[port_type]:
                        self._ports[port_type][i] = Port(self.node,
                                                         port_type=port_type,
                                                         index=i)
                continue

            # otherwise we may need to shift existing connections
            # gather connections for each port, retaining order
            old_connections: OrderedDict[int, list[Connection]] = OrderedDict()
            for port_idx, port in self._ports[port_type].items():
                if len(port.connections) == 0:
                    continue
                old_connections[port_idx] = []
                for conn in port.connections:
                    old_connections[port_idx].append(conn)

            if len(old_connections) > num_ports:
                raise RuntimeError(
                    "Gathered too many ports to reconnect "
                    f"({len(old_connections)} into {num_ports} ports)"
                )

            # Create new ports to set up new indexing
            self._ports[port_type] = OrderedDict(
                (i, Port(self.node, port_type=port_type, index=i))
                for i in range(num_ports)
            )

            # Re-assign connections to their new ports
            for new_port, connections in zip(self._ports[port_type].values(), old_connections.values()):
                for old_conn in connections:
                    old_conn._ports[port_type] = new_port
                    new_port.add_connection(old_conn)

    def __getitem__(self, key):
        self._update_ports()
        return self._ports[key]

    @property
    def ports(self):
        yield from self.input_ports
        yield from self.output_ports

    @property
    def input_ports(self):
        yield from self[PortType.input].values()

    @property
    def output_ports(self):
        yield from self[PortType.output].values()

    @property
    def output_connections(self):
        """All output connections"""
        self._update_ports()
        return [
            connection
            for idx, port in self._ports[PortType.output].items()
            for connection in port.connections
        ]

    @property
    def input_connections(self):
        """All input connections"""
        self._update_ports()
        return [
            connection
            for idx, port in self._ports[PortType.input].items()
            for connection in port.connections
        ]

    @property
    def all_connections(self):
        """All input and output connections"""
        return self.input_connections + self.output_connections

    def connections(self, port_type: PortType, port_index: int) -> list:
        """
        Connections

        Parameters
        ----------
        port_type : PortType
        port_index : int

        Returns
        -------
        value : list
        """
        self._update_ports()
        return list(self._ports[port_type][port_index].connections)

    def erase_connection(self, port_type: PortType, port_index: int, connection: 'Connection'):
        """
        Erase connection

        Parameters
        ----------
        port_type : PortType
        port_index : int
        connection : Connection
        """
        self._update_ports()
        self._ports[port_type][port_index].remove_connection(connection)

    @property
    def reaction(self) -> ReactToConnectionState:
        """
        Reaction

        Returns
        -------
        value : NodeState.ReactToConnectionState
        """
        return self._reaction

    @property
    def reacting_port_type(self) -> PortType:
        """
        Reacting port type

        Returns
        -------
        value : PortType
        """
        return self._reacting_port_type

    @property
    def reacting_data_type(self) -> NodeDataType:
        """
        Reacting data type

        Returns
        -------
        value : NodeDataType
        """
        return self._reacting_data_type

    def set_reaction(self, reaction: ReactToConnectionState,
                     reacting_port_type: PortType = PortType.none,
                     reacting_data_type: NodeDataType = None):
        """
        Set reaction

        Parameters
        ----------
        reaction : NodeState.ReactToConnectionState
        reacting_port_type : PortType, optional
        reacting_data_type : NodeDataType
        """
        self._reaction = ReactToConnectionState(reaction)
        self._reacting_port_type = reacting_port_type
        self._reacting_data_type = reacting_data_type

    @property
    def is_reacting(self) -> bool:
        """
        Is the node reacting to a mouse event?

        Returns
        -------
        value : bool
        """
        return self._reaction == ReactToConnectionState.reacting

    @property
    def resizing(self) -> bool:
        """
        Resizing

        Returns
        -------
        value : bool
        """
        return self._resizing

    @resizing.setter
    def resizing(self, resizing: bool):
        self._resizing = resizing
