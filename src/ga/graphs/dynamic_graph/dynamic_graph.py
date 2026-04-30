from __future__ import annotations
from typing import Any, Hashable, Optional,  Iterable, Self,  TypeVar, Generic
from copy import deepcopy

import warnings
from ..abstract_graph import AbstractGraphElement, AbstractNode, AbstractLink, AbstractTurn, AbstractGraph, AbstractStar

T = TypeVar("T")  # Defines a generic type

class DynamicGraphElement(AbstractGraphElement, dict[Hashable, Any], Generic[T]):
    """Base class for graph elements."""

    def __init__(self, base_time: float | int = 0, total_time: float | int = 1, delta_t: float | int = 1, **kwargs: Any):
        self.update(kwargs)
        self["_base_time"] = base_time
        self["_total_time"] = total_time
        self["_delta_t"] = delta_t
        self["_num_intervals"] = total_time // delta_t
        self["_type"] = "graph_element"        
        self["_attributes_params"] = {}

    def add_attribute(self, name: Hashable, value: Iterable[T] | T, default: Optional[T] = None, **kwargs: Any) -> None:
        num_intervals = self["_num_intervals"]
        if isinstance(value, Iterable):  # If value is iterable, adjust its length to num_intervals
            value_list: list[T] = list(value) # pyright: ignore[reportUnknownArgumentType]
            if num_intervals > len(value_list):
                value_list.extend([value_list[-1]] * (num_intervals - len(value_list)))
            else:
                value_list = value_list[:num_intervals]
            self["_attributes_params"][name] = {"default": default}
            self[name] = value_list
        else:  # If value is a scalar, fill the intervals with the same value
            self["_attributes_params"][name] = {"default": default}
            self[name] = [value] * num_intervals

    def get_value(self, name: Hashable, t: float | int = 0,  **kwargs: Any) -> Any:
        if name in self["_attributes"]:
            index = int((t - self["_base_time"]) // self["_delta_t"])
            default_value = kwargs.get("default", None)
            if default_value is None:
                default_value = self["_attributes_params"].get(name, {}).get("default", None)
            values = self[name]
            if index < len(values):
                return values[index]
            elif len(values) == 0:
                return default_value
            return values[-1]
        else:
            return self[name]            

    def set_value(self, name: Hashable, value: Any, t: float | int = 0, **kwargs: Any) -> None:
        if name in self["_attributes"]:
            index = int((t - self["_base_time"]) // self["_delta_t"])
            values = self[name]
            if index < len(values):
                values[index] = value
            elif len(values) == 0:
                self[name] = [value] * self["_num_intervals"]
            else:
                values[-1] = value
        else:
            self[name] = value

    def copy(self) -> Self:
        return deepcopy(self)
    
    @property
    def type(self) -> str:
        return self["_type"]


class DynamicNode(AbstractNode, DynamicGraphElement[Any]):
    """Node element of a graph."""

    def __init__(self, idx: Hashable, **kwargs: Any):
        DynamicGraphElement[Any].__init__(self, idx=idx, **kwargs)
        self["_type"] = "node"

    @property
    def idx(self) -> Hashable:
        return self["idx"]

    @property
    def i(self) -> Hashable:
        return self["idx"]

    @property
    def j(self) -> Hashable:
        return self["idx"]

class DynamicLink(AbstractLink, DynamicGraphElement[Any]):
    """Link element of a graph."""

    def __init__(self, idx: Hashable, i: Hashable, j: Hashable, **kwargs: Any):
        DynamicGraphElement[Any].__init__(self, idx=idx, i=i, j=j, **kwargs)
        self["_type"] = "link"

    @property
    def idx(self) -> Hashable:
        return self["idx"]

    @property
    def i(self) -> Hashable:
        return self["i"]

    @property
    def j(self) -> Hashable:
        return self["j"]
    

class DynamicTurn(AbstractTurn, DynamicGraphElement[Any]):
    """Turn element of a graph."""

    def __init__(self, idx: Hashable, in_link: Hashable, out_link: Hashable, **kwargs: Any):
        DynamicGraphElement[Any].__init__(self, idx=idx, in_link=in_link, out_link=out_link, **kwargs)

    @property
    def idx(self) -> Hashable:
        return self["idx"]

    @property
    def in_link(self) -> Hashable:
        return self["in_link"]

    @property
    def out_link(self) -> Hashable:
        return self["out_link"]
    
class DynamicForwardStar(AbstractStar, DynamicGraphElement[Any]):
    """Star structure to manage links connected to a node."""

    def __init__(self, **kwargs: Any):
        DynamicGraphElement[Any].__init__(self, **kwargs)

    def add_link(self, link: DynamicLink) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        Add a link to the star structure.

        :param link: Link object
        :param direct: True for incoming link, False for outgoing link
        """
        d = self.setdefault(link["i"], {})
        l_prev = d.setdefault(link["j"], link)
        if l_prev and link != l_prev:
            warnings.warn(f"Link {link['idx']} duplicates existing link {l_prev['idx']} in forward star of node {link['i']}-{link['j']}")

    def neighbors(self, idx: Hashable) -> Iterable[AbstractLink]:
        """
        Get the link star dictionary for a given node.
        
        Args:
            idx: Node identifier
        Returns:
            Iterable of links connected to the node
        """        
        for link in self.get(idx, {}).values():
            yield link

    def remove(self, idx_from: DynamicLink, idx_to: DynamicLink) -> None: # pyright: ignore[reportIncompatibleMethodOverride]
        d = self.get(idx_from["i"], {})
        if d:
            d.pop(idx_to["j"], None)
        if not d:
            self.pop(idx_from["i"], None)

class DynamicBackwardStar(AbstractStar, DynamicGraphElement[Any]):
    """Star structure to manage links connected to a node."""

    def __init__(self, **kwargs: Any):
        DynamicGraphElement[Any].__init__(self, **kwargs)

    def add_link(self, link: DynamicLink) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        Add a link to the star structure.

        :param link: Link object
        :param direct: True for incoming link, False for outgoing link
        """
        d = self.setdefault(link["j"], {})
        l_prev = d.setdefault(link["i"], link)
        if l_prev and link != l_prev:
            warnings.warn(f"Link {link['idx']} duplicates existing link {l_prev['idx']} in backward star of node {link['j']}-{link['i']}")

    def neighbors(self, idx: Hashable) -> Iterable[AbstractLink]:
        """
        Get the link star dictionary for a given node.
        
        Args:
            idx: Node identifier
        Returns:
            Iterable of links connected to the node
        """        
        for link in self.get(idx, {}).values():
            yield link
    
    def remove(self, link_from: DynamicLink, link_to: DynamicLink) -> None: # pyright: ignore[reportIncompatibleMethodOverride]
        d = self.get(link_to["j"], {})
        if d:
            d.pop(link_from["i"], None)
        if not d:
            self.pop(link_to["j"], None)

class DynamicGraph(AbstractGraph, DynamicGraphElement[Any]):
    """Graph structure to manage nodes, links, and turns."""

    def __init__(self, **kwargs: Any):
        super().__init__()
        self.update(**kwargs)

        self["links"] = {}
        self["nodes"] = {}
        self["turns"] = {}
        self["bws"] = DynamicBackwardStar()
        self["fws"] = DynamicForwardStar()
        self["turns_fws"] = {}

    @property
    def n_links(self) -> int:
        return len(self["links"])

    @property
    def n_nodes(self) -> int:
        return len(self["nodes"])

    @property
    def n_turns(self) -> int:
        return len(self["turns"])
    
    def get_links(self) -> Iterable[DynamicLink]:
        """
        Get all links in the graph.

        :return: Iterable of link objects
        """
        for link in self["links"].values():
            yield link

    def get_nodes(self) -> Iterable[DynamicNode]:
        """
        Get all nodes in the graph.

        :return: Iterable of node objects
        """
        for node in self["nodes"].values():
            yield node
    
    def get_turns(self) -> Iterable[DynamicTurn]:
        """
        Get all turns in the graph.

        :return: Iterable of turn objects
        """
        for turn in self["turns"].values():
            yield turn

    def add_link(self, idx: Hashable, i: Hashable, j: Hashable, **kwargs: dict[Hashable,Any]) -> DynamicLink:
        """
        Add a link to the graph.

        :param idx: Link identifier
        :param i: Start node identifier
        :param j: End node identifier
        :return: Link object
        """
        l = DynamicLink(idx=idx, i=i, j=j, **kwargs)
        links = self["links"]
        links[idx] = l

        self["fws"].add_link(l)
        self["bws"].add_link(l)

        return l

    def add_node(self, idx: Hashable, **kwargs: Any) -> DynamicNode:
        """
        Add a node to the graph.

        :param idx: Node identifier
        :return: Node object
        """
        n = self["nodes"].get(idx)
        if n is None:
            n = DynamicNode(idx=idx, **kwargs)
            self["nodes"][idx] = n
        return n
        
    def add_turn(self, idx: Hashable, in_link: Hashable, out_link: Hashable, **kwargs: Any) -> DynamicTurn:
        """
        Add a turn to the graph.

        :param idx: Turn identifier
        :param in_link: Incoming link identifier
        :param out_link: Outgoing link identifier
        :return: Turn object
        """
        t = DynamicTurn(idx=idx, in_link=in_link, out_link=out_link, **kwargs)

        turns = self["turns"]
        turns[idx] = t

        turns_fws: dict[Hashable, dict[Hashable, DynamicTurn]] = self["turns_fws"]
        d = turns_fws.setdefault(in_link, {})
        d[out_link] = t
        return t

    def get_link(self, idx: Hashable) -> Optional[DynamicLink]:
        """
        Get a link by its identifier.

        :param idx: Link identifier
        :return: Link object or None
        """
        return self["links"].get(idx)

    def get_node(self, idx: Hashable) -> Optional[DynamicNode]:
        """
        Get a node by its identifier.

        :param idx: Node identifier
        :return: Node object or None
        """
        return self["nodes"].get(idx)
    
    def get_fws(self, i: Hashable) -> Iterable[DynamicLink]:
        """
        Get forward star links for a node.

        :param i: Node identifier
        :return: Iterable of links
        """
        return self["fws"].neighbors(i)
    
    def get_bws(self, j: Hashable) -> Iterable[DynamicLink]:
        """
        Get backward star links for a node.

        :param j: Node identifier
        :return: Iterable of links
        """
        return self["bws"].neighbors(j)

    def get_turn(self, idx_or_in_link: Hashable, out_link: Optional[Hashable] = None) -> DynamicTurn:
        """
        Get turns for given incoming and outgoing links.

        :param in_link: Incoming link identifier
        :param out_link: Outgoing link identifier
        :return: List of turns
        """
        if out_link is None:
            return self["turns"].get(idx_or_in_link)
        else:
            return self["turns_fws"].get(idx_or_in_link, {}).get(out_link)

