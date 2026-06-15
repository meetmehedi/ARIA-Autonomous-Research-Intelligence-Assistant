import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import aria.memory as memory
from aria.tools.search import search_web
from aria.tools.scraper import scrape_url
from aria.tools.pdf import read_pdf
from aria.tools.telegram import send_telegram_message as send_telegram
from aria.tools.gmail import send_email
from aria.tools.executor import execute_python_script
from aria.assistant import parse_and_run_tool, execute_assistant_task
from aria.builder import extract_json_block, build_agent

class TestAriaTools(unittest.TestCase):
    
    def setUp(self):
        memory.init_db()

    def test_search_web(self):
        # We test with a real lookup or mock
        with patch('aria.tools.search.DDGS') as mock_ddg:
            mock_inst = MagicMock()
            mock_inst.text.return_value = [
                {"title": "Test Title", "href": "http://test.com", "body": "Test Body"}
            ]
            mock_ddg.return_value.__enter__.return_value = mock_inst
            
            res = search_web("test query")
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["title"], "Test Title")

    def test_scraper(self):
        # Test scraping with requests mock
        with patch('requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<html><body><h1>Headline</h1><p>Paragraph content</p></body></html>"
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            
            res = scrape_url("http://dummy-url.com")
            self.assertIn("Headline", res)
            self.assertIn("Paragraph content", res)

    def test_pdf_reader(self):
        # Test pdf reading with patch for fitz
        with patch('fitz.open') as mock_fitz_open:
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 1
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Extracted PDF content text"
            mock_doc.load_page.return_value = mock_page
            mock_fitz_open.return_value = mock_doc
            
            res = read_pdf("dummy.pdf")
            self.assertEqual(res, "Extracted PDF content text")

    def test_executor(self):
        # Test run script
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("print('Test execution output')")
            temp_path = f.name
            
        try:
            res = execute_python_script(temp_path)
            self.assertTrue(res["success"])
            self.assertIn("Test execution output", res["stdout"])
        finally:
            os.unlink(temp_path)

    def test_telegram_sender(self):
        # Test telegram fallback or response
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"ok": True}
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp
            
            # Temporarily configure environment
            with patch('aria.tools.telegram.TELEGRAM_BOT_TOKEN', 'token'), \
                 patch('aria.tools.telegram.TELEGRAM_CHAT_ID', 'chat_id'):
                res = send_telegram("Hello")
                self.assertTrue(res)

    def test_email_sender_fallback(self):
        # Standard email fallback should print draft to stdout and return True
        res = send_email("Test Subject", "Test Body", "target@test.com")
        self.assertTrue(res)

    def test_react_parsing(self):
        # Test parse_and_run_tool for correct parsing of Call: lines
        with patch('aria.assistant.TOOL_REGISTRY') as mock_registry:
            mock_func = MagicMock()
            mock_func.return_value = "Tool run completed."
            mock_registry.__contains__.return_value = True
            mock_registry.__getitem__.return_value = mock_func
            
            called, result = parse_and_run_tool('Thought: I need to do search.\nCall: search_web(query="Continual learning papers")')
            self.assertTrue(called)
            mock_func.assert_called_once_with(query="Continual learning papers")
            self.assertIn("Tool run completed", result)

    def test_json_block_extraction(self):
        # Test JSON parsing helper in builder
        json_payload = 'Some markdown text\n```json\n{\n  "agent_name": "test_agent",\n  "description": "desc",\n  "files": {}\n}\n```\nSome other trailing text.'
        extracted = extract_json_block(json_payload)
        self.assertEqual(extracted["agent_name"], "test_agent")

if __name__ == "__main__":
    unittest.main()
