"""Small, explicit XLSX reader: standard template or the BD_IJC1 adapter.

Reads values only. Does not evaluate formulas, copy worksheets, or consume clinical
columns. Avoids an additional spreadsheet dependency for this limited contract.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from zipfile import ZipFile, BadZipFile
import xml.etree.ElementTree as ET

from .contracts import ImportProblem, patient_key

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
HEADERS = {
    'standard': ('patient_key', 'patient_id', 'initials', 'birth_date'),
    'ijc1': ('Iniciales', 'ID', 'Iniciales', 'Fecha de nacimiento'),
}


@dataclass(frozen=True)
class PatientRow:
    key: str
    external_id: str
    initials: str
    birth_date: date


def birth_date(value, cell_type, epoch_1904=False):
    if value == '':
        raise ImportProblem('MISSING_BIRTH_DATE')
    try:
        if cell_type == 'n':
            number = Decimal(value)
            if not number.is_finite() or number != int(number) or number < 0 or (not epoch_1904 and number == 60):
                raise ValueError
            # Excel's 1900 leap-year bug must not shift January/February dates.
            origin = date(1904, 1, 1) if epoch_1904 else date(1899, 12, 31)
            result = origin + timedelta(days=int(number) - (not epoch_1904 and number > 60))
        else:
            result = date.fromisoformat(value)
        if result > date.today():
            raise ValueError
        return result
    except (ValueError, OverflowError, InvalidOperation):
        raise ImportProblem('INVALID_BIRTH_DATE') from None


def external_id(value, cell_type):
    if not value:
        raise ImportProblem('MISSING_PATIENT_ID')
    if cell_type == 'n':
        try:
            number = Decimal(value)
            if not number.is_finite() or number != int(number) or number < 0 or len(str(int(number))) > 15:
                raise ValueError
            value = str(int(number))
        except (ValueError, InvalidOperation, OverflowError):
            raise ImportProblem('INVALID_PATIENT_ID') from None
    if len(value) > 100:
        raise ImportProblem('INVALID_PATIENT_ID')
    return value


def read_patients(path, adapter='standard'):
    try:
        with ZipFile(path) as archive:
            if sum(i.file_size for i in archive.infolist()) > 32 * 1024 * 1024:
                raise ImportProblem('SPREADSHEET_TOO_LARGE')
            strings = []
            if 'xl/sharedStrings.xml' in archive.namelist():
                strings = [''.join(t.text or '' for t in s.iterfind('.//s:t', NS)) for s in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', NS)]
            book = ET.fromstring(archive.read('xl/workbook.xml'))
            sheets = book.findall('s:sheets/s:sheet', NS)
            if len(sheets) != 1:
                raise ImportProblem('SPREADSHEET_SHEET_AMBIGUOUS')
            rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
            rid = sheets[0].get('{'+REL_NS+'}id')
            target = next((r.get('Target') for r in rels if r.get('Id') == rid and r.get('TargetMode') != 'External'), None)
            if not target or '..' in PurePosixPath(target).parts:
                raise ImportProblem('INVALID_SPREADSHEET')
            sheet_path = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            sheet = ET.fromstring(archive.read(sheet_path))
            props = book.find('s:workbookPr', NS)
            epoch = props is not None and props.get('date1904') in ('1', 'true')

            def cell_value(cell):
                if cell is None:
                    return '', 's'
                if cell.find('s:f', NS) is not None:
                    raise ImportProblem('SPREADSHEET_FORMULA')
                kind = cell.get('t', 'n')
                v = cell.find('s:v', NS)
                text = v.text if v is not None and v.text else ''
                if kind == 's':
                    text = strings[int(text)] if text else ''
                elif kind == 'inlineStr':
                    text = ''.join(t.text or '' for t in cell.iterfind('.//s:t', NS))
                elif kind not in ('n', 'd', 'str'):
                    raise ImportProblem('INVALID_SPREADSHEET_CELL')
                return text.strip(), kind

            rows = sheet.findall('s:sheetData/s:row', NS)
            header_number = 2 if adapter == 'ijc1' else 1
            header = next((r for r in rows if int(r.get('r')) == header_number), None)
            if header is None:
                raise ImportProblem('SPREADSHEET_HEADERS')
            columns = defaultdict(list)
            for cell in header:
                value, _ = cell_value(cell)
                columns[value].append(''.join(c for c in cell.get('r') if c.isalpha()))
            required = HEADERS[adapter]
            if any(len(columns[name]) != 1 for name in required):
                raise ImportProblem('SPREADSHEET_HEADERS')
            records = defaultdict(list)
            ids = set()
            for row in rows:
                if int(row.get('r')) <= header_number:
                    continue
                cells = {''.join(c for c in cell.get('r') if c.isalpha()): cell for cell in row}
                values = [cell_value(cells.get(columns[name][0])) for name in required]
                if not any(v for v, _ in values):
                    continue
                key, _, initials, _ = [v for v, _ in values]
                if not key or not initials or len(key) > 100 or len(initials) > 100:
                    raise ImportProblem('INVALID_PATIENT_KEY')
                pid = external_id(*values[1])
                if pid in ids:
                    raise ImportProblem('DUPLICATE_PATIENT_ID')
                ids.add(pid)
                records[patient_key(key)].append(PatientRow(key, pid, initials, birth_date(*values[3], epoch)))
            return records
    except ImportProblem:
        raise
    except (BadZipFile, OSError, KeyError, ET.ParseError, ValueError, IndexError):
        raise ImportProblem('INVALID_SPREADSHEET') from None
