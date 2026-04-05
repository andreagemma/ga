"""
Performance tests for Static Graph operations.

This module tests the performance characteristics of StaticGraph operations
with emphasis on scalability and timing for large graphs.
"""
import os
import sys
import unittest
import time
import random
from typing import List, Tuple
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))
    
from ga.graphs.static_graph.static_graph import (
    StaticGraph, StaticNode, StaticLink, StaticTurn
)


class TestStaticGraphPerformance(unittest.TestCase):
    """Test performance characteristics of StaticGraph operations."""

    def setUp(self):
        """Set up test fixtures with different graph sizes."""
        self.small_graph = StaticGraph(name="small_test")
        self.medium_graph = StaticGraph(name="medium_test")
        self.large_graph = StaticGraph(name="large_test")
        
        # Populate graphs with different sizes
        self._populate_graph(self.small_graph, n_nodes=100, n_links=200, n_turns=50)
        self._populate_graph(self.medium_graph, n_nodes=1000, n_links=2000, n_turns=500)
        self._populate_graph(self.large_graph, n_nodes=5000, n_links=10000, n_turns=2000)

    def _populate_graph(self, graph: StaticGraph, n_nodes: int, n_links: int, n_turns: int):
        """Populate a graph with specified number of elements."""
        # Add nodes
        for i in range(n_nodes):
            graph.add_node(f"node_{i}", x=random.uniform(0, 100), y=random.uniform(0, 100))
        
        # Add links (ensuring valid node connections)
        link_count = 0
        for i in range(min(n_links, n_nodes - 1)):
            # Create a connected graph backbone first
            graph.add_link(f"link_{link_count}", f"node_{i}", f"node_{i+1}", 
                         length=random.uniform(1, 10), capacity=random.randint(10, 100))
            link_count += 1
        
        # Add remaining links randomly
        nodes = list(range(n_nodes))        
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        while link_count < n_links:
            i_node, j_node = random.sample(nodes, 2)
            graph.add_link(f"link_{link_count}", f"node_{i_node}", f"node_{j_node}",
                         length=random.uniform(1, 10), capacity=random.randint(10, 100))
            link_count += 1
        
        # Add turns randomly between existing links
        existing_links = [f"link_{i}" for i in range(min(n_links, graph.n_links))]
        random.shuffle(existing_links)
        turns = existing_links[:min(n_turns+1, len(existing_links)-1)]
        for i in range(len(turns)-1):
            in_link, out_link = turns[i], turns[i+1]
            try:
                graph.add_turn(f"turn_{i}", in_link, out_link,
                             cost=random.uniform(0, 20), delay=random.uniform(0, 5))
            except:
                # Skip if turn already exists or other issues
                pass

    def _time_operation(self, operation, *args, **kwargs):
        """Time a single operation and return execution time."""
        start_time = time.perf_counter()
        result = operation(*args, **kwargs)
        end_time = time.perf_counter()
        return end_time - start_time, result

    def test_get_node_performance_small(self):
        """Test get_node performance on small graph."""
        node_ids = [f"node_{i}" for i in range(0, 100, 10)]  # Sample 10 nodes
        
        total_time = 0
        for node_id in node_ids:
            exec_time, node = self._time_operation(self.small_graph.get_node, node_id)
            total_time += exec_time
            self.assertIsNotNone(node)
        
        avg_time = total_time / len(node_ids)
        print(f"Small graph get_node average time: {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
        self.assertLess(avg_time, 0.001, "get_node should be very fast (< 1ms) for small graph")

    def test_get_node_performance_large(self):
        """Test get_node performance on large graph."""
        node_ids = [f"node_{i}" for i in range(0, 5000, 100)]  # Sample 50 nodes
        
        total_time = 0
        for node_id in node_ids:
            exec_time, node = self._time_operation(self.large_graph.get_node, node_id)
            total_time += exec_time
            self.assertIsNotNone(node)
        
        avg_time = total_time / len(node_ids)
        print(f"Large graph get_node average time: {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
        self.assertLess(avg_time, 0.001, "get_node should remain fast (< 1ms) even for large graph")

    def test_get_link_performance_small(self):
        """Test get_link performance on small graph."""
        link_ids = [f"link_{i}" for i in range(0, min(200, self.small_graph.n_links), 20)]
        
        total_time = 0
        for link_id in link_ids:
            exec_time, link = self._time_operation(self.small_graph.get_link, link_id)
            total_time += exec_time
            self.assertIsNotNone(link)
        
        avg_time = total_time / len(link_ids)
        print(f"Small graph get_link average time: {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
        self.assertLess(avg_time, 0.001, "get_link should be very fast (< 1ms) for small graph")

    def test_get_link_performance_large(self):
        """Test get_link performance on large graph."""
        link_ids = [f"link_{i}" for i in range(0, min(10000, self.large_graph.n_links), 200)]
        
        total_time = 0
        for link_id in link_ids:
            exec_time, link = self._time_operation(self.large_graph.get_link, link_id)
            total_time += exec_time
            self.assertIsNotNone(link)
        
        avg_time = total_time / len(link_ids)
        print(f"Large graph get_link average time: {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
        self.assertLess(avg_time, 0.001, "get_link should remain fast (< 1ms) even for large graph")

    def test_get_turn_performance_by_id(self):
        """Test get_turn by ID performance."""
        turn_ids = [f"turn_{i}" for i in range(0, min(100, self.medium_graph.n_turns), 10)]
        
        total_time = 0
        successful_lookups = 0
        for turn_id in turn_ids:
            exec_time, turn = self._time_operation(self.medium_graph.get_turn, turn_id)
            total_time += exec_time
            if turn is not None:
                successful_lookups += 1
        
        if successful_lookups > 0:
            avg_time = total_time / successful_lookups
            print(f"Medium graph get_turn (by ID) average time: {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
            self.assertLess(avg_time, 0.001, "get_turn by ID should be fast (< 1ms)")

    def test_get_turn_performance_by_links(self):
        """Test get_turn by link combination performance."""
        # Get some existing links to test turn lookups
        links = list(self.medium_graph.get_links())[:20]  # Sample first 20 links
        
        total_time = 0
        test_count = 0
        for i in range(0, len(links)-1, 2):
            in_link = links[i].idx
            out_link = links[i+1].idx
            exec_time, turn = self._time_operation(self.medium_graph.get_turn, in_link, out_link)
            total_time += exec_time
            test_count += 1
        
        if test_count > 0:
            avg_time = total_time / test_count
            print(f"Medium graph get_turn (by links) average time: {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
            self.assertLess(avg_time, 0.002, "get_turn by links should be reasonably fast (< 2ms)")

    def test_add_node_performance(self):
        """Test add_node performance."""
        temp_graph = StaticGraph(name="temp_test")
        n_additions = 1000
        
        start_time = time.perf_counter()
        for i in range(n_additions):
            temp_graph.add_node(f"perf_node_{i}", x=i, y=i*2, value=i**2)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time = total_time / n_additions
        
        print(f"add_node average time (1000 additions): {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
        self.assertLess(avg_time, 0.001, "add_node should be fast (< 1ms per addition)")
        self.assertEqual(temp_graph.n_nodes, n_additions)

    def test_add_link_performance(self):
        """Test add_link performance."""
        temp_graph = StaticGraph(name="temp_test")
        
        # Pre-populate with nodes
        n_nodes = 1000
        for i in range(n_nodes):
            temp_graph.add_node(f"node_{i}")
        
        # Time link additions
        n_additions = 800
        start_time = time.perf_counter()
        for i in range(n_additions):
            i_node = i
            j_node = i+1
            if i_node != j_node:  # Avoid self-loops
                temp_graph.add_link(f"perf_link_{i}", f"node_{i_node}", f"node_{j_node}", 
                                  weight=i, capacity=i*10)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time = total_time / n_additions
        
        print(f"add_link average time (800 additions): {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
        self.assertLess(avg_time, 0.002, "add_link should be reasonably fast (< 2ms per addition)")

    def test_add_turn_performance(self):
        """Test add_turn performance."""
        temp_graph = StaticGraph(name="temp_test")
        
        # Pre-populate with nodes and links
        n_nodes = 200
        for i in range(n_nodes):
            temp_graph.add_node(f"node_{i}")
        
        links = []
        for i in range(300):
            i_node = i
            j_node = i+1
            if i_node != j_node:
                link_id = f"link_{i}"
                temp_graph.add_link(link_id, f"node_{i_node}", f"node_{j_node}")
                links.append(link_id)
        
        # Time turn additions
        n_additions = 200
        start_time = time.perf_counter()
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        random.shuffle(links)
        for i in range(min(n_additions+1, len(links)-1)):
            in_link = links[i]
            out_link = links[i+1]
            try:
                temp_graph.add_turn(f"perf_turn_{i}", in_link, out_link, cost=i*0.5)
            except:
                pass  # Skip duplicates or other issues
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time = total_time / n_additions
        
        print(f"add_turn average time (200 additions): {avg_time:.6f}s - (total_time: {total_time:.6f}s)")
        self.assertLess(avg_time, 0.003, "add_turn should be reasonably fast (< 3ms per addition)")

    def test_iteration_performance(self):
        """Test performance of iteration methods."""
        # Test get_nodes iteration
        start_time = time.perf_counter()
        node_count = 0
        for node in self.large_graph.get_nodes():
            node_count += 1
        end_time = time.perf_counter()
        nodes_time = end_time - start_time
        
        # Test get_links iteration  
        start_time = time.perf_counter()
        link_count = 0
        for link in self.large_graph.get_links():
            link_count += 1
        end_time = time.perf_counter()
        links_time = end_time - start_time
        
        # Test get_turns iteration
        start_time = time.perf_counter()
        turn_count = 0
        for turn in self.large_graph.get_turns():
            turn_count += 1
        end_time = time.perf_counter()
        turns_time = end_time - start_time
        
        print(f"Large graph iteration times:")
        print(f"  get_nodes ({node_count} nodes): {nodes_time:.4f}s")
        print(f"  get_links ({link_count} links): {links_time:.4f}s") 
        print(f"  get_turns ({turn_count} turns): {turns_time:.4f}s")
        
        # Iteration should be reasonably fast even for large graphs
        self.assertLess(nodes_time, 0.1, "Node iteration should be fast")
        self.assertLess(links_time, 0.1, "Link iteration should be fast")
        self.assertLess(turns_time, 0.1, "Turn iteration should be fast")

    def test_element_value_operations_performance(self):
        """Test performance of get_value and set_value operations on elements."""
        # Get a sample of elements
        nodes = list(self.medium_graph.get_nodes())[:100]
        links = list(self.medium_graph.get_links())[:100] 
        turns = list(self.medium_graph.get_turns())[:50]
        
        # Test node value operations
        start_time = time.perf_counter()
        for node in nodes:
            # Get existing value
            x_val = node.get_value("x")
            # Set new value
            node.set_value("test_attr", x_val * 2)
            # Get new value
            test_val = node.get_value("test_attr")
        end_time = time.perf_counter()
        node_ops_time = end_time - start_time
        
        # Test link value operations
        start_time = time.perf_counter()
        for link in links:
            # Get existing value
            length_val = link.get_value("length", 1.0)
            # Set new value
            link.set_value("test_weight", length_val * 1.5)
            # Get new value
            weight_val = link.get_value("test_weight")
        end_time = time.perf_counter()
        link_ops_time = end_time - start_time
        
        # Test turn value operations
        start_time = time.perf_counter()
        for turn in turns:
            # Get existing value
            cost_val = turn.get_value("cost", 0)
            # Set new value
            turn.set_value("test_penalty", cost_val + 5)
            # Get new value
            penalty_val = turn.get_value("test_penalty")
        end_time = time.perf_counter()
        turn_ops_time = end_time - start_time
        
        print(f"Element value operations performance:")
        print(f"  Node operations (100 elements): {node_ops_time:.6f}s")
        print(f"  Link operations (100 elements): {link_ops_time:.6f}s")
        print(f"  Turn operations ({len(turns)} elements): {turn_ops_time:.6f}s")
        
        # Value operations should be very fast
        avg_node_time = node_ops_time / (len(nodes) * 3)  # 3 operations per node
        avg_link_time = link_ops_time / (len(links) * 3)  # 3 operations per link
        
        self.assertLess(avg_node_time, 0.0001, "Node value operations should be very fast")
        self.assertLess(avg_link_time, 0.0001, "Link value operations should be very fast")

    def test_scalability_comparison(self):
        """Test that operations scale reasonably with graph size."""
        graphs = [
            ("small", self.small_graph),
            ("medium", self.medium_graph), 
            ("large", self.large_graph)
        ]
        
        results = {}
        
        for name, graph in graphs:
            # Test get_node time
            node_ids = [f"node_{i}" for i in range(0, min(graph.n_nodes, 1000), 100)]
            start_time = time.perf_counter()
            for node_id in node_ids:
                graph.get_node(node_id)
            end_time = time.perf_counter()
            get_node_time = end_time - start_time
            
            # Test get_link time  
            link_ids = [f"link_{i}" for i in range(0, min(graph.n_links, 1000), 100)]
            start_time = time.perf_counter()
            for link_id in link_ids:
                graph.get_link(link_id)
            end_time = time.perf_counter()
            get_link_time = end_time - start_time
            
            results[name] = {
                'nodes': graph.n_nodes,
                'links': graph.n_links,
                'get_node_time': get_node_time,
                'get_link_time': get_link_time
            }
        
        # Print results
        print("\nScalability comparison:")
        for name, data in results.items():
            print(f"{name:6}: {data['nodes']:5} nodes, {data['links']:5} links, "
                  f"get_node: {data['get_node_time']:.6f}s, get_link: {data['get_link_time']:.6f}s")
        
        # Check that performance doesn't degrade too badly
        # (This is a basic check - more sophisticated analysis could be done)
        small_node_time = results['small']['get_node_time']
        large_node_time = results['large']['get_node_time']
        
        # Performance shouldn't degrade by more than 10x for 50x size increase
        if small_node_time > 0:  # Avoid division by zero
            degradation_factor = large_node_time / small_node_time
            self.assertLess(degradation_factor, 10, 
                           f"Performance degradation too high: {degradation_factor:.1f}x")


if __name__ == "__main__":
    # Run with verbose output to see timing information
    unittest.main(verbosity=2)