from __future__ import annotations
from typing import Any, Hashable, Optional,  Iterable, Self
from copy import deepcopy

import warnings
from ..abstract_graph import AbstractGraphElement, AbstractNode, AbstractLink, AbstractTurn, AbstractGraph, AbstractStar


class StaticGraphElement(AbstractGraphElement, dict[Hashable, Any]):
    """Base class for graph elements."""

    def __init__(self, **kwargs: Any):
        self.update(kwargs)
        self["_type"] = "graph_element"

    def get_value(self, name: Hashable, default: Optional[Any] = None, **kwargs: Any) -> Any:
        return self.get(name, default)

    def set_value(self, name: Hashable, value: Any, **kwargs: Any) -> None:
        self[name] = value

    def copy(self) -> Self:
        return deepcopy(self)
    
    @property
    def type(self) -> str:
        return self["_type"]


class StaticNode(AbstractNode, StaticGraphElement):
    """Node element of a graph."""

    def __init__(self, idx: Hashable, **kwargs: Any):
        StaticGraphElement.__init__(self, idx=idx, **kwargs)
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

class StaticLink(AbstractLink, StaticGraphElement):
    """Link element of a graph."""

    def __init__(self, idx: Hashable, i: Hashable, j: Hashable, **kwargs: dict[Hashable, Any]):
        StaticGraphElement.__init__(self, idx=idx, i=i, j=j, **kwargs)
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
    

class StaticTurn(AbstractTurn, StaticGraphElement):
    """Turn element of a graph."""

    def __init__(self, idx: Hashable, in_link: Hashable, out_link: Hashable, **kwargs: Any):
        StaticGraphElement.__init__(self, idx=idx, in_link=in_link, out_link=out_link, **kwargs)

    @property
    def idx(self) -> Hashable:
        return self["idx"]

    @property
    def in_link(self) -> Hashable:
        return self["in_link"]

    @property
    def out_link(self) -> Hashable:
        return self["out_link"]
    
class StaticForwardStar(AbstractStar, StaticGraphElement):
    """Star structure to manage links connected to a node."""

    def __init__(self, **kwargs: Any):
        StaticGraphElement.__init__(self, **kwargs)

    def add_link(self, link: StaticLink) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
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

    def get_link(self, i: Hashable, j: Hashable) -> AbstractLink | None:
        return self.get(i,{}).get(j,None)

    def remove(self, idx_from: StaticLink, idx_to: StaticLink) -> None: # pyright: ignore[reportIncompatibleMethodOverride]
        d = self.get(idx_from["i"], {})
        if d:
            d.pop(idx_to["j"], None)
        if not d:
            self.pop(idx_from["i"], None)

class StaticBackwardStar(AbstractStar, StaticGraphElement):
    """Star structure to manage links connected to a node."""

    def __init__(self, **kwargs: Any):
        StaticGraphElement.__init__(self, **kwargs)

    def add_link(self, link: StaticLink) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
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

    def get_link(self, i: Hashable, j: Hashable) -> AbstractLink | None:
        return self.get(j,{}).get(i,None)
    
    def remove(self, link_from: StaticLink, link_to: StaticLink) -> None: # pyright: ignore[reportIncompatibleMethodOverride]
        d = self.get(link_to["j"], {})
        if d:
            d.pop(link_from["i"], None)
        if not d:
            self.pop(link_to["j"], None)

class StaticGraph(AbstractGraph, StaticGraphElement):
    """Graph structure to manage nodes, links, and turns."""

    def __init__(self, **kwargs: Any):
        super().__init__()
        self.update(**kwargs)

        self["links"] = {}
        self["nodes"] = {}
        self["turns"] = {}
        self["bws"] = StaticBackwardStar()
        self["fws"] = StaticForwardStar()
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
    
    def get_links(self) -> Iterable[StaticLink]:
        """
        Get all links in the graph.

        :return: Iterable of link objects
        """
        for link in self["links"].values():
            yield link

    def get_nodes(self) -> Iterable[StaticNode]:
        """
        Get all nodes in the graph.

        :return: Iterable of node objects
        """
        for node in self["nodes"].values():
            yield node
    
    def get_turns(self) -> Iterable[StaticTurn]:
        """
        Get all turns in the graph.

        :return: Iterable of turn objects
        """
        for turn in self["turns"].values():
            yield turn

    def add_link(self, idx: Hashable, i: Hashable, j: Hashable, **kwargs: dict[Hashable,Any]) -> StaticLink:
        """
        Add a link to the graph.

        :param idx: Link identifier
        :param i: Start node identifier
        :param j: End node identifier
        :return: Link object
        """
        l = StaticLink(idx=idx, i=i, j=j, **kwargs)
        links = self["links"]
        links[idx] = l

        self["fws"].add_link(l)
        self["bws"].add_link(l)

        return l

    def add_node(self, idx: Hashable, **kwargs: Any) -> StaticNode:
        """
        Add a node to the graph.

        :param idx: Node identifier
        :return: Node object
        """
        n = StaticNode(idx=idx, **kwargs)
        self["nodes"][idx] = n
        return n

    def add_turn(self, idx: Hashable, in_link: Hashable, out_link: Hashable, **kwargs: Any) -> StaticTurn:
        """
        Add a turn to the graph.

        :param idx: Turn identifier
        :param in_link: Incoming link identifier
        :param out_link: Outgoing link identifier
        :return: Turn object
        """
        t = StaticTurn(idx=idx, in_link=in_link, out_link=out_link, **kwargs)

        turns = self["turns"]
        turns[idx] = t

        turns_fws: dict[Hashable, dict[Hashable, StaticTurn]] = self["turns_fws"]
        d = turns_fws.setdefault(in_link, {})
        d[out_link] = t
        return t

    def get_link(self, idx: Hashable) -> Optional[StaticLink]:
        """
        Get a link by its identifier.

        :param idx: Link identifier
        :return: Link object or None
        """
        return self["links"].get(idx)
    
    def get_link_ij(self, i: Hashable, j: Hashable) -> Optional[StaticLink]:
        """
        Get a link by its identifier.

        :param idx: Link identifier
        :return: Link object or None
        """
        return self["fws"].get_link(i,j)
    
    def get_node(self, idx: Hashable) -> Optional[StaticNode]:
        """
        Get a node by its identifier.

        :param idx: Node identifier
        :return: Node object or None
        """
        return self["nodes"].get(idx)
    
    def get_fws(self, i: Hashable) -> Iterable[StaticLink]:
        """
        Get forward star links for a node.

        :param i: Node identifier
        :return: Iterable of links
        """
        return self["fws"].neighbors(i)
    
    def get_bws(self, j: Hashable) -> Iterable[StaticLink]:
        """
        Get backward star links for a node.

        :param j: Node identifier
        :return: Iterable of links
        """
        return self["bws"].neighbors(j)

    def get_turn(self, idx_or_in_link: Hashable, out_link: Optional[Hashable] = None) -> StaticTurn:
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

