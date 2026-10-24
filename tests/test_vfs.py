"""Проверки CSV, двоичных данных, путей и неизменности исходника."""

import base64
import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT
from src.vfs import VFS, VFSError

SAMPLES = PROJECT_ROOT / "vfs-samples"


class VFSTests(unittest.TestCase):
    """Загружать реальные CSV и отдельно проверять поврежденные записи."""

    def load_rows(self, rows):
        """Создать временный CSV и загрузить его в VFS."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.csv"
            with path.open("w", encoding="utf-8", newline="") as source:
                writer = csv.writer(source)
                writer.writerow(["path", "type", "data"])
                writer.writerows(rows)
            return VFS.from_csv(path)

    def test_samples(self):
        """Все три требуемых варианта VFS корректно загружаются."""
        for name in ("minimal", "several", "deep"):
            with self.subTest(name=name):
                vfs = VFS.from_csv(SAMPLES / f"{name}.csv")
                self.assertEqual(vfs.nodes["/"].kind, "dir")
        self.assertEqual(len(VFS.from_csv(SAMPLES / "minimal.csv").nodes), 1)

    def test_binary_empty_and_nested(self):
        """Base64 хранит произвольные байты, родители создаются в памяти."""
        data = bytes(range(256))
        vfs = self.load_rows([
            ("/a/b/c/file.bin", "file", base64.b64encode(data).decode()),
            ("/empty", "dir", ""), ("/zero.txt", "file", ""),
        ])
        self.assertEqual(vfs.nodes["/a/b/c/file.bin"].data, data)
        self.assertEqual(vfs.children("/a/b"), ["c"])
        self.assertEqual(vfs.children("/empty"), [])
        self.assertEqual(vfs.nodes["/zero.txt"].data, b"")

    def test_explicit_parents_after_files(self):
        """Строки CSV не требуют сортировки от родителей к потомкам."""
        vfs = self.load_rows([("/a/b", "file", ""), ("/a", "dir", "")])
        self.assertEqual(vfs.children("/a"), ["b"])

    def test_invalid_rows(self):
        """Ошибки формата и конфликтующие пути отклоняются."""
        cases = [
            [("relative", "dir", "")],
            [("/a/../b", "dir", "")],
            [("/a//b", "dir", "")],
            [("/bad", "file", "???")],
            [("/bad", "dir", "data")],
            [("/bad", "link", "")],
            [("/a", "dir", ""), ("/a", "dir", "")],
            [("/a", "file", ""), ("/a/b", "dir", "")],
            [("/a/b", "dir", ""), ("/a", "file", "")],
            [("/", "file", "")],
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(VFSError):
                self.load_rows(rows)

    def test_bad_header_and_missing_file(self):
        """Неправильный заголовок и отсутствующий файл дают VFSError."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            with self.assertRaises(VFSError):
                VFS.from_csv(path)
            path.write_text("wrong,header\n", encoding="utf-8")
            with self.assertRaises(VFSError):
                VFS.from_csv(path)

    def test_paths_and_intermediate_files(self):
        """Пути проверяются по компонентам, а .. ограничен корнем."""
        vfs = VFS.from_csv(SAMPLES / "deep.csv")
        self.assertEqual(vfs.resolve("../../..", "/home"), "/")
        self.assertEqual(vfs.resolve("./student/../student", "/home"),
                         "/home/student")
        for path in ("/missing/..", "/etc/hosts/..", "/etc/hosts/", ""):
            with self.subTest(path=path), self.assertRaises(VFSError):
                vfs.resolve(path)

    def test_loading_does_not_write_files(self):
        """Загрузка CSV не меняет исходник и не распаковывает данные."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_bytes((SAMPLES / "deep.csv").read_bytes())
            before = hashlib.sha256(path.read_bytes()).digest()
            VFS.from_csv(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])
