import re
from typing import List, Dict, Any, Tuple
from loguru import logger
from neo4j import GraphDatabase
from src.config import settings

def get_neo4j_driver():
    if not settings.neo4j_uri:
        raise ValueError("NEO4J_URI is not set in settings.")
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    return driver

def run_write_query(query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    db_name = settings.neo4j_database or "neo4j"
    driver = get_neo4j_driver()
    try:
        with driver.session(database=db_name) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    finally:
        driver.close()

def run_read_query(query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    db_name = settings.neo4j_database or "neo4j"
    driver = get_neo4j_driver()
    try:
        with driver.session(database=db_name) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    finally:
        driver.close()

def upsert_entities_and_relations(entities: List[Dict[str, str]], relations: List[Dict[str, str]]) -> None:
    """
    Saves extracted entities and relations to Neo4j.
    """
    logger.info(f"Upserting {len(entities)} entities and {len(relations)} relations to Neo4j...")
    
    # 1. Upsert entities
    entity_query = """
    UNWIND $entities AS ent
    MERGE (e:Entity {name: ent.name})
    SET e.label = ent.label
    """
    run_write_query(entity_query, {"entities": entities})
    
    # 2. Upsert relations
    # We must sanitize the relationship types and run them safely.
    for rel in relations:
        source = rel["source"]
        target = rel["target"]
        rel_type = rel["type"]
        
        # Sanitize rel_type for Cypher safety (only allow alphanumeric and underscore)
        clean_rel_type = re.sub(r'[^a-zA-Z0-9_]', '_', rel_type).upper()
        if not clean_rel_type:
            clean_rel_type = "RELATED_TO"
            
        relation_query = f"""
        MATCH (s:Entity {{name: $source}})
        MATCH (t:Entity {{name: $target}})
        MERGE (s)-[r:{clean_rel_type}]->(t)
        RETURN r
        """
        run_write_query(relation_query, {"source": source, "target": target})
        
    logger.info("Graph DB upsert completed successfully.")

def get_neighbors(entity_name: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Retrieves all direct neighbors of a specific entity.
    """
    query = """
    MATCH (e:Entity {name: $name})-[r]-(n:Entity)
    RETURN type(r) AS rel_type, n.name AS neighbor_name, n.label AS neighbor_label
    LIMIT $limit
    """
    records = run_read_query(query, {"name": entity_name, "limit": limit})
    return records

def find_shortest_path(start_entity: str, end_entity: str, max_depth: int = 5) -> Dict[str, Any]:
    """
    Finds the shortest path between start_entity and end_entity.
    Returns the path details (nodes and relations).
    """
    # Safe interpolation of max_depth
    depth_str = f"*..{int(max_depth)}"
    query = f"""
    MATCH p = shortestPath((start:Entity {{name: $start_entity}})-[{depth_str}]-(end:Entity {{name: $end_entity}}))
    RETURN p
    """
    records = run_read_query(query, {"start_entity": start_entity, "end_entity": end_entity})
    
    if not records or not records[0].get("p"):
        return {"found": False, "path": []}
    
    path = records[0]["p"]
    # Extract nodes and relationship types from path
    path_nodes = []
    path_rels = []
    
    for i, node in enumerate(path.nodes):
        path_nodes.append({
            "name": node.get("name"),
            "label": list(node.labels)[0] if node.labels else "Entity"
        })
        
    for rel in path.relationships:
        path_rels.append({
            "start": rel.nodes[0].get("name"),
            "end": rel.nodes[1].get("name"),
            "type": rel.type
        })
        
    return {
        "found": True,
        "nodes": path_nodes,
        "relations": path_rels
    }
