import requests
import json
from py2neo import Graph, Node, Relationship
import time

# Connect to Neo4j
graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))

def clear_database():
    """Clear the database"""
    graph.run("MATCH (n) DETACH DELETE n")
    print("Database cleared")

def get_openalex_works():
    """Get some research papers from OpenAlex API"""
    url = "https://api.openalex.org/works"
    params = {
        "filter": "concepts.id:C41008148,publication_year:>2022",  # getting computer science papers
        "per-page": 20,
        "sort": "cited_by_count:desc"
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data['results']
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

def create_nodes_and_relationships(works):
    """Process the works data and create nodes/relationships"""
    
    for work in works:
        # Creating Work node
        work_node = Node("Work", 
                        id=work['id'],
                        title=work.get('title', 'No title'),
                        year=work.get('publication_year'),
                        citations=work.get('cited_by_count', 0))
        graph.merge(work_node, "Work", "id")
        
        # Processing authors
        authorships = work.get('authorships', [])
        for authorship in authorships[:5]:  # limiting the authors to 5
            author_info = authorship.get('author', {})
            if author_info.get('id'):
                # Creating Author node
                author_node = Node("Author",
                                 id=author_info['id'],
                                 name=author_info.get('display_name', 'Unknown'))
                graph.merge(author_node, "Author", "id")
                
                # Creating relationship
                authored = Relationship(author_node, "AUTHORED", work_node)
                graph.merge(authored)
                
                # Processing institutions
                institutions = authorship.get('institutions', [])
                for inst in institutions[:2]:  # limiting institutions to only 2
                    if inst.get('id'):
                        inst_node = Node("Institution",
                                       id=inst['id'],
                                       name=inst.get('display_name', 'Unknown'))
                        graph.merge(inst_node, "Institution", "id")
                        
                        # Creating affiliation relationship
                        affiliation = Relationship(author_node, "AFFILIATED_WITH", inst_node)
                        graph.merge(affiliation)
        
        # Processing research topics/concepts
        concepts = work.get('concepts', [])
        for concept in concepts[:3]:  # limiting concepts
            if concept.get('id'):
                concept_node = Node("Concept",
                                  id=concept['id'],
                                  name=concept.get('display_name', 'Unknown'))
                graph.merge(concept_node, "Concept", "id")
                
                # Creating relationship
                covers = Relationship(work_node, "COVERS", concept_node)
                graph.merge(covers)

def run_basic_queries():
    """Run some basic queries"""
    
    # Counting nodes
    result = graph.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
    print("\nNode counts:")
    for record in result:
        print(f"{record['type']}: {record['count']}")
    
    # Finding top authors
    result = graph.run("""
        MATCH (a:Author)-[:AUTHORED]->(w:Work)
        RETURN a.name, count(w) as papers
        ORDER BY papers DESC LIMIT 5
    """)
    print("\nTop authors:")
    for record in result:
        print(f"{record['a.name']}: {record['papers']} papers")
    
    # Finding collaborations
    result = graph.run("""
        MATCH (a1:Author)-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(a2:Author)
        WHERE a1.name < a2.name
        RETURN a1.name, a2.name, count(w) as collaborations
        ORDER BY collaborations DESC LIMIT 5
    """)
    print("\nCollaborations:")
    for record in result:
        print(f"{record['a1.name']} & {record['a2.name']}: {record['collaborations']}")

def main():
    print("Starting OpenAlex Neo4j integration...")
    
    clear_database()
    
    print("Fetching data from OpenAlex...")
    works = get_openalex_works()
    print(f"Got {len(works)} research papers")
    
    print("Creating nodes and relationships...")
    create_nodes_and_relationships(works)
    
    print("Running queries...")
    run_basic_queries()
    
    print("\nDone! Now Relationship Graphs can be explored in Neo4j Browser")

if __name__ == "__main__":
    main()