# -*- coding=utf-8 -*-
from services.base import RunScriptService


class PYService(RunScriptService):
    def do_script(self, datas):
        result = []
        for data in datas:
            if "lee_test" in data.keys():
                result = data["lee_test"]["sys_user"]
        return result
