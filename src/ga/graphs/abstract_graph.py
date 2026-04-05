from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, Hashable, Optional, Self, Iterable
from ..io import Serializer
import warnings

try:
    from shapely import Point # pyright: ignore[reportMissingModuleSource]
except ImportError:
    # Fallback to identity if shapely is not available, for type compatibility
    from ..utils.convert import identity as Point

class AbstractGraphElement(ABC):
    """
    Abstract base class for graph elements (nodes, links, turns).
    
    This class provides a common interface for all graph elements. Each element
    has a type identifier and supports time-dependent or static value storage
    through abstract get_value/set_value methods.
    
    The class supports serialization/deserialization and deep copying,
    making it suitable for both persistent storage and in-memory operations.
    
    Attributes:
        type: The type of the graph element ("node", "link", or "turn")
    
    Note:
        Concrete implementations should inherit from this class and implement
        the abstract methods for value storage and retrieval.
    """
    def __init__(self, **kwargs: Any):
        """
        Initialize a graph element with arbitrary attributes.
        
        Args:
            **kwargs: Arbitrary keyword arguments to store as element attributes
        """
        super().__init__(**kwargs)


    @property
    def type(self) -> str:
        """
        Get the type of the graph element.
        
        Returns the stored type or falls back to the class name if not set.
        This property is automatically set by subclasses but can be overridden.
        
        Returns:
            str: The type identifier of this graph element
        """
        return "graph_element"
    
    
    @abstractmethod
    def get_value(self, name: Hashable, **kwargs: Any) -> Any:
        """
        Get the value of an attribute, potentially at a specific time.
        
        This method allows retrieving attribute values that may vary over time.
        Implementations should handle both static and dynamic attributes.
        For dynamic graphs, use kwargs to specify temporal parameters.
        
        Args:
            name: The name/key of the attribute to retrieve
            default: Default value returned if attribute doesn't exist
            **kwargs: Additional parameters for context (e.g., time=t for dynamic attributes)
            
        Returns:
            The attribute value at the specified context, or default if not found
            
        Example:
            >>> element.get_value("capacity")  # Static attribute
            >>> element.get_value("flow", time=10.5)  # Dynamic attribute at time 10.5
        """
        pass

    @abstractmethod
    def set_value(self, name: Hashable, value: Any, **kwargs: Any) -> None:
        """
        Set the value of an attribute, potentially at a specific time.
        
        This method allows setting attribute values that may vary over time.
        Implementations should handle both static and dynamic attributes.
        For dynamic graphs, use kwargs to specify temporal parameters.
        
        Args:
            name: The name/key of the attribute to set
            value: The value to assign to the attribute
            **kwargs: Additional parameters for context (e.g., time=t for dynamic attributes)
            
        Example:
            >>> element.set_value("capacity", 100)  # Static attribute
            >>> element.set_value("flow", 50, time=10.5)  # Dynamic attribute at time 10.5
        """
        pass

    def save(self, filename: str | Path) -> None:
        """
        Save the graph element to a file using serialization.
        
        Persists the complete element state including all attributes and
        metadata using the Serializer class. Supports optional compression
        for efficient storage. For dynamic elements, the entire time history
        is preserved.

        Args:
            filename: File path where the element should be saved
            compression: Compression algorithm ('blosc', 'gzip', 'bz2', 'lzma', etc.)
                        None means no compression
            clevel: Compression level from 1 (fastest) to 9 (best compression)
                   Higher values trade speed for smaller file size
            
        Raises:
            IOError: If the file cannot be written (permissions, disk space, etc.)
            SerializationError: If the element cannot be serialized
            
        Example:
            >>> element.save("my_node.pkl")  # Uncompressed
            >>> element.save("my_node.pkl.gz", compression="gzip", clevel=6)
        """
        Serializer.dump(self, filename, compression=None, clevel=5)

    @classmethod
    def load(cls, filename: str | Path) -> Self:
        """
        Load a graph element from a file.
        
        Deserializes a previously saved graph element, restoring all its
        attributes and state. The returned object will be of the correct
        subclass type when called on derived classes.
        
        Args:
            filename: Path to the file containing the serialized element
            
        Returns:
            The deserialized graph element of the appropriate type
            
        Raises:
            IOError: If the file cannot be read
            SerializationError: If the file cannot be deserialized
            
        Note:
            Uses @classmethod instead of @staticmethod to ensure proper
            type inference with inheritance.
        """
        return Serializer.load(filename)

    @abstractmethod
    def copy(self) -> Self:
        """
        Create a deep copy of the graph element.
        
        Returns a new instance of the same type with all attributes
        copied recursively. This ensures complete independence from
        the original object, including any nested data structures.
        
        Returns:
            A deep copy of this graph element with identical content
            
        Note:
            For elements with time-dependent attributes, the entire
            history is copied, not just the current state.
        """
        pass        


class AbstractNode(AbstractGraphElement):
    """
    Abstract base class for nodes (vertices) in a graph.
    
    Nodes represent discrete entities or locations in the graph structure.
    Each node has a unique identifier and can store additional attributes
    such as coordinates, capacities, costs, or any domain-specific properties.
    
    Common Applications:
        - Transportation: Intersections, stations, airports, ports
        - Networks: Routers, switches, servers, connection points
        - Social: People, organizations, entities
        - Supply Chain: Facilities, warehouses, distribution centers
        - Workflows: Tasks, decision points, milestones
    
    Attributes:
        idx: Unique identifier for the node (must be hashable)
        type: Element type, always "node" for node instances
    
    Example Usage:
        >>> # In a concrete implementation
        >>> node = ConcreteNode("intersection_1", 
        ...                    x=125.5, y=340.2, 
        ...                    capacity=1500,
        ...                    name="Main Street & Oak Ave")
        >>> print(node.idx)  # "intersection_1"
        >>> node.get_value("capacity")  # 1500
    """
    @abstractmethod
    def __init__(self, idx: Hashable, **kwargs: Any):
        """
        Initialize a node with a unique identifier.
        
        Args:
            idx: Unique identifier for this node (must be hashable)
            **kwargs: Additional attributes to store with the node
                     (e.g., coordinates, capacity, name, etc.)
                     
        Raises:
            TypeError: If idx is not hashable
        """
        pass


    @property
    @abstractmethod
    def idx(self) -> Hashable:
        """
        Get the unique identifier of this node.
        
        Returns:
            The unique identifier for this node
        """
        pass

    @property
    def type(self) -> str:
        """
        Get the type of the graph element.
        
        Returns the stored type or falls back to the class name if not set.
        This property is automatically set by subclasses but can be overridden.
        
        Returns:
            str: The type identifier of this graph element
        """
        return "node"
    


class AbstractLink(AbstractGraphElement):
    """
    Abstract base class for links (directed edges) in a graph.
    
    Links represent directed connections between nodes in the graph.
    Each link connects a source node (i) to a destination node (j) and
    has a unique identifier. Links can store attributes such as weights,
    capacities, costs, distances, or flow constraints.
    
    Direction: Links are inherently directed (i → j). For undirected graphs,
    create bidirectional links (A→B and B→A) or use graph-level logic.
    
    Common Applications:
        - Transportation: Roads, railway segments, flight routes, shipping lanes
        - Networks: Cables, wireless connections, data pipes, communication channels
        - Social: Relationships, communications, influence connections
        - Supply Chain: Transportation routes, conveyor belts, pipelines
        - Workflows: Process transitions, data flow, dependency relationships
    
    Attributes:
        idx: Unique identifier for the link (must be hashable)
        i: Source (origin) node identifier
        j: Destination (target) node identifier
        type: Element type, always "link" for link instances
        
    Example Usage:
        >>> # In a concrete implementation
        >>> link = ConcreteLink("highway_101", "city_A", "city_B",
        ...                    length=45.2, speed_limit=65, lanes=4,
        ...                    toll_cost=3.50)
        >>> print(f"{link.i} → {link.j}")  # "city_A → city_B"
        >>> link.get_value("length")  # 45.2
    """

    @abstractmethod
    def __init__(self, idx: Hashable, i: Hashable, j: Hashable, **kwargs: Any):
        """
        Initialize a link connecting two nodes.
        
        Creates a directed connection from node i to node j with the
        specified identifier and optional attributes.
        
        Args:
            idx: Unique identifier for this link (must be hashable)
            i: Source (origin) node identifier
            j: Destination (target) node identifier  
            **kwargs: Additional attributes to store with the link
                     (e.g., length, weight, capacity, cost, speed_limit)
                     
        Raises:
            TypeError: If any identifier is not hashable
            ValueError: If i and j are identical (self-loops may not be allowed)
        """
        pass
   
    @property    
    @abstractmethod
    def idx(self) -> Hashable:
        """
        Get the unique identifier of this link.
        
        The identifier is used for referencing and indexing the link
        within the graph structure and should be unique among all links.
        
        Returns:
            The unique identifier for this link
        """
        pass

    @property
    @abstractmethod
    def i(self) -> Hashable:
        """
        Get the source (origin) node identifier.
        
        This identifies the starting point of the directed link.
        In flow networks, this is where flow originates.
        In transportation, this is the departure point.
        
        Returns:
            The identifier of the source node this link originates from
        """
        pass

    @property
    @abstractmethod
    def j(self) -> Hashable:
        """
        Get the destination (target) node identifier.
        
        This identifies the ending point of the directed link.
        In flow networks, this is where flow terminates.
        In transportation, this is the arrival point.
        
        Returns:
            The identifier of the destination node this link points to
        """
        pass

    @property
    def type(self) -> str:
        """
        Get the type of the graph element.
        
        Returns the stored type or falls back to the class name if not set.
        This property is automatically set by subclasses but can be overridden.
        
        Returns:
            str: The type identifier of this graph element
        """
        return "link"
    
class AbstractTurn(AbstractGraphElement):
    """
    Abstract base class for turns in a graph.
    
    Turns represent transitions between two connected links in the graph.
    They model the movement from one link (incoming) to another link (outgoing)
    and are essential for representing movement constraints, costs, or
    restrictions at connection points.
    
    Turn Semantics: A turn exists when the destination of the incoming link
    matches the source of the outgoing link, creating a continuous path.
    
    Common Applications:
        - Transportation: Turn movements at intersections, lane changes,
          routing restrictions, turn costs and delays
        - Networks: Packet routing between network segments, switching costs
        - Workflows: Process transitions, conditional branches, decision logic
        - Supply Chain: Material handling transitions, equipment changeovers
        - Games/AI: Movement transitions in path planning, action sequences
    
    Attributes:
        idx: Unique identifier for the turn (must be hashable)
        in_link: Identifier of the incoming (source) link
        out_link: Identifier of the outgoing (destination) link
        type: Element type, always "turn" for turn instances
        
    Example Usage:
        >>> # In a concrete implementation - traffic intersection
        >>> turn = ConcreteTurn("left_turn_1", "north_approach", "west_exit",
        ...                    cost=15.0, delay=3.5, allowed=True,
        ...                    turn_type="left", signal_protected=True)
        >>> print(f"{turn.in_link} ↷ {turn.out_link}")  # "north_approach ↷ west_exit"
        >>> turn.get_value("delay")  # 3.5
        
        >>> # Network routing example
        >>> routing_turn = ConcreteTurn("route_A_to_B", "fiber_segment_1", "fiber_segment_2",
        ...                           bandwidth_cost=0.1, latency_ms=2.0)
    """

    @abstractmethod
    def __init__(self, idx: Hashable, in_link: Hashable, out_link: Hashable, **kwargs: Any):
        """
        Initialize a turn between two connected links.
        
        Creates a turn movement from the incoming link to the outgoing link.
        The links should be connected (out-node of in_link == in-node of out_link).
        
        Args:
            idx: Unique identifier for this turn (must be hashable)
            in_link: Identifier of the incoming (source) link
            out_link: Identifier of the outgoing (destination) link
            **kwargs: Additional attributes to store with the turn
                     (e.g., cost, delay, allowed, turn_type, restrictions)
                     
        Raises:
            TypeError: If any identifier is not hashable
            ValueError: If in_link and out_link are identical
            
        Note:
            The turn validity (whether links are actually connected) may be
            checked at the graph level rather than during turn creation.
        """
        pass
    
    @property
    @abstractmethod
    def idx(self) -> Hashable:
        """
        Get the unique identifier of this turn.
        
        The identifier is used for referencing and indexing the turn
        within the graph structure and should be unique among all turns.
        
        Returns:
            The unique identifier for this turn
        """
        pass

    @property
    @abstractmethod
    def in_link(self) -> Hashable:
        """
        Get the incoming (source) link identifier.
        
        This identifies the link from which the turn movement originates.
        Traffic or flow enters the turn from this link.
        
        Returns:
            The identifier of the link entering this turn
        """
        pass

    @property
    @abstractmethod
    def out_link(self) -> Hashable:
        """
        Get the outgoing (destination) link identifier.
        
        This identifies the link to which the turn movement leads.
        Traffic or flow exits the turn onto this link.
        
        Returns:
            The identifier of the link exiting this turn
        """
        pass

    @property
    def type(self) -> str:
        """
        Get the type of the graph element.
        
        Returns the stored type or falls back to the class name if not set.
        This property is automatically set by subclasses but can be overridden.
        
        Returns:
            str: The type identifier of this graph element
        """
        return "turn"
    
class AbstractStar(ABC):
    """
    Abstract base class for link star structures in a graph.
    
    Link stars provide efficient access to the forward and backward
    connections of links associated with nodes. They enable quick
    retrieval of outgoing (forward star) and incoming (backward star)
    links for any given node.
    
    Common Applications:
        - Transportation: Quickly find all outgoing roads from an intersection
          or all incoming roads to a junction
        - Networks: Retrieve all outgoing connections from a router or
          all incoming connections to a server
        - Social: Identify all outgoing relationships from a person
          or all incoming relationships to an entity
    """
    @abstractmethod
    def __init__(self):
        """
        Initialize an empty link star structure.
        
        Sets up internal data structures for storing forward and backward
        link connections associated with nodes.
        """
        pass

    @abstractmethod
    def add_link(self, link: AbstractLink) -> None:
        pass

    @abstractmethod
    def neighbors(self, idx: Hashable) -> Iterable[AbstractLink]:
        """
        Get the link star dictionary for a given node.
        
        Args:
            idx: Node identifier
        Returns:
            Iterable of links connected to the node
        """
        pass

    @abstractmethod
    def remove(self, link_from: AbstractLink, link_to: AbstractLink) -> None:
        """
        Remove all links associated with a given node from the star structure.
        
        Args:
            idx: Node identifier
            fws: True to remove from forward star, False for backward star
        """
        pass


class AbstractGraph(AbstractGraphElement):
    """
    Abstract base class for graph data structures.
    
    Provides a comprehensive interface for different types of graphs (static, dynamic, etc.).
    The graph can contain three types of elements:
    
    - **Nodes**: Vertices representing entities, locations, or decision points
    - **Links**: Directed edges connecting nodes, representing relationships or paths
    - **Turns**: Transitions between connected links, useful for modeling movement constraints
    
    This class extends dict to allow storing arbitrary graph-level attributes
    and metadata. Concrete implementations handle specific storage mechanisms
    and support both static graphs (unchanging topology) and dynamic graphs
    (topology and attributes that change over time).
    
    Graph Structure Principles:
        - Nodes are uniquely identified and can store arbitrary attributes
        - Links are directed and connect exactly two nodes (source → destination)
        - Turns connect two links that share a common node (link1.j == link2.i)
        - All elements support attribute storage with potential time-dependency
    
    Common Use Cases:
        - **Transportation Networks**: Roads, railways, airways, shipping routes
        - **Communication Networks**: Internet topology, telephone networks, data flows
        - **Social Networks**: People connections, organizational relationships
        - **Supply Chain Networks**: Material flows, distribution networks
        - **Workflow Systems**: Process flows, decision trees, state machines
        - **Infrastructure**: Utility networks, pipeline systems
    
    Performance Considerations:
        - Implementations should optimize for their specific use case
        - Static graphs can use simpler, faster data structures
        - Dynamic graphs need efficient temporal indexing
        - Large graphs may require specialized storage (databases, memory mapping)
    
    Note:
        This is an abstract class and cannot be instantiated directly.
        Use concrete implementations like StaticGraph or DynamicGraph.
        
    Example Workflow:
        >>> # Using a concrete implementation
        >>> graph = ConcreteGraph(name="Traffic Network", city="Milano")
        >>> node1 = graph.add_node("intersection_1", x=100, y=200)
        >>> node2 = graph.add_node("intersection_2", x=300, y=200) 
        >>> link = graph.add_link("street_1", "intersection_1", "intersection_2",
        ...                      length=200, speed_limit=50)
        >>> print(f"Graph has {graph.n_nodes} nodes and {graph.n_links} links")
    """

    @abstractmethod
    def __init__(self, **kwargs: Any):
        """
        Initialize an empty graph with optional metadata attributes.
        
        Creates a new graph instance with no nodes, links, or turns.
        Graph-level attributes can be provided to store metadata such as
        name, description, coordinate system, units, or any domain-specific
        information.
        
        Args:
            **kwargs: Arbitrary keyword arguments to store as graph-level attributes
                     Common examples: name, description, crs (coordinate system),
                     units, creation_date, author, version, etc.
                     
        Example:
            >>> graph = ConcreteGraph(name="Highway Network", 
            ...                      crs="EPSG:4326",
            ...                      units="km",
            ...                      description="Major highways in region")
        """
        pass
    
    @property
    @abstractmethod
    def n_links(self) -> int:
        """
        Get the total number of links currently in the graph.
        
        This count includes all links regardless of their attributes or state.
        For dynamic graphs, this represents the current topology.
        
        Returns:
            The count of links currently in the graph (non-negative integer)
            
        Note:
            This should be an O(1) operation in most implementations.
        """
        pass

    @property
    @abstractmethod
    def n_nodes(self) -> int:
        """
        Get the total number of nodes currently in the graph.
        
        This count includes all nodes regardless of their attributes or state.
        For dynamic graphs, this represents the current topology.
        
        Returns:
            The count of nodes currently in the graph (non-negative integer)
            
        Note:
            This should be an O(1) operation in most implementations.
        """
        pass

    @property
    @abstractmethod
    def n_turns(self) -> int:
        """
        Get the total number of turns currently in the graph.
        
        This count includes all turns regardless of their attributes or state.
        Not all graphs use turns - some may always return 0.
        
        Returns:
            The count of turns currently in the graph (non-negative integer)
            
        Note:
            This should be an O(1) operation in most implementations.
            May return 0 if the graph implementation doesn't support turns.
        """
        pass
    
    @abstractmethod
    def get_links(self) -> Iterable[AbstractLink]:
        """
        Get an iterable of all links in the graph.
        
        Provides access to all link objects for iteration, filtering, or analysis.
        The iteration order is implementation-dependent and may not be consistent
        across calls for dynamic graphs.
        
        Returns:
            An iterable (list, generator, etc.) containing all AbstractLink objects
            
        Performance:
            Should be efficient for iteration. May be O(n) space/time where n is link count.
            
        Example:
            >>> for link in graph.get_links():
            ...     if link.get_value("capacity") > 100:
            ...         print(f"High capacity link: {link.idx}")
        """
        pass

    @abstractmethod
    def get_nodes(self) -> Iterable[AbstractNode]:
        """
        Get an iterable of all nodes in the graph.
        
        Provides access to all node objects for iteration, filtering, or analysis.
        The iteration order is implementation-dependent and may not be consistent
        across calls for dynamic graphs.
        
        Returns:
            An iterable (list, generator, etc.) containing all AbstractNode objects
            
        Performance:
            Should be efficient for iteration. May be O(n) space/time where n is node count.
            
        Example:
            >>> for node in graph.get_nodes():
            ...     x, y = node.get_value("x"), node.get_value("y")
            ...     print(f"Node {node.idx} at ({x}, {y})")
        """
        pass

    @abstractmethod
    def get_turns(self) -> Iterable[AbstractTurn]:
        """
        Get an iterable of all turns in the graph.
        
        Provides access to all turn objects for iteration, filtering, or analysis.
        May return an empty iterable if the graph doesn't support turns.
        
        Returns:
            An iterable (list, generator, etc.) containing all AbstractTurn objects
            
        Performance:
            Should be efficient for iteration. May be O(n) space/time where n is turn count.
            
        Example:
            >>> for turn in graph.get_turns():
            ...     if not turn.get_value("allowed", True):
            ...         print(f"Prohibited turn: {turn.idx}")
        """
        pass
    
    def apply_links(self, fn: Callable[[AbstractLink], None]):
        """
        Apply a function to all links in the graph.
        
        Iterates through all links and applies the given function to each one.
        This provides a convenient way to perform bulk operations, transformations,
        or analysis on all links without manually iterating.
        
        Args:
            fn: Function that takes an AbstractLink and returns None
                The function should not modify the graph structure during iteration
                
        Performance:
            O(n) where n is the number of links, plus the cost of fn for each link
            
        Example:
            >>> # Set default speed limit for all links
            >>> def set_speed_limit(link):
            ...     if not link.get_value("speed_limit"):
            ...         link.set_value("speed_limit", 50)
            >>> graph.apply_links(set_speed_limit)
            
            >>> # Calculate total network length
            >>> total_length = 0
            >>> def sum_length(link):
            ...     nonlocal total_length
            ...     total_length += link.get_value("length", 0)
            >>> graph.apply_links(sum_length)
        """
        for link in self.get_links():
            fn(link)
    
    def apply_nodes(self, fn: Callable[[AbstractNode], None]):
        """
        Apply a function to all nodes in the graph.
        
        Iterates through all nodes and applies the given function to each one.
        This provides a convenient way to perform bulk operations, transformations,
        or analysis on all nodes without manually iterating.
        
        Args:
            fn: Function that takes an AbstractNode and returns None
                The function should not modify the graph structure during iteration
                
        Performance:
            O(n) where n is the number of nodes, plus the cost of fn for each node
            
        Example:
            >>> # Initialize elevation for nodes that don't have it
            >>> def init_elevation(node):
            ...     if not node.get_value("elevation"):
            ...         node.set_value("elevation", 0.0)
            >>> graph.apply_nodes(init_elevation)
            
            >>> # Find bounding box of all nodes
            >>> min_x = min_y = float('inf')
            >>> max_x = max_y = float('-inf')
            >>> def update_bounds(node):
            ...     nonlocal min_x, min_y, max_x, max_y
            ...     x, y = node.get_value("x"), node.get_value("y")
            ...     min_x, max_x = min(min_x, x), max(max_x, x)
            ...     min_y, max_y = min(min_y, y), max(max_y, y)
            >>> graph.apply_nodes(update_bounds)
        """
        for node in self.get_nodes():
            fn(node)

    def apply_turns(self, fn: Callable[[AbstractTurn], None]):
        """
        Apply a function to all turns in the graph.
        
        Iterates through all turns and applies the given function to each one.
        This provides a convenient way to perform bulk operations, transformations,
        or analysis on all turns without manually iterating.
        
        Args:
            fn: Function that takes an AbstractTurn and returns None
                The function should not modify the graph structure during iteration
                
        Performance:
            O(n) where n is the number of turns, plus the cost of fn for each turn
            
        Example:
            >>> # Set default turn cost for turns that don't have it
            >>> def set_default_cost(turn):
            ...     if not turn.get_value("cost"):
            ...         turn.set_value("cost", 5.0)  # Default 5 second delay
            >>> graph.apply_turns(set_default_cost)
            
            >>> # Count prohibited turns
            >>> prohibited_count = 0
            >>> def count_prohibited(turn):
            ...     nonlocal prohibited_count
            ...     if not turn.get_value("allowed", True):
            ...         prohibited_count += 1
            >>> graph.apply_turns(count_prohibited)
        """
        for turn in self.get_turns():
            fn(turn)

    @abstractmethod
    def add_link(self, idx: Hashable, i: Hashable, j: Hashable, **kwargs: dict[Hashable,Any]) -> AbstractLink:
        """
        Add a new link to the graph connecting two existing nodes.
        
        Creates a directed edge from node i to node j with the specified identifier.
        Both source and destination nodes should already exist in the graph.
        The link identifier must be unique among all links.
        
        Args:
            idx: Unique identifier for the new link (must be hashable and unique)
            i: Source (origin) node identifier (must exist in graph)
            j: Destination (target) node identifier (must exist in graph)
            **kwargs: Additional attributes for the link
                     (e.g., length=100, capacity=50, cost=10.5, speed_limit=60)
            
        Returns:
            The newly created and added AbstractLink object
            
        Raises:
            ValueError: If idx already exists, or if i or j nodes don't exist
            TypeError: If idx is not hashable
            
        Example:
            >>> link = graph.add_link("highway_1", "city_A", "city_B",
            ...                      length=250.5, lanes=4, toll=True)
            >>> print(f"Added link {link.idx}: {link.i} → {link.j}")
        """
        pass

    @abstractmethod
    def add_node(self, idx: Hashable, **kwargs: Any) -> AbstractNode:
        """
        Add a new node to the graph with the specified identifier.
        
        Creates a vertex in the graph with the given unique identifier.
        The node can store arbitrary attributes for domain-specific data.
        
        Args:
            idx: Unique identifier for the new node (must be hashable and unique)
            **kwargs: Additional attributes for the node
                     (e.g., x=100, y=200, name="Main St", capacity=500)
            
        Returns:
            The newly created and added AbstractNode object
            
        Raises:
            ValueError: If idx already exists in the graph
            TypeError: If idx is not hashable
            
        Example:
            >>> node = graph.add_node("intersection_1", 
            ...                      x=125.0, y=250.0,
            ...                      name="Main & Oak",
            ...                      traffic_lights=True)
            >>> print(f"Added node {node.idx} at ({node.get_value('x')}, {node.get_value('y')})")
        """
        pass

    @abstractmethod
    def add_turn(self, idx: Hashable, in_link: Hashable, out_link: Hashable, **kwargs: Any) -> AbstractTurn:
        """
        Add a new turn to the graph by specifying link identifiers.
        
        Creates a turn movement from the incoming link to the outgoing link.
        Both links should already exist in the graph and should be properly
        connected (out_link.i should equal in_link.j).
        
        Args:
            idx: Unique identifier for the new turn (must be hashable and unique)
            in_link: Identifier of the incoming link (must exist in graph)
            out_link: Identifier of the outgoing link (must exist in graph)
            **kwargs: Additional attributes for the turn
                     (e.g., cost=5.0, delay=3.5, allowed=True, turn_type="left")
            
        Returns:
            The newly created and added AbstractTurn object
            
        Raises:
            ValueError: If idx already exists, or if links don't exist or aren't connected
            TypeError: If idx is not hashable
            
        Example:
            >>> turn = graph.add_turn("left_turn_1", "north_approach", "west_exit",
            ...                      cost=15.0, turn_type="left", 
            ...                      signal_protected=True)
            >>> print(f"Added turn {turn.idx}: {turn.in_link} ⤷ {turn.out_link}")
        """
        pass

    @abstractmethod
    def get_link(self, idx: Hashable) -> Optional[AbstractLink]:
        """
        Retrieve a link by its unique identifier.
        
        Performs a lookup to find the link with the specified identifier.
        This is typically an O(1) operation in hash-based implementations.
        
        Args:
            idx: The unique identifier of the link to retrieve
            
        Returns:
            The AbstractLink object with the specified identifier,
            or None if no such link exists in the graph
            
        Example:
            >>> link = graph.get_link("highway_101")
            >>> if link:
            ...     print(f"Found link: {link.i} → {link.j}")
            ...     capacity = link.get_value("capacity")
            ... else:
            ...     print("Link not found")
        """
        pass

    @abstractmethod
    def get_link_ij(self, i: Hashable, j: Hashable) -> AbstractLink | None:
        """
        Retrieve link connecting node i to node j.

        Performs a lookup to find the link that connects the specified source node (i) to the specified destination node (j). This is useful for graphs that allow multiple links between the same
        pair of nodes (multigraphs). The method should return a single link if it exists, or None if no such link exists.
        Args:
            i: The identifier of the source node
            j: The identifier of the destination node

        Returns:
            The AbstractLink object connecting i to j, or None if no such link exists
        
        """
        pass

    @abstractmethod
    def get_node(self, idx: Hashable) -> Optional[AbstractNode]:
        """
        Retrieve a node by its unique identifier.
        
        Performs a lookup to find the node with the specified identifier.
        This is typically an O(1) operation in hash-based implementations.
        
        Args:
            idx: The unique identifier of the node to retrieve
            
        Returns:
            The AbstractNode object with the specified identifier,
            or None if no such node exists in the graph
            
        Example:
            >>> node = graph.get_node("intersection_1")
            >>> if node:
            ...     x, y = node.get_value("x"), node.get_value("y")
            ...     print(f"Node {node.idx} at coordinates ({x}, {y})")
            ... else:
            ...     print("Node not found")
        """
        pass

    @abstractmethod
    def get_turn(self, idx_or_in_link: Hashable, out_link: Optional[Hashable] = None) -> Optional[AbstractTurn]:
        """
        Retrieve a turn by identifier or by link combination.
        
        This method supports two different calling patterns:
        1. **By turn ID**: get_turn(turn_idx) - Direct lookup by turn identifier
        2. **By link pair**: get_turn(in_link_idx, out_link_idx) - Find turn connecting two links
        
        The link pair approach is useful when you know the movement you're interested
        in but don't know the specific turn identifier.
        
        Args:
            idx_or_in_link: Either the turn identifier (when out_link is None)
                            or the incoming link identifier (when out_link is provided)
            out_link: The outgoing link identifier (required for link-pair lookup)
                     None for direct turn ID lookup
            
        Returns:
            The AbstractTurn object that matches the criteria,
            or None if no such turn exists
            
        Example:
            >>> # Method 1: Direct turn lookup
            >>> turn = graph.get_turn("left_turn_1")
            >>> 
            >>> # Method 2: Find turn by link combination  
            >>> turn = graph.get_turn("north_approach", "west_exit")
            >>> if turn:
            ...     cost = turn.get_value("cost", 0)
            ...     print(f"Turn cost: {cost}")
            ... else:
            ...     print("Turn not found or not allowed")
        """
        pass

    @property
    def type(self) -> str:
        """
        Get the type of the graph element.
        
        Returns the stored type or falls back to the class name if not set.
        This property is automatically set by subclasses but can be overridden.
        
        Returns:
            str: The type identifier of this graph element
        """
        return "graph"

    def load_nodes(self, records: list[dict[str, Any]], idx: str = "id", use_data:bool=True):
        """
        Load nodes from a list of records (dictionaries).
        
        Args:
            records: A list of dictionaries containing node data
            idx: The key in each dictionary to use as the node identifier
            use_data: Whether to use the additional data in the dictionary
            
        Example:
            >>> node_records = [
            ...     {"id": "node_1", "x": 0, "y": 0},
            ...     {"id": "node_2", "x": 1, "y": 1},
            ... ]
            >>> graph.load_nodes(node_records)

        """        
        for params in records:
            _idx=params.pop(idx)
            if use_data:
                params.pop("idx",None)
                self.add_node(idx=_idx,**params)
            else:
                self.add_node(idx=_idx)
            

    def load_links(self, records: list[dict[str, Any]], idx: str = "id", i: str = "i", j: str = "j", geometry: str = "geometry", create_nodes: bool=False, use_data: bool =True):
        for params in records:    
            _idx = params.pop(idx)
            _i = params.pop(i)
            _j = params.pop(j)        
            _geometry = params.pop(geometry, None)
            if create_nodes:
                if _geometry is not None:
                    gi = _geometry.coords[0]
                    kw: dict[str, Any] = {"idx": _i, "x": gi[0], "y": gi[1], geometry: Point(gi)}
                    self.add_node(**kw)                                        

                    gj = _geometry.coords[-1]                    
                    kw = {"idx": _j, "x": gj[0], "y": gj[1], geometry: Point(gj)}
                    self.add_node(**kw)                    
                else:
                    self.add_node(idx=_i)
                    self.add_node(idx=_j)
            if use_data:
                params.pop("idx",None)
                params.pop("i",None)
                params.pop("j",None)                
                if _geometry is not None:
                    self.add_link(idx=_idx,i=_i,j=_j,geometry=_geometry, **params)
                else:
                    self.add_link(idx=_idx,i=_i,j=_j, **params)
            else:
                if _geometry is not None:
                    self.add_link(idx=_idx,i=_i,j=_j,geometry=_geometry)
                else:
                    self.add_link(idx=_idx,i=_i,j=_j)


    def load_turns(self, records: list[dict[str, Any]], idx: str = "id", in_link: str = "in_link", out_link: str = "to_link", use_data: bool =True):
        for i, params in enumerate(records):  
            _idx = params.pop(idx, i)
            _in_link = params.pop(in_link, None)
            _out_link = params.pop(out_link, None)
            if _in_link is None or _out_link is None:
                warnings.warn(f"Cannot create turn {_idx}: missing link value(s) {_in_link} or {_out_link}")
                continue
            if self.get_link(_in_link) is None or self.get_link(_out_link) is None:
                warnings.warn(f"Cannot create turn {_idx}: missing link(s) {_in_link} or {_out_link}")
                continue
            if use_data:
                self.add_turn(idx=_idx,in_link=_in_link,out_link=_out_link, **params)
            else:
                self.add_turn(idx=_idx,in_link=_in_link,out_link=_out_link)

    def load_turns_ij(self, records: list[dict[str, Any]], idx: str = "id", from_node: str = "from_node", via_node: str = "via_node", to_node: str = "to_node", use_data: bool =True):
        for i, params in enumerate(records):  
            _idx = params.pop(idx, i)
            _from_node = params.pop(from_node, None)
            _via_node = params.pop(via_node, None)
            _to_node = params.pop(to_node, None)
            if _from_node is None or _via_node is None or _to_node is None:
                warnings.warn(f"Cannot create turn {_idx}: missing node value(s) {_from_node}, {_via_node} or {_to_node}")
                continue
            _in_link = self.get_link_ij(i=_from_node,j=_via_node)
            _out_link = self.get_link_ij(i=_via_node,j=_to_node)
            if _in_link is None or _out_link is None:
                warnings.warn(f"Cannot create turn {_idx}: missing link(s) {_from_node}->{_via_node} or {_via_node}->{_to_node}")
                continue
            if use_data:
                self.add_turn(idx=_idx, in_link=_in_link["idx"], out_link=_out_link["idx"], **params)
            else:
                self.add_turn(idx=_idx, in_link=_in_link["idx"], out_link=_out_link["idx"])
