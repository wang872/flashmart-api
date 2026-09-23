from fastapi import HTTPException, status


class BizError(HTTPException):
    def __init__(self, code: int, detail: str):
        super().__init__(status_code=code, detail=detail)


def unauthorized(msg: str = "未登录或令牌无效") -> BizError:
    return BizError(status.HTTP_401_UNAUTHORIZED, msg)


def forbidden(msg: str = "无权限") -> BizError:
    return BizError(status.HTTP_403_FORBIDDEN, msg)


def not_found(msg: str = "资源不存在") -> BizError:
    return BizError(status.HTTP_404_NOT_FOUND, msg)


def conflict(msg: str) -> BizError:
    return BizError(status.HTTP_409_CONFLICT, msg)


def bad_request(msg: str) -> BizError:
    return BizError(status.HTTP_400_BAD_REQUEST, msg)
