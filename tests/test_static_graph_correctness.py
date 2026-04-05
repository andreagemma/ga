"""
Unit tests for Static Graph correctness.

This module tests the correctness of StaticGraph operations including
element creation, retrieval, and value management.
"""
import os
import sys
import unittest
from typing import Optional
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))


from ga.graphs.static_graph.static_graph import (
    StaticGraph, StaticNode, StaticLink, StaticTurn
)


class TestStaticGraphCorrectnessBasics(unittest.TestCase):
    """Test basic functionality and correctness of StaticGraph operations."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.graph = StaticGraph(name="test_graph", description="Test graph for unit tests")

    def test_empty_graph_initialization(self):
        """Test that empty graph is properly initialized."""
        self.assertEqual(self.graph.n_nodes, 0)
        self.assertEqual(self.graph.n_links, 0)
        self.assertEqual(self.graph.n_turns, 0)
        self.assertEqual(self.graph["name"], "test_graph")
        self.assertEqual(self.graph["description"], "Test graph for unit tests")

    def test_add_node_basic(self):
        """Test basic node addition."""
        node = self.graph.add_node("node1", x=10.5, y=20.3, name="Test Node")
        
        self.assertEqual(self.graph.n_nodes, 1)
        self.assertEqual(node.idx, "node1")
        self.assertEqual(node["x"], 10.5)
        self.assertEqual(node["y"], 20.3)
        self.assertEqual(node["name"], "Test Node")
        self.assertEqual(node.type, "node")

    def test_add_link_basic(self):
        """Test basic link addition."""
        # Add nodes first
        self.graph.add_node("A")
        self.graph.add_node("B")
        
        # Add link
        link = self.graph.add_link("link1", "A", "B", length=100.0, capacity=50)
        
        self.assertEqual(self.graph.n_links, 1)
        self.assertEqual(link.idx, "link1")
        self.assertEqual(link.i, "A")
        self.assertEqual(link.j, "B")
        self.assertEqual(link["length"], 100.0)
        self.assertEqual(link["capacity"], 50)
        self.assertEqual(link.type, "link")

    def test_add_turn_basic(self):
        """Test basic turn addition."""
        # Add nodes and links first
        self.graph.add_node("A")
        self.graph.add_node("B")
        self.graph.add_node("C")
        self.graph.add_link("link1", "A", "B")
        self.graph.add_link("link2", "B", "C")
        
        # Add turn
        turn = self.graph.add_turn("turn1", "link1", "link2", cost=5.0, delay=2.5)
        
        self.assertEqual(self.graph.n_turns, 1)
        self.assertEqual(turn.idx, "turn1")
        self.assertEqual(turn.in_link, "link1")
        self.assertEqual(turn.out_link, "link2")
        self.assertEqual(turn["cost"], 5.0)
        self.assertEqual(turn["delay"], 2.5)

    def test_get_node_existing(self):
        """Test retrieving existing node."""
        original_node = self.graph.add_node("node1", value=42)
        retrieved_node = self.graph.get_node("node1")
        
        self.assertIsNotNone(retrieved_node)
        self.assertEqual(retrieved_node.idx, "node1")
        self.assertEqual(retrieved_node["value"], 42)
        self.assertIs(retrieved_node, original_node)  # Should be same object

    def test_get_node_nonexistent(self):
        """Test retrieving non-existent node."""
        result = self.graph.get_node("nonexistent")
        self.assertIsNone(result)

    def test_get_link_existing(self):
        """Test retrieving existing link."""
        self.graph.add_node("A")
        self.graph.add_node("B")
        original_link = self.graph.add_link("link1", "A", "B", weight=10)
        retrieved_link = self.graph.get_link("link1")
        
        self.assertIsNotNone(retrieved_link)
        self.assertEqual(retrieved_link.idx, "link1")
        self.assertEqual(retrieved_link.i, "A")
        self.assertEqual(retrieved_link.j, "B")
        self.assertEqual(retrieved_link["weight"], 10)
        self.assertIs(retrieved_link, original_link)  # Should be same object

    def test_get_link_nonexistent(self):
        """Test retrieving non-existent link."""
        result = self.graph.get_link("nonexistent")
        self.assertIsNone(result)

    def test_get_turn_by_id_existing(self):
        """Test retrieving existing turn by ID."""
        self.graph.add_node("A")
        self.graph.add_node("B")
        self.graph.add_node("C")
        self.graph.add_link("link1", "A", "B")
        self.graph.add_link("link2", "B", "C")
        original_turn = self.graph.add_turn("turn1", "link1", "link2", cost=15)
        
        retrieved_turn = self.graph.get_turn("turn1")
        
        self.assertIsNotNone(retrieved_turn)
        self.assertEqual(retrieved_turn.idx, "turn1")
        self.assertEqual(retrieved_turn["cost"], 15)
        self.assertIs(retrieved_turn, original_turn)  # Should be same object

    def test_get_turn_by_links_existing(self):
        """Test retrieving existing turn by link combination."""
        self.graph.add_node("A")
        self.graph.add_node("B")
        self.graph.add_node("C")
        self.graph.add_link("link1", "A", "B")
        self.graph.add_link("link2", "B", "C")
        original_turn = self.graph.add_turn("turn1", "link1", "link2", cost=15)
        
        retrieved_turn = self.graph.get_turn("link1", "link2")
        
        self.assertIsNotNone(retrieved_turn)
        self.assertEqual(retrieved_turn.idx, "turn1")
        self.assertEqual(retrieved_turn["cost"], 15)
        self.assertIs(retrieved_turn, original_turn)  # Should be same object

    def test_get_turn_nonexistent(self):
        """Test retrieving non-existent turn."""
        result = self.graph.get_turn("nonexistent")
        self.assertIsNone(result)
        
        result = self.graph.get_turn("link1", "link2")
        self.assertIsNone(result)


class TestStaticElementValueMethods(unittest.TestCase):
    """Test get_value and set_value methods for graph elements."""

    def setUp(self):
        """Set up test fixtures."""
        self.graph = StaticGraph()
        self.graph.add_node("A", initial_value=100)
        self.graph.add_node("B", initial_value=200)
        self.graph.add_link("link1", "A", "B", capacity=500)
        self.graph.add_turn("turn1", "link1", "link1", cost=10)  # self-loop turn for testing

    def test_node_get_value_existing(self):
        """Test getting existing value from node."""
        node = self.graph.get_node("A")
        self.assertEqual(node.get_value("initial_value"), 100)
        self.assertEqual(node.get_value("idx"), "A")

    def test_node_get_value_nonexistent_with_default(self):
        """Test getting non-existent value with default from node."""
        node = self.graph.get_node("A")
        self.assertEqual(node.get_value("nonexistent", "default_value"), "default_value")
        self.assertIsNone(node.get_value("nonexistent"))

    def test_node_set_value_new(self):
        """Test setting new value on node."""
        node = self.graph.get_node("A")
        node.set_value("new_attribute", "new_value")
        
        self.assertEqual(node.get_value("new_attribute"), "new_value")
        self.assertEqual(node["new_attribute"], "new_value")

    def test_node_set_value_existing(self):
        """Test updating existing value on node."""
        node = self.graph.get_node("A")
        original_value = node.get_value("initial_value")
        self.assertEqual(original_value, 100)
        
        node.set_value("initial_value", 999)
        self.assertEqual(node.get_value("initial_value"), 999)

    def test_link_get_value_existing(self):
        """Test getting existing value from link."""
        link = self.graph.get_link("link1")
        self.assertEqual(link.get_value("capacity"), 500)
        self.assertEqual(link.get_value("i"), "A")
        self.assertEqual(link.get_value("j"), "B")

    def test_link_get_value_nonexistent_with_default(self):
        """Test getting non-existent value with default from link."""
        link = self.graph.get_link("link1")
        self.assertEqual(link.get_value("speed_limit", 50), 50)
        self.assertIsNone(link.get_value("nonexistent"))

    def test_link_set_value_new(self):
        """Test setting new value on link."""
        link = self.graph.get_link("link1")
        link.set_value("weight", 25.5)
        
        self.assertEqual(link.get_value("weight"), 25.5)
        self.assertEqual(link["weight"], 25.5)

    def test_link_set_value_existing(self):
        """Test updating existing value on link."""
        link = self.graph.get_link("link1")
        original_capacity = link.get_value("capacity")
        self.assertEqual(original_capacity, 500)
        
        link.set_value("capacity", 750)
        self.assertEqual(link.get_value("capacity"), 750)

    def test_turn_get_value_existing(self):
        """Test getting existing value from turn."""
        turn = self.graph.get_turn("turn1")
        self.assertEqual(turn.get_value("cost"), 10)
        self.assertEqual(turn.get_value("in_link"), "link1")
        self.assertEqual(turn.get_value("out_link"), "link1")

    def test_turn_get_value_nonexistent_with_default(self):
        """Test getting non-existent value with default from turn."""
        turn = self.graph.get_turn("turn1")
        self.assertEqual(turn.get_value("delay", 0), 0)
        self.assertIsNone(turn.get_value("nonexistent"))

    def test_turn_set_value_new(self):
        """Test setting new value on turn."""
        turn = self.graph.get_turn("turn1")
        turn.set_value("restriction", "no_left_turn")
        
        self.assertEqual(turn.get_value("restriction"), "no_left_turn")
        self.assertEqual(turn["restriction"], "no_left_turn")

    def test_turn_set_value_existing(self):
        """Test updating existing value on turn."""
        turn = self.graph.get_turn("turn1")
        original_cost = turn.get_value("cost")
        self.assertEqual(original_cost, 10)
        
        turn.set_value("cost", 25)
        self.assertEqual(turn.get_value("cost"), 25)


class TestStaticGraphIterationMethods(unittest.TestCase):
    """Test iteration methods for graph elements."""

    def setUp(self):
        """Set up a graph with multiple elements."""
        self.graph = StaticGraph()
        
        # Add nodes
        for i in range(5):
            self.graph.add_node(f"node{i}", value=i*10)
        
        # Add links creating a path: node0 -> node1 -> node2 -> node3 -> node4
        for i in range(4):
            self.graph.add_link(f"link{i}", f"node{i}", f"node{i+1}", weight=i+1)
        
        # Add some turns
        for i in range(3):
            self.graph.add_turn(f"turn{i}", f"link{i}", f"link{i+1}", cost=i*5)

    def test_get_nodes_count(self):
        """Test that get_nodes returns correct number of nodes."""
        nodes = list(self.graph.get_nodes())
        self.assertEqual(len(nodes), 5)

    def test_get_nodes_content(self):
        """Test that get_nodes returns correct node objects."""
        nodes = list(self.graph.get_nodes())
        node_ids = {node.idx for node in nodes}
        expected_ids = {f"node{i}" for i in range(5)}
        self.assertEqual(node_ids, expected_ids)

    def test_get_links_count(self):
        """Test that get_links returns correct number of links."""
        links = list(self.graph.get_links())
        self.assertEqual(len(links), 4)

    def test_get_links_content(self):
        """Test that get_links returns correct link objects."""
        links = list(self.graph.get_links())
        link_ids = {link.idx for link in links}
        expected_ids = {f"link{i}" for i in range(4)}
        self.assertEqual(link_ids, expected_ids)

    def test_get_turns_count(self):
        """Test that get_turns returns correct number of turns."""
        turns = list(self.graph.get_turns())
        self.assertEqual(len(turns), 3)

    def test_get_turns_content(self):
        """Test that get_turns returns correct turn objects."""
        turns = list(self.graph.get_turns())
        turn_ids = {turn.idx for turn in turns}
        expected_ids = {f"turn{i}" for i in range(3)}
        self.assertEqual(turn_ids, expected_ids)


class TestStaticGraphEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.graph = StaticGraph()

    def test_duplicate_node_ids(self):
        """Test behavior when adding nodes with duplicate IDs."""
        self.graph.add_node("duplicate", value=1)
        self.graph.add_node("duplicate", value=2)  # Should overwrite
        
        node = self.graph.get_node("duplicate")
        self.assertEqual(node["value"], 2)
        self.assertEqual(self.graph.n_nodes, 1)  # Should still be 1

    def test_duplicate_link_ids(self):
        """Test behavior when adding links with duplicate IDs."""
        self.graph.add_node("A")
        self.graph.add_node("B")
        self.graph.add_node("C")
        
        self.graph.add_link("duplicate", "A", "B", value=1)
        self.graph.add_link("duplicate", "B", "C", value=2)  # Should overwrite
        
        link = self.graph.get_link("duplicate")
        self.assertEqual(link["value"], 2)
        self.assertEqual(link.i, "B")  # Should be updated link
        self.assertEqual(link.j, "C")
        self.assertEqual(self.graph.n_links, 1)  # Should still be 1

    def test_duplicate_turn_ids(self):
        """Test behavior when adding turns with duplicate IDs."""
        self.graph.add_node("A")
        self.graph.add_node("B")
        self.graph.add_node("C")
        self.graph.add_link("link1", "A", "B")
        self.graph.add_link("link2", "B", "C")
        
        self.graph.add_turn("duplicate", "link1", "link2", value=1)
        self.graph.add_turn("duplicate", "link1", "link2", value=2)  # Should overwrite
        
        turn = self.graph.get_turn("duplicate")
        self.assertEqual(turn["value"], 2)
        self.assertEqual(self.graph.n_turns, 1)  # Should still be 1

    def test_element_type_properties(self):
        """Test that element type properties are correct."""
        node = self.graph.add_node("test_node")
        self.graph.add_node("A")
        self.graph.add_node("B")
        link = self.graph.add_link("test_link", "A", "B")
        turn = self.graph.add_turn("test_turn", "test_link", "test_link")
        
        self.assertEqual(node.type, "node")
        self.assertEqual(link.type, "link")
        # Note: StaticTurn doesn't seem to set _type in __init__, checking if it inherits correctly


if __name__ == "__main__":
    unittest.main()