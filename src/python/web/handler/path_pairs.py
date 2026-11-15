import json
import os
from typing import Any, Dict, Optional

from bottle import HTTPResponse, request

from common import Context, PathPair, PathPairsConfig, overrides
from ..rate_limit import rate_limit
from ..web_app import IHandler, WebApp


class PathPairsHandler(IHandler):
    """
    CRUD for the remote-to-local path pairs.

    Changes are written to path_pairs.json at once but only take effect when the
    server restarts, so every successful change reports restart_required.
    """

    __MAX_NAME_LENGTH = 64
    __JSON = {"Content-Type": "application/json"}

    def __init__(
        self, path_pairs: PathPairsConfig, path_pairs_path: str, context: Context
    ):
        self.__path_pairs = path_pairs
        self.__path_pairs_path = path_pairs_path
        self.logger = context.logger.getChild("PathPairsHandler")

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        limit = rate_limit(max_requests=60, window_seconds=60.0, logger=self.logger)
        web_app.add_handler("/server/pathpairs", self.__handle_list)
        web_app.add_post_handler(
            "/server/pathpairs/create", limit(self.__handle_create)
        )
        web_app.add_post_handler(
            "/server/pathpairs/update/<pair_id>", limit(self.__handle_update)
        )
        web_app.add_post_handler(
            "/server/pathpairs/delete/<pair_id>", limit(self.__handle_delete)
        )

    def __handle_list(self):
        body = {"path_pairs": [p.to_dict() for p in self.__path_pairs.pairs]}
        return HTTPResponse(body=json.dumps(body), headers=self.__JSON)

    def __handle_create(self):
        data = request.json
        if not isinstance(data, dict):
            return HTTPResponse(body="Invalid request body", status=400)
        error = self.__validate(data, require_all=True)
        if error:
            return error
        pair = PathPair(
            name=data["name"].strip(),
            remote_path=data["remote_path"].strip(),
            local_path=data["local_path"].strip(),
            enabled=data.get("enabled", True),
            auto_queue=data.get("auto_queue", True),
        )
        conflict = self.__find_conflict(pair)
        if conflict:
            return HTTPResponse(body=conflict, status=409)
        self.__path_pairs.add_pair(pair)
        failure = self.__save(rollback=lambda: self.__path_pairs.remove_pair(pair.id))
        if failure:
            return failure
        self.logger.info("Created path pair '{}'".format(pair.name))
        return HTTPResponse(
            body=self.__pair_body(pair), status=201, headers=self.__JSON
        )

    def __handle_update(self, pair_id: str):
        existing = self.__path_pairs.get_pair(pair_id)
        if existing is None:
            return HTTPResponse(body="Path pair not found", status=404)
        data = request.json
        if not isinstance(data, dict):
            return HTTPResponse(body="Invalid request body", status=400)
        error = self.__validate(data, require_all=False)
        if error:
            return error
        updated = PathPair(
            name=data.get("name", existing.name).strip(),
            remote_path=data.get("remote_path", existing.remote_path).strip(),
            local_path=data.get("local_path", existing.local_path).strip(),
            enabled=data.get("enabled", existing.enabled),
            auto_queue=data.get("auto_queue", existing.auto_queue),
            pair_id=existing.id,
        )
        if existing.id == PathPair.LEGACY_ID and (
            updated.remote_path != existing.remote_path
            or updated.local_path != existing.local_path
        ):
            return HTTPResponse(
                body="The paths of the Default pair come from the Lftp settings; change them there",
                status=409,
            )
        conflict = self.__find_conflict(updated, ignore_id=existing.id)
        if conflict:
            return HTTPResponse(body=conflict, status=409)
        self.__path_pairs.update_pair(updated)
        failure = self.__save(rollback=lambda: self.__path_pairs.update_pair(existing))
        if failure:
            return failure
        self.logger.info("Updated path pair '{}'".format(updated.name))
        return HTTPResponse(body=self.__pair_body(updated), headers=self.__JSON)

    def __handle_delete(self, pair_id: str):
        existing = self.__path_pairs.get_pair(pair_id)
        if existing is None:
            return HTTPResponse(body="Path pair not found", status=404)
        self.__path_pairs.remove_pair(pair_id)
        failure = self.__save(rollback=lambda: self.__path_pairs.add_pair(existing))
        if failure:
            return failure
        self.logger.info("Deleted path pair '{}'".format(existing.name))
        return HTTPResponse(
            body=json.dumps({"restart_required": True}), headers=self.__JSON
        )

    def __validate(
        self, data: Dict[str, Any], require_all: bool
    ) -> Optional[HTTPResponse]:
        for key in ("name", "remote_path", "local_path"):
            if key not in data:
                if require_all:
                    return HTTPResponse(body="{} is required".format(key), status=400)
                continue
            value = data[key]
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                return HTTPResponse(
                    body="{} must be a non-empty string".format(key), status=400
                )
        if "name" in data and len(data["name"].strip()) > self.__MAX_NAME_LENGTH:
            return HTTPResponse(
                body="name must be at most {} characters".format(
                    self.__MAX_NAME_LENGTH
                ),
                status=400,
            )
        if "local_path" in data and not os.path.isabs(data["local_path"].strip()):
            return HTTPResponse(body="local_path must be an absolute path", status=400)
        for key in ("enabled", "auto_queue"):
            if key in data and not isinstance(data[key], bool):
                return HTTPResponse(body="{} must be a boolean".format(key), status=400)
        unknown = set(data) - {
            "name",
            "remote_path",
            "local_path",
            "enabled",
            "auto_queue",
        }
        if unknown:
            return HTTPResponse(
                body="Unknown field(s): {}".format(", ".join(sorted(unknown))),
                status=400,
            )
        return None

    def __find_conflict(
        self, pair: PathPair, ignore_id: Optional[str] = None
    ) -> Optional[str]:
        for other in self.__path_pairs.pairs:
            if other.id == ignore_id:
                continue
            if other.name == pair.name:
                return "A path pair named '{}' already exists".format(pair.name)
            if other.local_path.rstrip("/") == pair.local_path.rstrip("/"):
                return "Path pair '{}' already uses that local path".format(other.name)
            if other.remote_path.rstrip("/") == pair.remote_path.rstrip("/"):
                return "Path pair '{}' already uses that remote path".format(other.name)
        return None

    def __save(self, rollback) -> Optional[HTTPResponse]:
        try:
            self.__path_pairs.to_file(self.__path_pairs_path)
        except OSError:
            self.logger.exception("Could not write the path pairs")
            rollback()
            return HTTPResponse(body="Could not save the path pairs", status=500)
        return None

    @staticmethod
    def __pair_body(pair: PathPair) -> str:
        body = pair.to_dict()
        body["restart_required"] = True
        return json.dumps(body)
