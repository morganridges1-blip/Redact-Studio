"""Publish synthetic test outcomes in the GitHub Actions run summary."""
import os
from importlib.metadata import version
from pathlib import Path
import xml.etree.ElementTree as ET


def summary(report):
    if not report.is_file():
        return '## Windows tests\n\nNo test report was produced. Inspect the test step logs.\n'
    root = ET.parse(report).getroot()
    cases = list(root.iter('testcase'))
    failures = [(case, failure) for case in cases
                for failure in list(case.findall('failure')) + list(case.findall('error'))]
    skipped = sum(case.find('skipped') is not None for case in cases)
    lines = ['## Windows tests', '',
             f'{len(cases)} tests; {len(failures)} failures/errors; {skipped} skipped.', '',
             f'Built with Pillow {version("Pillow")}, PySide6 {version("PySide6")}, pytest {version("pytest")}.', '']
    for case, failure in failures:
        lines += [f'### {case.get("classname", "")}.{case.get("name", "")}', '',
                  '```text', (failure.text or failure.get('message', ''))[:12000], '```', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    text = summary(Path('test-results.xml'))
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
        stream.write(text)
