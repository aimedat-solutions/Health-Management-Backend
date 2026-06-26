from rest_framework.response import Response


class ApiResponse(Response):
    def __init__(self, data=None, meta=None, status=None, headers=None, exception=False):
        body = {"data": data}
        if meta is not None:
            body["meta"] = meta
        super().__init__(body, status=status, headers=headers, exception=exception)
