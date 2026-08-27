from pathlib import Path
from pypdf import PdfReader
from pypdf.errors import PdfReadError

def extract_pdf_text(file_path:Path)->str:
    try:
        reader = PdfReader(str(file_path))
        pages_text=[]

        for page in reader.pages:
            text=page.extract_text() or ''
            pages_text.append(text)

        result =  '\n'.join(pages_text).strip()
        if not result:
            raise ValueError('PDF中没有可提取的文字')
        return result
    except(PdfReadError,OSError) as error:
        raise ValueError('PDF文件无法读取') from error
