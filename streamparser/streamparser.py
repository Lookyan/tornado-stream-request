from tornado.web import RequestHandler
from tornado.gen import coroutine
from tornado.gen import is_future
from tornado.httputil import HTTPHeaders
from tornado.httputil import _parse_header
from tornado.log import gen_log


PHASE_BOUNDARY = 1
PHASE_HEADERS = 2
PHASE_BODY = 3


def get_boundary(content_type):
    """
    Extracts boundary from Content-Type
    """
    if content_type.startswith("multipart/form-data"):
        fields = content_type.split(";")
        for field in fields:
            k, sep, v = field.strip().partition("=")
            if k == "boundary" and v:
                return v
        else:
            raise ValueError("multipart boundary not found")


class StreamingFormDataParserDelegate:
    """
    Implement this interface to handle streaming multipart/form-data
    """

    def start_file(self, headers, disp_params):
        """
        Called when a new file is coming
        :arg headers: dict of headers
        :arg disp_params: dict of content disposition parameters
        """
        pass

    def file_data_received(self, file_data):
        """
        Called when a chunk of data has been received (for a current file)
        :arg file_data: chunk of file data
        """
        pass

    def finish_file(self):
        """Called when a file has been received"""
        pass


class StreamingFormDataParser:
    """
    Streaming multipart/form-data parser

    Most common use case is to create a parser in `prepare` method of `.RequestHandler`
    decorated with stream_request_body using self as the delegate and pass a chunk of data
    to `data_received` method.

    `.StreamingFormDataParser` invokes methods of `.StreamingFormDataParserDelegate`

    """
    def __init__(self, parser_delegate, headers=None):
        """
        :arg parser_delegate: a `.StreamingFormDataParserDelegate`
        :arg headers: dict of headers

        :raises: TypeError
        :raises: ValueError
        """
        self.parser_delegate = parser_delegate
        if not headers:
            if not isinstance(parser_delegate, RequestHandler):
                raise TypeError("parser_delegate must be a subclass of RequestHandler or you must provide headers dict")
            else:
                headers = parser_delegate.request.headers
        elif not isinstance(parser_delegate, StreamingFormDataParserDelegate):
            raise TypeError("parser_delegate must implement StreamingFormDataParserDelegate interface")

        self.current_phase = PHASE_BOUNDARY
        self.file_headers = []
        self.current_file = None
        self.boundary = get_boundary(headers["Content-Type"])
        if not self.boundary:
            raise ValueError("Invalid multipart/form-data")
        if self.boundary.startswith('"') and self.boundary.endswith('"'):
            self.boundary = self.boundary[1:-1]

        self._buffer = None
        self._boundary_delimiter = "--{}\r\n".format(self.boundary).encode()
        self._end_boundary = "\r\n--{}--\r\n".format(self.boundary).encode()

    @coroutine
    def data_received(self, chunk):
        """
        Receive chunk of multipart/form-data
        :arg chunk: chunk of data
        """
        if not self._buffer:
            self._buffer = chunk
        else:
            self._buffer += chunk

        while True:
            if self.current_phase == PHASE_BOUNDARY:
                if len(self._buffer) > len(self._boundary_delimiter):
                    if self._buffer.startswith(self._boundary_delimiter):
                        self.current_phase = PHASE_HEADERS
                        self._buffer = self._buffer[len(self._boundary_delimiter):]
                    elif self._buffer.startswith(self._end_boundary):
                        result = self.parser_delegate.finish_file()
                        if is_future(result):
                            yield result
                        return
                    else:
                        gen_log.warning("Invalid multipart/form-data")
                        return
                else:
                    # wait for next chunk
                    return

            if self.current_phase == PHASE_HEADERS:
                if b"\r\n\r\n" in self._buffer:
                    headers, remaining_part = self._buffer.split(b"\r\n\r\n", 1)

                    if headers:
                        headers = HTTPHeaders.parse(headers.decode("utf-8"))
                    else:
                        gen_log.warning("multipart/form-data missing headers")
                        return

                    disp_header = headers.get("Content-Disposition", "")
                    disposition, disp_params = _parse_header(disp_header)
                    if disposition != "form-data":
                        gen_log.warning("Invalid multipart/form-data")
                        return
                    self._buffer = remaining_part
                    self.current_phase = PHASE_BODY
                    result = self.parser_delegate.start_file(headers, disp_params)
                    if is_future(result):
                        yield result
                else:
                    # wait for all headers for current file
                    return

            if self.current_phase == PHASE_BODY:
                if self._boundary_delimiter in self._buffer:
                    data, remaining_data = self._buffer.split(self._boundary_delimiter, 1)
                    self._buffer = remaining_data
                    result = self.parser_delegate.file_data_received(data[:-2])
                    if is_future(result):
                        yield result
                    self.current_phase = PHASE_HEADERS
                    result = self.parser_delegate.finish_file()
                    if is_future(result):
                        yield result
                    continue
                elif self._end_boundary in self._buffer:
                    result = self.parser_delegate.file_data_received(self._buffer.split(self._end_boundary)[0])
                    if is_future(result):
                        yield result
                    result = self.parser_delegate.finish_file()
                    if is_future(result):
                        yield result

                    return
                else:
                    if self._buffer:
                        result = self.parser_delegate.file_data_received(self._buffer)
                        if is_future(result):
                            yield result
                    self._buffer = b""

                    return
