import ast
from pathlib import Path

def test_no_network_ai_ocr_or_logging_imports():
    banned={'socket','requests','urllib','http','httpx','logging','torch','tensorflow','transformers','pytesseract','cv2','openai'}
    for path in (Path(__file__).parents[1]/'redact_studio').glob('*.py'):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                assert not {a.name.split('.')[0] for a in node.names}&banned
            if isinstance(node,ast.ImportFrom):
                assert (node.module or '').split('.')[0] not in banned
