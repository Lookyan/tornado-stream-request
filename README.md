# Tornado Streaming Parser

## Example with filestorage

```python
@stream_request_body
class UploadHandler(BaseHandler, StreamingFormDataParserDelegate):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files_id = None
        self.parser = None
        self.file = None

    @property
    def fs(self):
        return self.application.file_storage.fs

    @coroutine
    def post(self):
        if self.file and not self.file.closed:
            yield self.file.close()
            self.set_status(BAD_REQUEST)
            return self.finish({'error': {
                'code': BAD_REQUEST,
                'message': 'Invalid multipart/form-data',
            }})
        self.write({'result': {
            'fileIds': self.files_id
        }})

    @coroutine
    def prepare(self):
        if self.request.method == 'POST':
            self.files_id = []
            try:
                self.parser = StreamingFormDataParser(self)
            except Exception as e:
                self.exception(e)
                self.set_status(BAD_REQUEST)
                return self.finish({'error': {
                    'code': BAD_REQUEST,
                    'message': 'Invalid multipart/form-data',
                }})

    @coroutine
    def data_received(self, chunk: bytes):
        if self.request.method == 'POST':
            try:
                yield self.parser.data_received(chunk)
            except Exception as e:
                self.exception(e)
                self.set_status(BAD_REQUEST)
                return self.finish({'error': {
                    'code': BAD_REQUEST,
                    'message': 'Invalid multipart/form-data',
                }})

    @coroutine
    def start_file(self, headers, disp_params):
        filename = disp_params.get('filename', None)

        if self.file and not self.file.closed:
            yield self.file.close()
            self.set_status(BAD_REQUEST)
            return self.finish({'error': {
                'code': BAD_REQUEST,
                'message': 'Invalid multipart/form-data',
            }})

        self.file = yield self.fs.new_file(filename=filename)

    @coroutine
    def finish_file(self):
        if not self.file or self.file.closed:
            self.warning('file is not opened or is already closed. Invalid multipart/form-data')
            return
        self.files_id.append(str(self.file._id))
        yield self.file.close()

    @coroutine
    def file_data_received(self, file_data):
        try:
            yield self.file.write(file_data)
        except Exception as e:
            self.exception(e)
            yield self.file.close()
```
