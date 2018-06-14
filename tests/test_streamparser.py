import unittest

from tornado.httputil import HTTPHeaders
from tornado.log import gen_log
from tornado.testing import ExpectLog

from streamparser import StreamingFormDataParser

try:
    # py33+
    from unittest import mock
except ImportError:
    import mock


class StreamingFormDataParserTest(unittest.TestCase):

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_file_upload_full(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")
        parser = StreamingFormDataParser(delegate, headers)
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--
        """.replace(b"\n", b"\r\n")

        parser.data_received(data)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers = HTTPHeaders()
        expected_headers.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        delegate.start_file.assert_called_with(expected_headers, {"name": "files", "filename": "ab.txt"})
        delegate.file_data_received.assert_called_with(b"Foo")

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_file_upload_full_multiple_files(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")
        parser = StreamingFormDataParser(delegate, headers)
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234
Content-Disposition: form-data; name="files2"; filename="abc.txt"

Foo2
--1234--
        """.replace(b"\n", b"\r\n")

        parser.data_received(data)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers_first_file = HTTPHeaders()
        expected_headers_first_file.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        expected_headers_second_file = HTTPHeaders()
        expected_headers_second_file.add("Content-Disposition", 'form-data; name="files2"; filename="abc.txt"')
        delegate.file_data_received.assert_has_calls(
            [mock.call(b"Foo"), mock.call(b"Foo2")]
        )
        delegate.start_file.assert_has_calls(
            [
                mock.call(expected_headers_first_file, {"name": "files", "filename": "ab.txt"}),
                mock.call(expected_headers_second_file, {"name": "files2", "filename": "abc.txt"})
            ]
        )

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_file_upload_multiline(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")
        parser = StreamingFormDataParser(delegate, headers)
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
Bar
--1234--
        """.replace(b"\n", b"\r\n")

        parser.data_received(data)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers = HTTPHeaders()
        expected_headers.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        delegate.start_file.assert_called_with(expected_headers, {"name": "files", "filename": "ab.txt"})
        delegate.file_data_received.assert_called_with(b"Foo\r\nBar")

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_file_upload_special_filenames(self, StreamingFormDataParserDelegateMock):
        filenames = ['a;b.txt',
                     'a"b.txt',
                     'a";b.txt',
                     'a;"b.txt',
                     'a";";.txt',
                     'a\\"b.txt',
                     'a\\b.txt',
                     ]
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")

        for filename in filenames:
            delegate = StreamingFormDataParserDelegateMock()
            parser = StreamingFormDataParser(delegate, headers)
            data = """\
--1234
Content-Disposition: form-data; name="files"; filename="%s"

Foo
--1234--
""" % filename.replace('\\', '\\\\').replace('"', '\\"')
            data = data.replace("\n", "\r\n").encode()

            parser.data_received(data)

            self.assertTrue(delegate.start_file.called)
            self.assertTrue(delegate.finish_file.called)
            self.assertTrue(delegate.file_data_received.called)
            expected_headers = HTTPHeaders()
            expected_headers.add(
                "Content-Disposition", 'form-data; name="files"; filename="%s"' % filename
                                       .replace('\\', '\\\\')
                                       .replace('"', '\\"')
            )
            delegate.start_file.assert_has_calls([mock.call(expected_headers, {"name": "files", "filename": filename})])
            delegate.file_data_received.assert_called_with(b"Foo")
            delegate.reset_mock()
            StreamingFormDataParserDelegateMock.reset_mock()

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_boundary_starts_and_ends_with_quotes(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", 'multipart/form-data; boundary="1234"')
        parser = StreamingFormDataParser(delegate, headers)
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--
        """.replace(b"\n", b"\r\n")

        parser.data_received(data)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers = HTTPHeaders()
        expected_headers.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        delegate.start_file.assert_called_with(expected_headers, {"name": "files", "filename": "ab.txt"})
        delegate.file_data_received.assert_called_with(b"Foo")

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_missing_headers(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", 'multipart/form-data; boundary=1234')
        parser = StreamingFormDataParser(delegate, headers)
        data = b"""\
--1234


Foo
--1234--
        """.replace(b"\n", b"\r\n")

        with ExpectLog(gen_log, "multipart/form-data missing headers"):
            parser.data_received(data)

        self.assertFalse(delegate.start_file.called)
        self.assertFalse(delegate.finish_file.called)
        self.assertFalse(delegate.file_data_received.called)

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_invalid_content_disposition(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", 'multipart/form-data; boundary=1234')
        parser = StreamingFormDataParser(delegate, headers)
        data = b"""\
--1234
Content-Disposition: invalid; name="files"; filename="ab.txt"


Foo
--1234--
        """.replace(b"\n", b"\r\n")

        with ExpectLog(gen_log, "Invalid multipart/form-data"):
            parser.data_received(data)

        self.assertFalse(delegate.start_file.called)
        self.assertFalse(delegate.finish_file.called)
        self.assertFalse(delegate.file_data_received.called)

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_invalid_content_type_raises_value_error(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-type", "application/json; charset=UTF-8")
        with self.assertRaises(ValueError):
            StreamingFormDataParser(delegate, headers)

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_line_does_not_end_with_correct_line_break(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", 'multipart/form-data; boundary=1234')
        parser = StreamingFormDataParser(delegate, headers)
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"


Foo--1234--
        """.replace(b"\n", b"\r\n")

        parser.data_received(data)

        self.assertTrue(delegate.start_file.called)
        self.assertFalse(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_data_after_final_boundary(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")
        parser = StreamingFormDataParser(delegate, headers)
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--
garbage
        """.replace(b"\n", b"\r\n")

        parser.data_received(data)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers = HTTPHeaders()
        expected_headers.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        delegate.start_file.assert_called_with(expected_headers, {"name": "files", "filename": "ab.txt"})
        delegate.file_data_received.assert_called_with(b"Foo")

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_file_upload_by_parts(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")
        parser = StreamingFormDataParser(delegate, headers)
        data1 = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"\
""".replace(b"\n", b"\r\n")

        data2 = b"""\


Foo
--1234--
""".replace(b"\n", b"\r\n")

        parser.data_received(data1)
        parser.data_received(data2)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers = HTTPHeaders()
        expected_headers.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        delegate.start_file.assert_called_with(expected_headers, {"name": "files", "filename": "ab.txt"})
        delegate.file_data_received.assert_called_with(b"Foo")

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_file_upload_parted_boundary(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")
        parser = StreamingFormDataParser(delegate, headers)
        data1 = b"""\
--1234
Content-Disposition: form-d\
""".replace(b"\n", b"\r\n")

        data2 = b"""\
ata; name="files"; filename="ab.txt"

Foo
--1234--
""".replace(b"\n", b"\r\n")

        parser.data_received(data1)
        parser.data_received(data2)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers = HTTPHeaders()
        expected_headers.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        delegate.start_file.assert_called_with(expected_headers, {"name": "files", "filename": "ab.txt"})
        delegate.file_data_received.assert_called_with(b"Foo")

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_file_upload_parted_boundary_and_body(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")
        parser = StreamingFormDataParser(delegate, headers)
        data1 = b"""\
--1234
Content-Disposition: form-d\
""".replace(b"\n", b"\r\n")

        data2 = b"""\
ata; name="files"; filename="ab.txt"

Fo\
""".replace(b"\n", b"\r\n")

        data3 = b"""\
o
--1234--
""".replace(b"\n", b"\r\n")

        parser.data_received(data1)
        parser.data_received(data2)
        parser.data_received(data3)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers = HTTPHeaders()
        expected_headers.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        delegate.start_file.assert_called_with(expected_headers, {"name": "files", "filename": "ab.txt"})
        delegate.file_data_received.assert_has_calls([mock.call(b"Fo"), mock.call(b"o")])

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_file_upload_splitted_boundary(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data; boundary=1234")
        parser = StreamingFormDataParser(delegate, headers)
        data1 = b"""\
--12\
""".replace(b"\n", b"\r\n")

        data2 = b"""\
34
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--
""".replace(b"\n", b"\r\n")

        parser.data_received(data1)
        parser.data_received(data2)

        self.assertTrue(delegate.start_file.called)
        self.assertTrue(delegate.finish_file.called)
        self.assertTrue(delegate.file_data_received.called)
        expected_headers = HTTPHeaders()
        expected_headers.add("Content-Disposition", 'form-data; name="files"; filename="ab.txt"')
        delegate.start_file.assert_called_with(expected_headers, {"name": "files", "filename": "ab.txt"})
        delegate.file_data_received.assert_called_with(b"Foo")

    @mock.patch("streamparser.StreamingFormDataParserDelegate", spec=True)
    def test_invalid_boundary(self, StreamingFormDataParserDelegateMock):
        delegate = StreamingFormDataParserDelegateMock()
        headers = HTTPHeaders()
        headers.add("Content-Type", "multipart/form-data;")
        with self.assertRaises(ValueError):
            StreamingFormDataParser(delegate, headers)
