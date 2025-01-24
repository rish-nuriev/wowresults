import tempfile

from django.core import files
import requests


def download_logo(logo_url: str): # type: ignore
    with requests.get(logo_url, stream=True, timeout=10) as resp:
        if resp.status_code == requests.codes.ok:
            file_name = logo_url.split("/")[-1]
            # Создать временный файл
            tmp_file = tempfile.NamedTemporaryFile()
            # Считать по частям
            for block in resp.iter_content(1024 * 8):
                # Если больше нет блоков завершить чтение
                if not block:
                    break
                # Записать блок во временный файл
                tmp_file.write(block)
            return (file_name, files.File(tmp_file))
    return None
