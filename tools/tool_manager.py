import sqlite3
import os
from typing import List, Dict, Optional

# Importiere die Datenbankverbindungsfunktion und den Tabellennamen für Werkzeugbeschreibungen
# aus dem tool_description_manager.
# Das Unterstrich-Präfix bei _get_db_connection deutet auf eine interne Verwendung hin,
# aber für modulübergreifende Helferfunktionen ist dies in Python üblich, wenn klar dokumentiert.
from .tool_description_manager import _get_db_connection, TABLE_NAME as TOOL_DESCRIPTIONS_TABLE_NAME

AGENT_TOOLS_TABLE_NAME = 'agent_tools' # Name der Tabelle für Agenten-Werkzeug-Zuweisungen

def list_available_tools_for_agent(agent_name: str) -> List[Dict[str, str]]:
    """
    Listet alle Werkzeuge auf, die im System definiert, aber für den angegebenen Agenten aktuell NICHT aktiviert sind.
    Dies hilft dabei, Werkzeuge zu entdecken, die potenziell zu den Fähigkeiten eines Agenten hinzugefügt werden können.

    Args:
        agent_name (str): Der Name des Agenten, für den verfügbare (aber nicht aktivierte) Werkzeuge aufgelistet werden sollen.

    Returns:
        List[Dict[str, str]]: Eine Liste von Werkzeugen, wobei jedes Werkzeug ein Dictionary ist,
                               das 'tool_name' und 'description' enthält.
                               Gibt eine leere Liste zurück, wenn alle Werkzeuge bereits aktiviert sind oder keine weiteren Werkzeuge definiert sind.
                               Im Fehlerfall enthält die Liste ein einzelnes Dictionary mit einem 'error'-Schlüssel.
    """
    conn = _get_db_connection()
    available_tools = []
    try:
        cursor = conn.cursor()
        # Hole alle Werkzeuge und ihre Beschreibungen
        cursor.execute(f"SELECT tool_name, description FROM {TOOL_DESCRIPTIONS_TABLE_NAME}")
        all_tools_rows = cursor.fetchall()
        all_tools_map = {row["tool_name"]: row["description"] for row in all_tools_rows}

        # Hole die aktuell für den Agenten aktivierten Werkzeuge
        cursor.execute(f"SELECT tool_name FROM {AGENT_TOOLS_TABLE_NAME} WHERE agent_name = ?", (agent_name,))
        enabled_tools_rows = cursor.fetchall()
        enabled_tools_set = {row["tool_name"] for row in enabled_tools_rows}

        # Bestimme die Werkzeuge, die noch nicht für den Agenten aktiviert sind
        for tool_name, description in all_tools_map.items():
            if tool_name not in enabled_tools_set:
                available_tools.append({"tool_name": tool_name, "description": description})
        
        return available_tools # Gibt eine leere Liste zurück, wenn keine neuen Werkzeuge verfügbar sind

    except sqlite3.Error as e:
        print(f"Datenbankfehler in list_available_tools_for_agent für '{agent_name}': {e}")
        return [{"error": f"Auflisten verfügbarer Werkzeuge für Agent '{agent_name}' aufgrund eines Datenbankfehlers fehlgeschlagen: {e}"}]
    finally:
        if conn:
            conn.close()

def set_tool_availability_for_agent(agent_name: str, tool_name: str, enable: bool) -> Dict[str, str]:
    """
    Aktiviert oder deaktiviert ein bestimmtes Werkzeug für einen gegebenen Agenten in der Datenbank.
    Das Werkzeug muss in der Haupttabelle 'tool_descriptions' existieren.

    Args:
        agent_name (str): Der Name des Agenten (z.B. 'Product-Owner', 'Developer').
        tool_name (str): Der Name des zu aktivierenden oder deaktivierenden Werkzeugs.
        enable (bool): True, um das Werkzeug zu aktivieren, False, um es zu deaktivieren.

    Returns:
        Dict[str, str]: Ein Dictionary mit einer Statusmeldung, die Erfolg oder Misserfolg anzeigt.
    """
    conn = _get_db_connection()
    try:
        with conn: # Stellt sicher, dass Transaktionen atomar sind (commit/rollback)
            cursor = conn.cursor()
            # Überprüfe, ob das Werkzeug in der Haupttabelle tool_descriptions existiert
            cursor.execute(f"SELECT 1 FROM {TOOL_DESCRIPTIONS_TABLE_NAME} WHERE tool_name = ?", (tool_name,))
            if not cursor.fetchone():
                return {"status": "error", "message": f"Werkzeug '{tool_name}' nicht im System gefunden. Verfügbarkeit kann nicht geändert werden."}

            if enable:
                # Füge das Werkzeug hinzu, ignoriere es, falls es bereits existiert
                cursor.execute(
                    f"INSERT OR IGNORE INTO {AGENT_TOOLS_TABLE_NAME} (agent_name, tool_name) VALUES (?, ?)",
                    (agent_name, tool_name)
                )
                if cursor.rowcount > 0:
                    return {"status": "success", "message": f"Werkzeug '{tool_name}' für Agent '{agent_name}' aktiviert."}
                else:
                    # Überprüfe, ob es bereits vorhanden war (da INSERT OR IGNORE rowcount 0 zurückgibt, wenn es ignoriert wurde)
                    cursor.execute(f"SELECT 1 FROM {AGENT_TOOLS_TABLE_NAME} WHERE agent_name = ? AND tool_name = ?", (agent_name, tool_name))
                    if cursor.fetchone():
                        return {"status": "info", "message": f"Werkzeug '{tool_name}' war bereits für Agent '{agent_name}' aktiviert."}
                    else:
                        # Sollte nicht erreicht werden, wenn INSERT OR IGNORE wie erwartet funktioniert
                        return {"status": "error", "message": f"Fehler beim Aktivieren von Werkzeug '{tool_name}' für Agent '{agent_name}'. Unbekannter Grund."}
            else: # Deaktivieren
                cursor.execute(
                    f"DELETE FROM {AGENT_TOOLS_TABLE_NAME} WHERE agent_name = ? AND tool_name = ?",
                    (agent_name, tool_name)
                )
                if cursor.rowcount > 0:
                    return {"status": "success", "message": f"Werkzeug '{tool_name}' für Agent '{agent_name}' deaktiviert."}
                else:
                    return {"status": "info", "message": f"Werkzeug '{tool_name}' war nicht für Agent '{agent_name}' aktiviert oder existiert nicht."}
    except sqlite3.Error as e:
        print(f"Datenbankfehler in set_tool_availability_for_agent für '{agent_name}', Werkzeug '{tool_name}': {e}")
        return {"status": "error", "message": f"Datenbankfehler: {e}"}
    finally:
        if conn:
            conn.close()

__all__ = ['list_available_tools_for_agent', 'set_tool_availability_for_agent']
