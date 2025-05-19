import unittest
from unittest.mock import patch, MagicMock
import sqlite3
import sys
import os

# Füge das Projekt-Stammverzeichnis zum sys.path hinzu, um das 'tools'-Modul zu finden
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.tool_manager import list_available_tools_for_agent, set_tool_availability_for_agent, AGENT_TOOLS_TABLE_NAME
from tools.tool_description_manager import TABLE_NAME as TOOL_DESCRIPTIONS_TABLE_NAME

# Konstanten für Testdaten
TEST_AGENT_1 = "TestAgent1"
TEST_AGENT_2 = "TestAgent2"
TOOL_1 = "tool1"
TOOL_DESC_1 = "Beschreibung für Werkzeug1"
TOOL_MODULE_1 = "test.module1"
TOOL_2 = "tool2"
TOOL_DESC_2 = "Beschreibung für Werkzeug2"
TOOL_MODULE_2 = "test.module2"
TOOL_3 = "tool3"
TOOL_DESC_3 = "Beschreibung für Werkzeug3"
TOOL_MODULE_3 = "test.module3"
NON_EXISTENT_TOOL = "nicht_existierendes_werkzeug"

class TestToolManager(unittest.TestCase):

    def setUp(self):
        # Verwende eine In-Memory SQLite-Datenbank für Tests
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row # Ermöglicht Spaltenzugriff über Namen
        self.cursor = self.conn.cursor()

        # Erstelle Tabellen
        self.cursor.execute(f"""
            CREATE TABLE {TOOL_DESCRIPTIONS_TABLE_NAME} (
                tool_name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                source_module TEXT
            )
        """)
        self.cursor.execute(f"""
            CREATE TABLE {AGENT_TOOLS_TABLE_NAME} (
                agent_name TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                PRIMARY KEY (agent_name, tool_name),
                FOREIGN KEY (tool_name) REFERENCES {TOOL_DESCRIPTIONS_TABLE_NAME}(tool_name)
            )
        """)
        self.conn.commit()

        # Befülle tool_descriptions
        self.cursor.execute(f"INSERT INTO {TOOL_DESCRIPTIONS_TABLE_NAME} (tool_name, description, source_module) VALUES (?, ?, ?)", (TOOL_1, TOOL_DESC_1, TOOL_MODULE_1))
        self.cursor.execute(f"INSERT INTO {TOOL_DESCRIPTIONS_TABLE_NAME} (tool_name, description, source_module) VALUES (?, ?, ?)", (TOOL_2, TOOL_DESC_2, TOOL_MODULE_2))
        self.cursor.execute(f"INSERT INTO {TOOL_DESCRIPTIONS_TABLE_NAME} (tool_name, description, source_module) VALUES (?, ?, ?)", (TOOL_3, TOOL_DESC_3, TOOL_MODULE_3))
        self.conn.commit()

        # Patche _get_db_connection, die von den Funktionen in tool_manager.py verwendet wird
        # um unsere In-Memory-Datenbankverbindung zurückzugeben
        self.mock_db_patcher = patch('tools.tool_manager._get_db_connection')
        self.mock_get_db_connection = self.mock_db_patcher.start()
        self.mock_get_db_connection.return_value = self.conn

    def tearDown(self):
        self.mock_db_patcher.stop()
        self.conn.close()

    # --- Tests für list_available_tools_for_agent ---

    def test_list_some_tools_available(self):
        # TEST_AGENT_1 hat TOOL_1 aktiviert
        self.cursor.execute(f"INSERT INTO {AGENT_TOOLS_TABLE_NAME} (agent_name, tool_name) VALUES (?, ?)", (TEST_AGENT_1, TOOL_1))
        self.conn.commit()

        result = list_available_tools_for_agent(TEST_AGENT_1)
        self.assertEqual(len(result), 2)
        result_tool_names = {tool['tool_name'] for tool in result}
        self.assertIn(TOOL_2, result_tool_names)
        self.assertIn(TOOL_3, result_tool_names)
        for tool in result:
            if tool['tool_name'] == TOOL_2:
                self.assertEqual(tool['description'], TOOL_DESC_2)
            elif tool['tool_name'] == TOOL_3:
                self.assertEqual(tool['description'], TOOL_DESC_3)

    def test_list_no_tools_available_all_enabled(self):
        self.cursor.execute(f"INSERT INTO {AGENT_TOOLS_TABLE_NAME} (agent_name, tool_name) VALUES (?, ?)", (TEST_AGENT_1, TOOL_1))
        self.cursor.execute(f"INSERT INTO {AGENT_TOOLS_TABLE_NAME} (agent_name, tool_name) VALUES (?, ?)", (TEST_AGENT_1, TOOL_2))
        self.cursor.execute(f"INSERT INTO {AGENT_TOOLS_TABLE_NAME} (agent_name, tool_name) VALUES (?, ?)", (TEST_AGENT_1, TOOL_3))
        self.conn.commit()

        result = list_available_tools_for_agent(TEST_AGENT_1)
        self.assertEqual(len(result), 0)

    def test_list_all_tools_available_none_enabled(self):
        result = list_available_tools_for_agent(TEST_AGENT_1) # TEST_AGENT_1 hat keine Werkzeuge aktiviert
        self.assertEqual(len(result), 3)
        result_tool_names = {tool['tool_name'] for tool in result}
        self.assertIn(TOOL_1, result_tool_names)
        self.assertIn(TOOL_2, result_tool_names)
        self.assertIn(TOOL_3, result_tool_names)

    def test_list_non_existent_agent(self):
        # Ein nicht existierender Agent sollte alle Werkzeuge als verfügbar anzeigen
        result = list_available_tools_for_agent("AgentNichtExistent")
        self.assertEqual(len(result), 3)

    def test_list_no_tools_defined_in_system(self):
        # Leere die tool_descriptions Tabelle
        self.cursor.execute(f"DELETE FROM {TOOL_DESCRIPTIONS_TABLE_NAME}")
        self.conn.commit()
        result = list_available_tools_for_agent(TEST_AGENT_1)
        self.assertEqual(len(result), 0)

    def test_list_db_error_handling(self):
        # Simuliere einen DB-Fehler, indem _get_db_connection eine Exception auslöst
        # oder die zurückgegebene Verbindung fehlerhaft ist.
        mock_bad_conn = MagicMock()
        mock_bad_conn.cursor.side_effect = sqlite3.Error("Simulierter DB Fehler")
        self.mock_get_db_connection.return_value = mock_bad_conn

        result = list_available_tools_for_agent(TEST_AGENT_1)
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertTrue("Datenbankfehler" in result[0]["error"] or "Auflisten verfügbarer Werkzeuge" in result[0]["error"])

    # --- Tests für set_tool_availability_for_agent ---

    def test_set_enable_new_tool_success(self):
        result = set_tool_availability_for_agent(TEST_AGENT_1, TOOL_1, True)
        self.assertEqual(result["status"], "success")
        self.assertIn(f"Werkzeug '{TOOL_1}' für Agent '{TEST_AGENT_1}' aktiviert.", result["message"])

        # Überprüfe Datenbank
        self.cursor.execute(f"SELECT tool_name FROM {AGENT_TOOLS_TABLE_NAME} WHERE agent_name = ? AND tool_name = ?", (TEST_AGENT_1, TOOL_1))
        self.assertIsNotNone(self.cursor.fetchone())

    def test_set_enable_already_enabled_tool_info(self):
        self.cursor.execute(f"INSERT INTO {AGENT_TOOLS_TABLE_NAME} (agent_name, tool_name) VALUES (?, ?)", (TEST_AGENT_1, TOOL_1))
        self.conn.commit()

        result = set_tool_availability_for_agent(TEST_AGENT_1, TOOL_1, True)
        self.assertEqual(result["status"], "info")
        self.assertIn(f"Werkzeug '{TOOL_1}' war bereits für Agent '{TEST_AGENT_1}' aktiviert.", result["message"])

    def test_set_enable_non_existent_tool_error(self):
        result = set_tool_availability_for_agent(TEST_AGENT_1, NON_EXISTENT_TOOL, True)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Werkzeug '{NON_EXISTENT_TOOL}' nicht im System gefunden.", result["message"])

    def test_set_disable_enabled_tool_success(self):
        self.cursor.execute(f"INSERT INTO {AGENT_TOOLS_TABLE_NAME} (agent_name, tool_name) VALUES (?, ?)", (TEST_AGENT_1, TOOL_1))
        self.conn.commit()

        result = set_tool_availability_for_agent(TEST_AGENT_1, TOOL_1, False)
        self.assertEqual(result["status"], "success")
        self.assertIn(f"Werkzeug '{TOOL_1}' für Agent '{TEST_AGENT_1}' deaktiviert.", result["message"])

        # Überprüfe Datenbank
        self.cursor.execute(f"SELECT tool_name FROM {AGENT_TOOLS_TABLE_NAME} WHERE agent_name = ? AND tool_name = ?", (TEST_AGENT_1, TOOL_1))
        self.assertIsNone(self.cursor.fetchone())

    def test_set_disable_not_enabled_tool_info(self):
        result = set_tool_availability_for_agent(TEST_AGENT_1, TOOL_1, False) # TOOL_1 ist nicht aktiviert
        self.assertEqual(result["status"], "info")
        self.assertIn(f"Werkzeug '{TOOL_1}' war nicht für Agent '{TEST_AGENT_1}' aktiviert oder existiert nicht.", result["message"])

    def test_set_disable_non_existent_tool_error(self):
        result = set_tool_availability_for_agent(TEST_AGENT_1, NON_EXISTENT_TOOL, False)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Werkzeug '{NON_EXISTENT_TOOL}' nicht im System gefunden.", result["message"])

    def test_set_db_error_during_enable(self):
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock(spec=sqlite3.Cursor)
        # Erster Aufruf (Werkzeug existiert) ist ok
        mock_cursor.fetchone.return_value = (TOOL_1,)

        def execute_raiser_insert_side_effect(sql_query, params=None):
            if "INSERT INTO" in sql_query.upper() or "VALUES" in sql_query.upper() : # Allgemeiner für INSERT
                raise sqlite3.Error("Simulierter DB Fehler bei INSERT")
            return None # Für SELECTs

        mock_cursor.execute.side_effect = execute_raiser_insert_side_effect
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_cursor) # Für den with conn: Block
        mock_conn.__exit__ = MagicMock(return_value=None) # Sicherstellen, dass Exceptions weitergegeben werden
        self.mock_get_db_connection.return_value = mock_conn

        result = set_tool_availability_for_agent(TEST_AGENT_1, TOOL_1, True)
        self.assertEqual(result["status"], "error")
        self.assertIn("Datenbankfehler", result["message"])

    def test_set_db_error_during_disable(self):
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock(spec=sqlite3.Cursor)
        # Erster Aufruf (Werkzeug existiert) ist ok
        mock_cursor.fetchone.return_value = (TOOL_1,)

        def execute_raiser_delete_side_effect(sql_query, params=None):
            if "DELETE FROM" in sql_query.upper():
                raise sqlite3.Error("Simulierter DB Fehler bei DELETE")
            return None # Für SELECTs

        mock_cursor.execute.side_effect = execute_raiser_delete_side_effect
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_cursor) # Für den with conn: Block
        mock_conn.__exit__ = MagicMock(return_value=None) # Sicherstellen, dass Exceptions weitergegeben werden
        self.mock_get_db_connection.return_value = mock_conn

        result = set_tool_availability_for_agent(TEST_AGENT_1, TOOL_1, False)
        self.assertEqual(result["status"], "error")
        self.assertIn("Datenbankfehler", result["message"])

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
