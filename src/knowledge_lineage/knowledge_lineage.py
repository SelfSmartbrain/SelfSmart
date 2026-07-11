"""knowledge_lineage.py

Git-like history tracking for knowledge structures.
Tracks evolution from concepts to theories to mental models to strategies.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class KnowledgeType(str, Enum):
    """Types of knowledge in the lineage."""

    MEMORY = "memory"
    CONCEPT = "concept"
    THEORY = "theory"
    MENTAL_MODEL = "mental_model"
    STRATEGY = "strategy"
    INSIGHT = "insight"


class LineageEventType(str, Enum):
    """Types of lineage events."""

    CREATED = "created"
    DERIVED = "derived"
    MERGED = "merged"
    SPLIT = "split"
    REFINED = "refined"
    DEPRECATED = "deprecated"
    VALIDATED = "validated"


@dataclass
class LineageNode:
    """A node in the knowledge lineage graph."""

    id: str
    knowledge_type: KnowledgeType
    name: str
    content: Dict[str, Any]
    author_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "knowledge_type": self.knowledge_type.value,
            "name": self.name,
            "content": self.content,
            "author_id": self.author_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class LineageEdge:
    """An edge in the knowledge lineage graph."""

    from_id: str
    to_id: str
    event_type: LineageEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class LineageCommit:
    """A commit in the knowledge lineage (like a Git commit)."""

    commit_id: str
    parent_ids: List[str]
    node_id: str
    message: str
    author_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_id": self.commit_id,
            "parent_ids": self.parent_ids,
            "node_id": self.node_id,
            "message": self.message,
            "author_id": self.author_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class KnowledgeLineage:
    """Git-like lineage tracking for knowledge structures."""

    def __init__(self):
        self.nodes: Dict[str, LineageNode] = {}
        self.edges: Dict[str, List[LineageEdge]] = {}  # node_id -> list of edges
        self.commits: Dict[str, LineageCommit] = {}
        self.branches: Dict[str, str] = {}  # branch_name -> commit_id
        self.head: Optional[str] = None  # Current head commit

        # Initialize main branch
        self.branches["main"] = None

        logger.info("KnowledgeLineage initialized")

    def create_node(
        self,
        knowledge_type: KnowledgeType,
        name: str,
        content: Dict[str, Any],
        author_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LineageNode:
        """Create a new knowledge node."""
        node = LineageNode(
            id=str(uuid.uuid4()),
            knowledge_type=knowledge_type,
            name=name,
            content=content,
            author_id=author_id,
            metadata=metadata or {},
        )

        self.nodes[node.id] = node
        self.edges[node.id] = []

        logger.info(f"Created node {node.id}: {name} ({knowledge_type.value})")
        return node

    def commit(
        self,
        node_id: str,
        message: str,
        author_id: str,
        parent_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LineageCommit:
        """Commit a knowledge node to the lineage."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")

        if parent_ids is None:
            parent_ids = [self.head] if self.head else []

        commit = LineageCommit(
            commit_id=str(uuid.uuid4()),
            parent_ids=parent_ids,
            node_id=node_id,
            message=message,
            author_id=author_id,
            metadata=metadata or {},
        )

        self.commits[commit.commit_id] = commit

        # Create edges from parents
        for parent_id in parent_ids:
            if parent_id in self.nodes:
                edge = LineageEdge(
                    from_id=parent_id,
                    to_id=node_id,
                    event_type=LineageEventType.DERIVED,
                )
                self.edges[parent_id].append(edge)

        # Update head
        self.head = commit.commit_id
        self.branches["main"] = commit.commit_id

        logger.info(f"Committed {node_id} as {commit.commit_id}: {message}")
        return commit

    def derive(
        self,
        parent_id: str,
        knowledge_type: KnowledgeType,
        name: str,
        content: Dict[str, Any],
        author_id: str,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[LineageNode, LineageCommit]:
        """Derive a new knowledge node from a parent."""
        if parent_id not in self.nodes:
            raise ValueError(f"Parent node {parent_id} not found")

        # Create new node
        node = self.create_node(knowledge_type, name, content, author_id, metadata)

        # Commit with parent
        commit = self.commit(
            node.id, message or f"Derived {name} from {parent_id}", author_id, [parent_id]
        )

        return node, commit

    def merge(
        self,
        node_ids: List[str],
        new_name: str,
        new_type: KnowledgeType,
        content: Dict[str, Any],
        author_id: str,
        message: str = "",
    ) -> Tuple[LineageNode, LineageCommit]:
        """Merge multiple knowledge nodes into one."""
        for node_id in node_ids:
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} not found")

        # Create merged node
        node = self.create_node(new_type, new_name, content, author_id)

        # Commit with multiple parents
        commit = self.commit(
            node.id,
            message or f"Merged {len(node_ids)} nodes into {new_name}",
            author_id,
            node_ids,
        )

        # Mark edges as merge events
        for parent_id in node_ids:
            for edge in self.edges[parent_id]:
                if edge.to_id == node.id:
                    edge.event_type = LineageEventType.MERGED

        return node, commit

    def get_lineage(self, node_id: str) -> List[LineageNode]:
        """Get the full lineage (ancestors) of a node."""
        if node_id not in self.nodes:
            return []

        lineage = []
        visited = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current in self.nodes:
                lineage.append(self.nodes[current])

            # Find parents (nodes that point to this node)
            for other_id, edges in self.edges.items():
                for edge in edges:
                    if edge.to_id == current and other_id not in visited:
                        queue.append(other_id)

        return lineage

    def get_descendants(self, node_id: str) -> List[LineageNode]:
        """Get all descendants of a node."""
        if node_id not in self.nodes:
            return []

        descendants = []
        visited = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Find children (nodes this node points to)
            for edge in self.edges.get(current, []):
                if edge.to_id not in visited:
                    descendants.append(self.nodes.get(edge.to_id))
                    queue.append(edge.to_id)

        return [d for d in descendants if d is not None]

    def get_path(self, from_id: str, to_id: str) -> List[str]:
        """Find the path between two nodes using BFS."""
        if from_id not in self.nodes or to_id not in self.nodes:
            return []

        if from_id == to_id:
            return [from_id]

        queue = [(from_id, [from_id])]
        visited = {from_id}

        while queue:
            current, path = queue.pop(0)

            for edge in self.edges.get(current, []):
                if edge.to_id == to_id:
                    return path + [to_id]

                if edge.to_id not in visited:
                    visited.add(edge.to_id)
                    queue.append((edge.to_id, path + [edge.to_id]))

        return []

    def get_history(self, commit_id: Optional[str] = None, limit: int = 50) -> List[LineageCommit]:
        """Get commit history."""
        if commit_id is None:
            commit_id = self.head

        if commit_id is None or commit_id not in self.commits:
            return []

        history = []
        current = commit_id
        visited = set()

        while current and current not in visited and len(history) < limit:
            visited.add(current)
            commit = self.commits.get(current)
            if commit:
                history.append(commit)
                current = commit.parent_ids[0] if commit.parent_ids else None

        return history

    def get_commit(self, commit_id: str) -> Optional[LineageCommit]:
        """Get a commit by ID."""
        return self.commits.get(commit_id)

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def find_nodes_by_type(self, knowledge_type: KnowledgeType) -> List[LineageNode]:
        """Find all nodes of a specific type."""
        return [n for n in self.nodes.values() if n.knowledge_type == knowledge_type]

    def find_nodes_by_author(self, author_id: str) -> List[LineageNode]:
        """Find all nodes by an author."""
        return [n for n in self.nodes.values() if n.author_id == author_id]

    def create_branch(self, branch_name: str, commit_id: Optional[str] = None) -> bool:
        """Create a new branch."""
        if commit_id is None:
            commit_id = self.head

        if commit_id is None or commit_id not in self.commits:
            return False

        self.branches[branch_name] = commit_id
        logger.info(f"Created branch {branch_name} at {commit_id}")
        return True

    def checkout_branch(self, branch_name: str) -> bool:
        """Switch to a branch."""
        if branch_name not in self.branches:
            return False

        self.head = self.branches[branch_name]
        logger.info(f"Checked out branch {branch_name}")
        return True

    def get_branches(self) -> Dict[str, str]:
        """Get all branches."""
        return self.branches.copy()

    def diff(self, commit_id_a: str, commit_id_b: str) -> Optional[Dict[str, Any]]:
        """Compare two commits."""
        commit_a = self.commits.get(commit_id_a)
        commit_b = self.commits.get(commit_id_b)

        if not commit_a or not commit_b:
            return None

        node_a = self.nodes.get(commit_a.node_id)
        node_b = self.nodes.get(commit_b.node_id)

        if not node_a or not node_b:
            return None

        # Simple diff: compare content
        diff = {
            "commit_a": commit_id_a,
            "commit_b": commit_id_b,
            "node_a": node_a.name,
            "node_b": node_b.name,
            "type_changed": node_a.knowledge_type != node_b.knowledge_type,
            "content_keys_a": set(node_a.content.keys()),
            "content_keys_b": set(node_b.content.keys()),
            "added_keys": set(node_b.content.keys()) - set(node_a.content.keys()),
            "removed_keys": set(node_a.content.keys()) - set(node_b.content.keys()),
        }

        return diff

    def get_statistics(self) -> Dict[str, Any]:
        """Get lineage statistics."""
        type_counts = {}
        for node in self.nodes.values():
            type_counts[node.knowledge_type.value] = (
                type_counts.get(node.knowledge_type.value, 0) + 1
            )

        event_counts = {}
        for edges_list in self.edges.values():
            for edge in edges_list:
                event_counts[edge.event_type.value] = event_counts.get(edge.event_type.value, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": sum(len(edges) for edges in self.edges.values()),
            "total_commits": len(self.commits),
            "by_type": type_counts,
            "by_event": event_counts,
            "total_branches": len(self.branches),
            "current_branch": "main",
            "current_head": self.head,
        }
