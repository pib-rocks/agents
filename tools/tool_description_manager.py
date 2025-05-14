import sqlite3
import os
from typing import Dict, Optional, List

# Pfad zur Datenbankdatei im selben Verzeichnis wie dieses Skript
DB_PATH = os.path.join(os.path.dirname(__file__), 'tool_descriptions.db')
TABLE_NAME = 'tool_descriptions'

def _get_db_connection():
    """Stellt eine Verbindung zur SQLite-Datenbank her."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Ermöglicht den Zugriff auf Spalten per Namen
    return conn

def create_table_if_not_exists():
    """Erstellt die Tabelle für Werkzeugbeschreibungen, falls sie noch nicht existiert."""
    conn = _get_db_connection()
    try:
        with conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    tool_name TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    source_module TEXT 
                )
            """)
            # Indizes für schnellere Abfragen hinzufügen (optional, aber gut für die Zukunft)
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_tool_name ON {TABLE_NAME} (tool_name);")
        print(f"Tabelle '{TABLE_NAME}' erfolgreich initialisiert/überprüft in '{DB_PATH}'.")
    except sqlite3.Error as e:
        print(f"Fehler beim Erstellen/Überprüfen der Tabelle '{TABLE_NAME}': {e}")
    finally:
        conn.close()

def _get_initial_tool_descriptions() -> Dict[str, Dict[str, str]]:
    """
    Liefert die initialen Beschreibungen für die Anforderungs-Werkzeuge.
    Diese werden verwendet, um die Datenbank beim ersten Mal zu befüllen.
    Die Beschreibungen hier sollten prägnant und informativ für den LLM-Agenten sein.
    """
    return {
        # Aus tools.vector_storage.requirements
        "add_requirement": {
            "description": "Adds a new software requirement to the vector database with an automatically generated ID. Manages requirement text and metadata, including 'source_jira_ticket', 'implementation_status' (Open, In Progress, Done, etc.), and 'classification' (Functional, Non-Functional, Business).",
            "source_module": "tools.vector_storage.requirements"
        },
        "retrieve_similar_requirements": {
            "description": "Retrieves requirements from the vector database that are semantically similar to a given query text. Supports filtering by metadata (e.g., 'source_jira_ticket', 'implementation_status') and specifying the number of results.",
            "source_module": "tools.vector_storage.requirements"
        },
        "update_requirement": {
            "description": "Updates the text and/or metadata of an existing requirement in the vector database, identified by its ID. New metadata (JSON format) replaces existing metadata. 'implementation_status' and 'classification' can be updated.",
            "source_module": "tools.vector_storage.requirements"
        },
        "delete_requirement": {
            "description": "Deletes one or more requirements from the vector database based on a list of their unique IDs.",
            "source_module": "tools.vector_storage.requirements"
        },
        "get_all_requirements": {
            "description": "Retrieves all requirements currently stored in the vector database, including their IDs, text, and all associated metadata.",
            "source_module": "tools.vector_storage.requirements"
        },
        # Aus tools.neo4j_requirements_tool
        "add_or_update_requirement_neo4j": {
            "description": "Adds a new requirement node to a Neo4j graph database or updates an existing one, identified by 'req_id'. Manages requirement text and a flexible set of properties (JSON format), automatically adding a 'change_date'.",
            "source_module": "tools.neo4j_requirements_tool"
        },
        "add_relationship_neo4j": {
            "description": "Adds a directed relationship (e.g., RELATES_TO, DEPENDS_ON, DUPLICATES) between two existing requirement nodes in the Neo4j graph database, identified by their 'req_id's. Relationship type must be uppercase with underscores.",
            "source_module": "tools.neo4j_requirements_tool"
        }
    }

def populate_initial_descriptions():#AI! Change the descriptions in this module to english
    """Befüllt die Datenbank mit den initialen Werkzeugbeschreibungen, falls noch nicht vorhanden."""
    conn = _get_db_connection()
    try:
        initial_descriptions = _get_initial_tool_descriptions()
        with conn:
            for tool_name, data in initial_descriptions.items():
                # Füge nur ein, wenn der tool_name noch nicht existiert
                conn.execute(
                    f"INSERT OR IGNORE INTO {TABLE_NAME} (tool_name, description, source_module) VALUES (?, ?, ?)",
                    (tool_name, data["description"], data["source_module"])
                )
        print(f"{len(initial_descriptions)} initiale Werkzeugbeschreibungen in '{TABLE_NAME}' eingefügt/ignoriert.")
    except sqlite3.Error as e:
        print(f"Fehler beim Befüllen der initialen Beschreibungen: {e}")
    finally:
        conn.close()

def get_tool_description(tool_name: str) -> Optional[str]:
    """
    Ruft die Beschreibung für ein bestimmtes Werkzeug aus der Datenbank ab.

    Args:
        tool_name (str): Der Name der Funktion des Werkzeugs (z.B. "add_requirement").

    Returns:
        Optional[str]: Die Beschreibung des Werkzeugs oder None, wenn nicht gefunden.
    """
    conn = _get_db_connection()
    description: Optional[str] = None
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT description FROM {TABLE_NAME} WHERE tool_name = ?", (tool_name,))
        row = cursor.fetchone()
        if row:
            description = row['description']
    except sqlite3.Error as e:
        print(f"Fehler beim Abrufen der Beschreibung für '{tool_name}': {e}")
    finally:
        conn.close()
    return description

def update_tool_description_in_db(tool_name: str, new_description: str) -> bool:
    """
    Aktualisiert die Beschreibung eines Werkzeugs in der Datenbank.
    Nützlich für externe Systeme, um Beschreibungen zu ändern.

    Args:
        tool_name (str): Der Name des Werkzeugs, dessen Beschreibung aktualisiert werden soll.
        new_description (str): Die neue Beschreibung.

    Returns:
        bool: True bei Erfolg, False bei Fehler.
    """
    conn = _get_db_connection()
    try:
        with conn:
            result = conn.execute(
                f"UPDATE {TABLE_NAME} SET description = ? WHERE tool_name = ?",
                (new_description, tool_name)
            )
            if result.rowcount == 0:
                print(f"Warnung: Werkzeug '{tool_name}' nicht in der Datenbank gefunden. Keine Aktualisierung.")
                return False
        print(f"Beschreibung für Werkzeug '{tool_name}' erfolgreich aktualisiert.")
        return True
    except sqlite3.Error as e:
        print(f"Fehler beim Aktualisieren der Beschreibung für '{tool_name}': {e}")
        return False
    finally:
        conn.close()

def get_all_tool_descriptions_from_db() -> List[Dict[str, str]]:
    """Ruft alle Werkzeugnamen und ihre Beschreibungen aus der Datenbank ab."""
    conn = _get_db_connection()
    tools_data = []
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT tool_name, description, source_module FROM {TABLE_NAME}")
        rows = cursor.fetchall()
        for row in rows:
            tools_data.append({"tool_name": row["tool_name"], "description": row["description"], "source_module": row["source_module"]})
    except sqlite3.Error as e:
        print(f"Fehler beim Abrufen aller Werkzeugbeschreibungen: {e}")
    finally:
        conn.close()
    return tools_data

# Initialisierung: Tabelle erstellen und mit initialen Daten befüllen, wenn das Modul geladen wird.
# Dies stellt sicher, dass die DB und die Tabelle existieren, wenn andere Teile der Anwendung sie verwenden.
if __name__ == "__main__":
    print(f"Datenbank-Setup wird ausgeführt für: {DB_PATH}")
    create_table_if_not_exists()
    populate_initial_descriptions()
    print("\nBeispielabruf aller Beschreibungen:")
    all_descs = get_all_tool_descriptions_from_db()
    for desc_item in all_descs:
        print(f"  Tool: {desc_item['tool_name']} (aus {desc_item['source_module']})")
        print(f"    Desc: {desc_item['description'][:70]}...")
    
    print("\nBeispielabruf einer einzelnen Beschreibung:")
    example_desc = get_tool_description("add_requirement")
    if example_desc:
        print(f"  Desc für 'add_requirement': {example_desc}")
    else:
        print("  'add_requirement' nicht gefunden.")
else:
    # Sicherstellen, dass die DB und Tabelle beim Import existieren
    create_table_if_not_exists()
    populate_initial_descriptions()

__all__ = ['get_tool_description', 'update_tool_description_in_db', 'get_all_tool_descriptions_from_db', 'DB_PATH']
